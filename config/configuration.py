       
registry_cfg = {
    "url" : "ghcr.io", 
    "user": "_put_username", 
    "token": "_put_token",
    "images_prefix": "ghcr.io/eflows4hpc/"
    }
    
repositories_cfg = {
    "workflow_repository":"https://github.com/eflows4hpc/workflow-registry.git", 
    "software_repository":"/path/to/software-catalog/" 
    }

build_cfg = {
    "tmp_folder":"/path/to/tmp", 
    "builder_home": "/path/to/image_creation/", 
    "base_image": "spack_base", 
    "dockerfile": "Dockerfile.spack", 
    "spack_cfg":"/path/to/software-catalog/cfg",
    "max_concurrent_builds" : 3,
    "singularity_sudo" : True
    }

database = 'sqlite:///db.sqlite'
port = 5000
host = '0.0.0.0'
application_root = 'image_creation'
secret_key = '_put_here_the_secret_key'
