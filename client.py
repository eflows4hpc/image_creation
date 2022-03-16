from curses.ascii import HT
import requests
from requests.auth import HTTPBasicAuth
import time
ssl_verify = False
url = "https://localhost:5000"
js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "skylake", "container_engine": "singularity"},
"workflow":"minimal_workflow",
"step_id" :"wordcount",
"force": True}
user="test"
pswd="T3st22"
#js_register_request = {"username" : "test", "password" : "T3st22"}
#requests.post(url +'/register', json=js_register_request, verify=ssl_verify)
auth_u_p = HTTPBasicAuth(user,pswd)
res = requests.get(url+'/login', verify=ssl_verify,  auth=HTTPBasicAuth(user,pswd))
token = res.json()['token']
hed = {'Authorization': 'Bearer ' + token}
print("Login successfull. Token:" + token)
auth_u_p = HTTPBasicAuth(token,None)
res = requests.post(url+'/build/', json=js_build_request, verify=ssl_verify, auth=auth_u_p)
if res.ok:
    id = res.json()['id']
    print(" Submitted with id" + id)
    status = 'PENDING'
    while (status != 'FAILED') and (status != 'FINISHED'): 
        time.sleep(5)
        res2 = requests.get(url+'/build/'+id, verify=ssl_verify, auth=auth_u_p)
        if res2.ok:
            status = res2.json()['status']
            print ("Build " + id + ": status - " + status)
        else:
            print("Error \n"+str(res2))
            status = 'FAILED'
else :
    print("Error \n"+str(res)) 