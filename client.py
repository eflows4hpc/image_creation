
import requests
from requests.auth import HTTPBasicAuth
import time
ssl_verify = False
#url = "https://localhost:5000/image_creation"

url = "https://bscgrid20.bsc.es/image_creation"


js_base_build_request = js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "skylake", "container_engine": "docker"},
"workflow": "BASE",
"step_id" : "BASE",
"force": False}

js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "skylake", "container_engine": "singularity"},
"workflow":"minimal_workflow",
"step_id" :"wordcount",
"force": False}
user="test"
pswd="T3st22"
#js_register_request = {"username" : "test", "password" : "T3st22"}
#requests.post(url +'/register', json=js_register_request, verify=ssl_verify)
auth_u_p = HTTPBasicAuth(user,pswd)
res = requests.get(url+'/login', verify=ssl_verify,  auth=HTTPBasicAuth(user,pswd))
print ("response" + str(res))
token = res.json()['token']
hed = {'Authorization': 'Bearer ' + token}
print("Login successfull. Token:" + token)
auth_u_p = HTTPBasicAuth(token,None)
# build normal image
res = requests.post(url+'/build/', json=js_build_request, verify=ssl_verify, auth=auth_u_p)
# build base image
#res = requests.post(url+'/build/', json=js_base_build_request, verify=ssl_verify, auth=auth_u_p)
if res.ok:
    id = res.json()['id']
    print(" Submitted with id" + id)
    status = 'PENDING'
    while (status != 'FAILED') and (status != 'FINISHED'): 
        time.sleep(5)
        res2 = requests.get(url+'/build/'+id, verify=ssl_verify, auth=auth_u_p)
        if res2.ok:
            result = res2.json()
            status = result['status']
            print ("Build " + id + ": status - " + status)
            if status == 'FAILED':
                print("ERROR:" +str(result)) 
        else:
            print("Error \n"+str(res2))
            status = 'FAILED'
else :
    print("Error \n"+str(res)) 
