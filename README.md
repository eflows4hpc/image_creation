# HPC Container Image Creation 
This repository contains the implementation of the Service for creating container images for eFlows4HPC platform

## Requirements

This service requires to have Docker buildx system in the computer where running the service python > 3.7. Once, these tools have been installed, install the python modules described in requirements.txt file.

```
$ pip install -r requirements.txt
```

Finally, clone the workflow registry and software catalog repositories

```
$ git clone https://github.com/eflows4hpc/workflow-registry.git

$ git clone https://github.com/eflows4hpc/software-catalog.git

```

## Installation and configuration

Once you have installed the requirements clone the Container Image Creation repository

```
$ git clone https://github.com/eflows4hpc/image_creation.git
```
Modify the image creation configuration, provinding the information for accessing the container registry and the loaction where the workflow registry or the software catalog has been donwloaded

```
$ cd image_creation
$ vim config/configuration.py
```

Finally, start the service with the following command

```
$ python3 builder_service.py
```


## API


### Trigger an image creation 

This API endpoint allows the *end-user* to trigger the image creation

#### Request

`POST /build/`

```json
{
  "machine": {
    "platform": "linux/amd64", 
    "architecture": "rome", 
    "container_engine": "singularity"},
  "workflow":"minimal_workflow",
  "step_id" :"wordcount",
  "force": False
}
```

#### Response

```
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "id": "<creation_id>"
}
```

### Check status of an image creation 

This API endpoint allows the *end-user* to check the status of an the image creation

#### Request

`GET /build/<creation_id>`


#### Response

```
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "status": "< PENDING | STARTED | BUILDING | CONVERTING | FINISHED | FAILED >",
  "message": "< Error message in case of failure >",
  "image_id": "< Generated docker image id >",
  "filename": "< Generated singularity image filename >"
}
```

### Download image 

This API endpoint allows the *end-user* to download the created image

#### Request

`GET /images/download/<Generated singularity image filename>`


#### Response

```
HTTP/1.1 200 OK
Content-Disposition: attachment
Content-Type: application/binary
```
## Client
A simple BASH client has been implemented in client.sh. This is the usage of this client

```
./client.sh <user> <passwd> <image_creation_service_url> <"build"|"status"|"download"> <json_file|build_id|image_name>
```

The following lines show an example of the different commands

```
$ image_creation> ./client.sh user pass https://bscgrid20.bsc.es build test_request.json
Response:
{"id":"f1f4699b-9048-4ecc-aff3-1c689b855adc"}

$ image_creation> ./client.sh user pass https://bscgrid20.bsc.es status f1f4699b-9048-4ecc-aff3-1c689b855adc
Response:
{"filename":"reduce_order_model_sandybridge.sif","image_id":"ghcr.io/eflows4hpc/reduce_order_model_sandybridge","message":null,"status":"FINISHED"}

$ image_creation> ./client.sh user pass https://bscgrid20.bsc.es download reduce_order_model_sandybridge.sif

--2022-05-24 16:01:28--  https://bscgrid20.bsc.es/image_creation/images/download/reduce_order_model_sandybridge.sif
Resolving bscgrid20.bsc.es (bscgrid20.bsc.es)... 84.88.52.251
Connecting to bscgrid20.bsc.es (bscgrid20.bsc.es)|84.88.52.251|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2339000320 (2.2G) [application/octet-stream]
Saving to: ‘reduce_order_model_sandybridge.sif’

reduce_order_model_sandybridge.sif        0%[                          ]   4.35M   550KB/s    eta 79m 0s
```
