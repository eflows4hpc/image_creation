# image_creation
Service for creating container images for eFlows4HPC platform

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

