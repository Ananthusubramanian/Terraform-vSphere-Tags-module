# Terraform-vSphere-tags-module


Terraform module which provides vsphere tag ids as result for attaching to VM's or any resources in vSphere.

Features : 

If category or tag is missing, it creates new vSphere Tags and Category 

Else it utilizes existing vsphere category or tag 

Returns list of tag id which we can provide to vsphere server module





Example Usage

```
module "tags" {

    source = "./../tags"

    env = "dev"

    tier = "3"

    location = "India"

    created-by = "Ananthu"

    api-user = "${local.user}" 

    api-pass = "${local.user}"

    vcenter-ip = "${local.vcenter_url}" 

}
```

Output :

"tags_id" : List containg ID's of all tags 


Note : 


Provide the api-user which is user name of vsphere , api-pass which is the password of vsphere login and vcenter-ip is the ip of vSphere 
