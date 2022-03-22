
import shutil
import requests
from requests.auth import HTTPBasicAuth
import time
import os
import wget

ssl_verify = False
# Local test
# url = "https://localhost:5000/image_creation"

url = "https://bscgrid20.bsc.es/image_creation"




js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "rome", "container_engine": "singularity"},
"workflow":"minimal_workflow",
"step_id" :"wordcount",
"force": True}

#image_creation credentials
user="test"
pswd="*****"

download_path="/home/jorgee/Downloads/"


###### This is only required to configure the service first time #####
# Registration of new user
#js_register_request = {"username" : "test", "password" : "T3st22"}
#requests.post(url +'/register', json=js_register_request, verify=ssl_verify)


# create HTTP Basic authentication
auth_u_p = HTTPBasicAuth(user,pswd)

# Login with credentials and get a temporal token

res = requests.get(url+'/login', verify=ssl_verify,  auth=HTTPBasicAuth(user,pswd))
print ("response" + str(res))
token = res.json()['token']
print("Login successfull. Token:" + token)
auth_u_p = HTTPBasicAuth(token,None)

# Build of the base image. - Commented because THIS IS JUST REQUIRED FIRST TIME -

# js_base_build_request = js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "skylake", "container_engine": "docker"},
# "workflow": "BASE",
# "step_id" : "BASE",
# "force": False}

#res = requests.post(url+'/build/', json=js_base_build_request, verify=ssl_verify, auth=auth_u_p)

# build workflow image
container_engine = "singularity"
js_build_request = {"machine": {"platform": "linux/amd64", "architecture": "rome", "container_engine": container_engine},
"workflow":"minimal_workflow",
"step_id" :"wordcount",
"force": False}

res = requests.post(url+'/build/', json=js_build_request, verify=ssl_verify, auth=auth_u_p)

# Check result of the call and get the build id
if res.ok:
    id = res.json()['id']
    print(" Submitted with id" + id)
    status = 'PENDING'
    
    # Periodically check the status of the build
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
    
    # Once finished get the singularity image 
    if status == 'FINISHED' and container_engine == "singularity":
        image_file = os.path.join(download_path, result['filename'])
        #import ssl
        #ssl._create_default_https_context = ssl._create_unverified_context
        #filename = wget.download(url + "/images/download/"+image_file, out=download_path)
        response = requests.get(url+ "/images/download/"+image_file, verify=ssl_verify, auth=auth_u_p, stream=True)
        
        with open(image_file, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response
        
    
else :
    # error in the build call
    print("Error \n"+str(res)) 
