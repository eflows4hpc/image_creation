# HPC Container Image Creation
This repository contains the implementation of the Container Image Creation tool of the eFlows4HPC project. This tool can be deployed as a Service in a Server or used a a library in a stand alone model. 

## Requirements

This tool requires a computer with a Linux distribution, Docker buildx system and Python >=3.7 installed. Docker Buildx is already included in latest Docker packages for Linux distributions.

Details about how to install docker in this can be found in https://docs.docker.com/engine/install/

For supporting the creation of Singularity Images, you need to install Singularity-CE. Details about how to install it can be found in https://docs.sylabs.io/guides/3.9/admin-guide/installation.html#install-from-source 

Once, these tools have been installed, install the python modules depending on the type of deployment we want to do:

* Service deployment Option: if you want to do a Service deployment you have to use the dependencies described in requirements.txt file.

```
$ pip install -r requirements.txt
```

* Library Deployement Option: if you want to use the tool in a library mode, you have to use the dependencies described in requirements-library.txt file.

```
$ pip install -r requirements-library.txt
```

Finally, in both cases you need clone the software catalog repository. You can use the eflows4HPC version or any other github repository forked from this one.

```
$ git clone https://github.com/eflows4hpc/software-catalog.git
```

## Installation and configuration

Once you have installed the requirements, clone the Container Image Creation repository. 

```
$ git clone https://github.com/eflows4hpc/image_creation.git
```
To configure the image creation tool you need to modify the configuration file located in the 'config' folder. 

```
$ cd image_creation
$ image_creation > vim config/configuration.py
```

The required configuration will depend on the deployment type. The first steps described in this guide are common for library and service mode and latest steps are just required for the service deployment steps.

## Common installation steps

1. Specify the details to access the container image registry. In this section you need to specify the URL, credentials and image prefix used by this image registry. In the example below, we have set an example of this configuration for the eflow4hpc container registry. You can specify any image registry compatible with the docker registry API.

```
registry_cfg = {
    "url" : "ghcr.io", 
    "user": "_put_username", 
    "token": "_put_token",
    "images_prefix": "ghcr.io/eflows4hpc/"
} 
```

2. Specify the Workflow Registry URL and Software Catalog location. 
```
repositories_cfg = {
    "workflow_repository":"https://github.com/eflows4hpc/workflow-registry.git", 
    "software_repository":"/path/to/software-catalog/" 
    }
```

3. Specify the folder where images are created and other configuration parameters for the image creation.
```
build_cfg = {
    "tmp_folder":"/path/to/tmp", # path where images are created 
    "builder_home": "/path/to/image_creation/", # path where the Container Image Creation is installed
    "base_image": "ghcr.io/eflows4hpc/spack_base:0.19.2", 
    "dockerfile": "Dockerfile.spack",  
    "spack_cfg":"/path/to/software-catalog/cfg",
    "max_concurrent_builds" : 3, # number of concurrent builds (No used in library mode)
    "singularity_sudo" : True # Indicates if singularity build must be done ir sudo mode
    }
```

## Extra installation steps for Service deployment.

4. The last steps included in the config/configuration.py file are included to configure the deployment as a Service such as the location of the database, deployment address and port, secret key for encryption and the Google captcha access credentials.

```
database = 'sqlite:///db.sqlite'
port = 5000
host = '0.0.0.0'
application_root = 'image_creation'
secret_key = '_put_here_the_secret_key'
captcha_web_site_key = '_put_captcha_web_site_key'
captcha_site_key='_put_captcha_site_key'
```

5. After setting the configuration values, we need to create the database. To do it, run the following commands in a Python 3 interpreter.

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


## Using the Container Image Creation as Library

To build a container image using the library mode, you have to specify a JSON file with the machine information and the workflow reference (name, step and version) in the Workflow Registry as you do in the CLI. You can also refer to a local workflow indicating the path in your localhost where we can fin the description. In this case, you must also specify a name, step and version to generate an image id to refer to the created image. Moreover you can also indicate if you want to push the generated image to the repository or just keep in your local repository. An example of this JSON file is shown below.


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



## Accessing the Container Image Creation Service with the REST API

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
## Accessing the Container Image Creation Service with the CIC CLI
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

## Debugging the Spack packages

The Container Image Creation uses Spack to install HPC software. Testing the installation of the whole workflow dependencies can take some time. So debugging new packages with the Container Image Creation will be difficult due to the long times to get feedback. For reducing this time, we provide a set of commands to set-up a Docker environment to test the installation in the same way that the CIC does in the service.

```
$ docker run -it -v /path/to/software-catalog/:/software-catalog
-v
/path/to/software/software-catalog/cfg:/root/.spack
--platform linux/amd64 ghcr.io/eflows4hpc/spack_base:0.19.2

$ spack install -v <your package>
```
