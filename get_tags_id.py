from email import header
from typing import List, Dict
import sys
import subprocess
import enum
import json

input = sys.stdin.read()
argsdict  = json.loads(input)

def install(package):
    subprocess.check_call(["pip3", "install", package,"--force-reinstall","--no-cache-dir"]
    ,stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)

install("aiohttp")

import asyncio
import aiohttp

VALUE_KEY = 'value'
Categories = ["env","tier","backup","location","created-by"]


class Case(enum.Enum):
   Post = 1
   Get = 2
   Create_Category_Tag = 3
   Create_Tag = 4


class VMTagReader:
   

    async def get_details(self, url, sem, case):
    

        if Case.Get == case:

            async with sem, self.session.get(url,headers=self.headers) as resp:
                data = await resp.json()
                data["url"] = url
                return data

        elif Case.Post == case:  

            async with sem, self.session.post(url,headers=self.headers) as resp:
                data = await resp.json()
                data["url"] = url
                return data

        elif Case.Create_Category_Tag == case:

            create_category_payload = {
            "create_spec": {
                "associable_types": [
                    "VirtualMachine"
                ],
                "cardinality": "SINGLE",
                "description": "Created from terraform",
                "name": url["category"]
            }
            }
        
            async with sem , self.session.post(str('{}/rest/com/vmware/cis/tagging/category'.format(self.host)) , json=create_category_payload , headers=self.headers) as resp:
                data = await resp.json()
                
                create_tag_payload = {
                     "create_spec": {
                        "category_id":  data[VALUE_KEY],
                        "description": "Created Tag using terraform",
                        "name": url["tag"]
                     }
                }

                async with sem , self.session.post(str('{}/rest/com/vmware/cis/tagging/tag'.format(self.host)) , json=create_tag_payload  , headers=self.headers) as resp:
                    
                    data = await resp.json()
                    return data[VALUE_KEY]

        elif Case.Create_Tag == case:
            
            create_tag_payload = {
                     "create_spec": {
                        "category_id":  url["category_id"],
                        "description": "Created Tag using terraform",
                        "name": url["tag"]
                     }
            }

            async with sem , self.session.post(str('{}/rest/com/vmware/cis/tagging/tag'.format(self.host)) , json=create_tag_payload  , headers=self.headers) as resp:
                data = await resp.json()
                return data[VALUE_KEY]
    
    async def runrequest(self, urls, case):
        sem = asyncio.Semaphore(10)
        tasks = []
       
        for url in urls:
            tasks.append(self.loop.create_task(self.get_details(url, sem, case)))
        results = await asyncio.gather(*tasks)
        return results


    def __init__(self, vcenter_url: str, login: str, password: str):
        self.host = vcenter_url
        self.login= login
        self.password = password
    

    def read_vms_tags(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get Categories With Tags
        """
        dict_category_tag = {}

        loop = asyncio.get_event_loop()
        
        self.loop = loop

        loop.run_until_complete(asyncio.gather(self.get_session()))

        categories = loop.run_until_complete(asyncio.gather(self.get_categories()))[0]
        
        urls = []
        [urls.append(str('{}/rest/com/vmware/cis/tagging/category/id:{}'.format(self.host,category_uid))) for category_uid in categories]
         
        category_details = loop.run_until_complete(asyncio.gather(self.runrequest(urls,Case.Get)))[0]

        tasks = []
        category_found = []
        for category in category_details:
            if VALUE_KEY in category and "name" in category[VALUE_KEY]:
                category_name_lower = category[VALUE_KEY]["name"].lower()
                if category_name_lower in Categories:
                    dict_category_tag[category_name_lower] = {}
                    dict_category_tag[category_name_lower]["*id*"] = category[VALUE_KEY]["id"]
                    category_found.append(category_name_lower)
                    url = '{}/rest/com/vmware/cis/tagging/tag/id:{}?~action=list-tags-for-category'.format(self.host,category[VALUE_KEY]["id"])
                    tasks.append(self.runrequest([url], Case.Post))

        tags_in_category = loop.run_until_complete(asyncio.gather(*tasks))
 
        tasks = []
        for result in tags_in_category:
            tagurls = []
            [tagurls.append(str('{}/rest/com/vmware/cis/tagging/tag/id:{}'.format(self.host,tags))) for tags in result[0][VALUE_KEY]]
            tasks.append(self.get_all_tags_name(tagurls))
        
        tags_details_of_all_categories = loop.run_until_complete(asyncio.gather(*tasks))

        for i , result in enumerate(tags_details_of_all_categories):
            for tag in result:
                if("name" in tag[VALUE_KEY].keys()):
                    dict_category_tag[category_found[i]][tag[VALUE_KEY]["name"]] = tag[VALUE_KEY]["id"]
         
        tags_id = []


        create_category_tag = []
        create_tag = []
        for category in Categories:
            if(category in dict_category_tag.keys()):
                
                tags = list(dict_category_tag[category].keys())
                tagsLower= [i.lower() for i in tags]

                if(argsdict[category].lower() in tagsLower):
                    tag_name = tags[tagsLower.index(argsdict[category].lower())]
                    tags_id.append(dict_category_tag[category][tag_name])
                else:
                    #Create Tag with category id = dict_category_tag[category]["*id*"]
                    create_tag.append({ "category_id" : dict_category_tag[category]["*id*"] , "tag" : argsdict[category]})
            else:
                #Create Category And Tag
                create_category_tag.append({ "category" : category, "tag" : argsdict[category]})
        
        tag_id_from_create_category_tag = loop.run_until_complete(asyncio.gather(self.runrequest(create_category_tag,Case.Create_Category_Tag)))[0]
        tag_id_from_create_tag = loop.run_until_complete(asyncio.gather(self.runrequest(create_tag,Case.Create_Tag)))[0]
        
        tags_id.extend(tag_id_from_create_category_tag)
        tags_id.extend(tag_id_from_create_tag)

        loop.run_until_complete(asyncio.gather(self.session.close()))
        
        
        return tags_id

        
    async def get_session(self):

        conn = aiohttp.TCPConnector(ssl=False)
        auth = aiohttp.BasicAuth(login=self.login, password=self.password, encoding='utf-8')
        self.session = aiohttp.ClientSession(connector=conn,auth=auth)
        async with self.session.post('{}/rest/com/vmware/cis/session'.format(self.host)) as resp:
            data = await resp.json()
            self.headers = {'vmware-api-session-id': data[VALUE_KEY]}

    async def get_categories(self):
        
        async with self.session.get('{}/rest/com/vmware/cis/tagging/category'.format(self.host),headers=self.headers) as res_category:
            
            data = await res_category.json()
            return data[VALUE_KEY]
            
    async def get_all_tags_name(self, tagsurl):

        resp = await self.runrequest(tagsurl, Case.Get)
        return resp     
                    
      

vcentre = argsdict['vcenter-ip']
vmr = VMTagReader(
        vcenter_url='https://'+vcentre,
        login=argsdict['api-user'],
        password=argsdict['api-pass'])

vm_tags = vmr.read_vms_tags()


output = {
    "tags_id" : " ".join(vm_tags)
}

output_json = json.dumps(output,indent=2)
print(output_json)

    


