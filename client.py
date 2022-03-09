import requests
import time
ssl_verify = False
url = "http://localhost:5000"

js_request = {"machine": {"platform": "linux/amd64", "architecture": "skylake", "container_engine": "singularity"},
"workflow":"minimal_workflow",
"step_id" :"wordcount",
"force": True}

res = requests.post(url+'/build/', json=js_request, verify=ssl_verify)
if res.ok:
    id = res.json()['id']
    print(" Submitted with id" + id)
    status = 'PENDING'
    while (status != 'FAILED') and (status != 'FINISHED'): 
        time.sleep(5)
        res2 = requests.get(url+'/build/'+id, verify=ssl_verify)
        if res2.ok:
            ret = res2.json()
            status = ret['status']
            print ("Build " + id + ": status - " + status)
            if status == 'FAILED'  or status == 'FINISHED':
                print("Result:" + str(ret))
        else:
            print("Error \n"+str(res2))
            status = 'FAILED'
else :
    print("Error \n"+str(res))