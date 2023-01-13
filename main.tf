locals {

  ## Add checks
 
  env-check = contains(["qa", "test", "prod", "dev"], var.env) == false ? file("ERROR:  env can only have value :  qa, nal-prod, test, prod, dev ") : "Test"
  
}

data "external" "get_all_vm_tags_id" {
  program = ["${path.module}/get_tags_id.py"]
  query = {
    env             = "${var.env}"
    tier            =  "${var.tier}"
    backup          =  "${var.backup}"
    location        = "${var.location}"
    created-by      =  "${var.created-by}" 
    vcenter-ip      =  "${var.vcenter-ip}"
    api-user        =  "${var.api-user}"
    api-pass        =  "${var.api-pass}"
    path            =  "${path.module}"
  }
}

output "tagslist" {
  value = split(" ", data.external.get_all_vm_tags_id.result.tags_id)
  depends_on = [ data.external.get_all_vm_tags_id ]
}
