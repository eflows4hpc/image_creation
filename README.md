# HPC Container Image Creation 
This repository contains the implementation of the Service for creating container images for eFlows4HPC platform

## Requirements

This service requires to have Docker buildx system in the computer where running the service python > 3.7. Once, these tools have been installed, install the python modules described in requirements.txt file.

```
$ pip install -r requirements.txt
```

Finally, clone the software catalog repositories

```
$ git clone https://github.com/eflows4hpc/software-catalog.git
```

## Installation and configuration

Once you have installed the requirements clone the Container Image Creation repository

```
$ git clone https://github.com/eflows4hpc/image_creation.git
```
Modify the image creation configuration, provinding the information for accessing the container registry and the Google captcha as well as the location where the software catalog has been donwloaded and the directory where images will be created.

```
$ cd image_creation
$ image_creation > vim config/configuration.py
```

Create the database

```
$ image_creation > python3
>>> from builder_service import db
>>> db.drop_all()
>>> db.create_all()
```

Finally, start the service with the following command

```
$ image_creation > python3 builder_service.py
```

For production runs we recommend to use production WGSY servers. Next instructions are explained for mod_wsgi-express.
First you have to install the mod_wsgi-express software

```
$ sudo apt install apache2-dev
$ sudo pip install mod_wsgi
```

Start the service using the following command. (Customize it according to your machine configuration)

```
$ image_creation> mod_wsgi-express start-server --port 5000 --processes=4 --enable-sendfile --url-alias /image_creation/images/download </path/to/tmp>/images/ wsgi.py
```

## API


### Trigger an image creation 

This API endpoint allows the *end-user* to trigger the image creation. The request should include a description of the target machine and the identification of the workflow.

#### Request

`POST /build/`

```json
{
  "machine": {
    "platform": "linux/amd64", 
    "architecture": "rome", 
    "container_engine": "singularity",
    "mpi": "openmpi@4",
    "gpu": "cuda@10"},
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
./cic_cli <user> <passwd> <image_creation_service_url> <"build"|"status"|"download"> <json_file|build_id|image_name>
```

The following lines show an example of the different commands

```
$ image_creation> ./cic_cli user pass https://bscgrid20.bsc.es build test_request.json
Response:
{"id":"f1f4699b-9048-4ecc-aff3-1c689b855adc"}

$ image_creation> ./cic_cli user pass https://bscgrid20.bsc.es status f1f4699b-9048-4ecc-aff3-1c689b855adc
Response:
{"filename":"reduce_order_model_sandybridge.sif","image_id":"ghcr.io/eflows4hpc/reduce_order_model_sandybridge","message":null,"status":"FINISHED"}

$ image_creation> ./cic_cli user pass https://bscgrid20.bsc.es download reduce_order_model_sandybridge.sif

--2022-05-24 16:01:28--  https://bscgrid20.bsc.es/image_creation/images/download/reduce_order_model_sandybridge.sif
Resolving bscgrid20.bsc.es (bscgrid20.bsc.es)... 84.88.52.251
Connecting to bscgrid20.bsc.es (bscgrid20.bsc.es)|84.88.52.251|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2339000320 (2.2G) [application/octet-stream]
Saving to: ‘reduce_order_model_sandybridge.sif’

reduce_order_model_sandybridge.sif        0%[                          ]   4.35M   550KB/s    eta 79m 0s
```
## Using Image Creation as library

Image creation can be also used in a laptop without a service interface.

The installation procedure is almost the same as when deploying as a service. You need to install the requirements-library.txt, clone the software-catalog repository and fill the configuration file.

To build a container image you have to specify a JSON file with the machine information and the workflow reference (name, step and version) in the Workflow Registry as you do in the CLI. You can also refer to a local workflow indicating the path in your localhost where we can fin the description. In this case, you must also specify a name, step and version to generate an image id to refer to the created image. Moreover you can also indicate if you want to push the generated image to the repository or just keep in your local repository. An example of this JSON file is shown below.


```json
{
  "machine": {
    "platform": "linux/amd64", 
    "architecture": "rome", 
    "container_engine": "singularity",
    "mpi": "openmpi@4"},
  "workflow" : "tutorial" ,
  "step_id" : "lysozyme",
  "path" : "/path/to/description/",
  "force": False,
  "push" : False
}
```

To run the local execution you have to run the following command:

```
$ image_creation > python3 cic_builder.py --request /path/to/json_file
```
