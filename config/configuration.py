       
registry_cfg = {
    "url" : "ghcr.io", 
    "user": "_put_username", 
    "token": "_put_token",
    "images_prefix": "ghcr.io/eflows4hpc/"
    }
    
repositories_cfg = {
    "workflow_repository":"/home/jorgee/Shared/Projects/eFlows4HPC/workflow_registry/",
    "software_repository":"/home/jorgee/Shared/Projects/eFlows4HPC/easybuild-tests/software_repo" 
    }

build_cfg = {
    "tmp_folder":"/home/jorgee/tmp", 
    "builder_home": "/home/jorgee/Shared/Projects/eFlows4HPC/git/image_creation/", 
    "base_image": "eflows/spack_base", 
    "dockerfile": "Dockerfile.spack", 
    "spack_cfg":"/home/jorgee/Shared/Projects/eFlows4HPC/easybuild-tests/.spack",
    "max_concurrent_builds" : 3,
    "singularity_sudo" : True
    }

database = 'sqlite:///db.sqlite'

secret_key = '_put_here_the_secret_key'