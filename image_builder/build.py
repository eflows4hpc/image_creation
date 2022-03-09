
import os
import uuid
import docker
import shutil
import concurrent.futures

from image_builder import utils

PENDING='PENDING'
STARTED='STARTED'
BUILDING='BUILDING'
CONVERTING='CONVERTING'
FINISHED='FINISHED'
FAILED = 'FAILED'

class Build:
    status = PENDING
    image_id = None
    filename = None
    message = None

class ImageBuilder:
    def __init__(self, repositories_cfg, builder_cfg, registry_cfg):
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=builder_cfg['max_concurrent_builds'])
        self.builds= dict()
        self.workflow_repository = repositories_cfg["workflow_repository"]
        self.software_repository = repositories_cfg["software_repository"]
        self.spack_cfg = builder_cfg['spack_cfg']
        self.base_image = builder_cfg['base_image']
        #self.builder_cfg = builder_cfg
        self.container_registry = registry_cfg
        self.images_location = os.path.join(builder_cfg["tmp_folder"], "images")
        if not os.path.exists(self.images_location):
            os.makedirs(self.images_location)
        self.builds_location = os.path.join(builder_cfg["tmp_folder"], "builds")
        if not os.path.exists(self.builds_location):
            os.makedirs(self.builds_location)
        self.dockerfile_template =  os.path.join(builder_cfg["builder_home"], "files", builder_cfg["dockerfile"])
        self.builder_script = os.path.join(builder_cfg["builder_home"], "files", "run_build.sh")
        self.singularity_sudo = builder_cfg['singularity_sudo'] 
    

    def _generate_build_env(self, tmp_folder, step_id, machine):
        #TODO: Change build according to building system (spack/easybuild)
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        to_replace = {"%BASE_IMG%": self.base_image,"%ARCH%": machine['architecture'], "%APPDIR%": step_id, "%CFG_DIR%": self.spack_cfg}
        utils.replace_in_file(self.dockerfile_template, dockerfile, to_replace)
        #TODO: Check architecture and pass te corresponding build command (build or buildx)
        return "build"

    def _build_image_and_push(self, tmp_folder, workflow, step_id, image_id, machine):
        os.makedirs(tmp_folder)
        workflow_repo_path = os.path.join(self.workflow_repository,workflow,step_id)
        workflow_folder_path = os.path.join(tmp_folder, step_id)
        shutil.copytree(workflow_repo_path, workflow_folder_path)
        software_repo_path = os.path.join(tmp_folder, os.path.basename(self.software_repository))
        shutil.copytree(self.software_repository, software_repo_path)
        spack_cfg_path = os.path.join(tmp_folder, os.path.basename(self.spack_cfg))
        shutil.copytree(self.spack_cfg, spack_cfg_path)

        build_command = self._generate_build_env(tmp_folder, step_id, machine)
        
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
            self.container_registry['url'], self.container_registry['user'], self.container_registry['token'], build_command]
        print("Running build")
        utils.run_commands([' '.join(command)])

    def _to_singularity(self, image_id, singularity_image_path, built):
        if (not os.path.exists(singularity_image_path)) or built:
            if os.path.exists(singularity_image_path):
                os.remove(singularity_image_path)
            if built:
                source = 'docker-daemon://' + image_id +":latest"
            else:
                source = 'docker://' + image_id + ":latest"
            if self.singularity_sudo :
                command = ['sudo', 'singularity', 'build', singularity_image_path ,source]
            else:
                command = ['singularity', 'build', singularity_image_path ,source]
            utils.run_commands([' '.join(command)])

    def _check_and_build(self, build_id, workflow, step_id, machine, singularity, force):
        current_build = self.builds[build_id]
        current_build.status=STARTED
        image_id = self.container_registry["images_prefix"] + step_id + '_' + machine["architecture"]
        current_build.image_id = image_id
        tmp_folder = os.path.join(self.builds_location, build_id)
        try:
            if (force):
                rd=None
            else:
                print("IB: Checking if image exists")
            
                client = docker.from_env()
                auth_config = dict(username=self.container_registry['user'], password=self.container_registry['token'])
                try:
                    rd = client.images.get_registry_data(image_id, auth_config)
                    print("IB:Image already in registry. Nothing to do.")
                except docker.errors.NotFound as ex:
                    print("IB:Image not found: " + str(ex))
                    rd=None
            if rd is None:
                print("IB: Building Image")
                current_build.status = BUILDING
                self._build_image_and_push(tmp_folder, workflow, step_id, image_id, machine)
                built=True
            else :
                built=False
            if singularity:
                image_filename = step_id + '_' + machine["architecture"] + '.sif'
                singularity_image_path = os.path.join(self.images_location, image_filename)
                current_build.status = CONVERTING
                print("IB: Coverting to Singularity")
                self._to_singularity(image_id, singularity_image_path, built)
                current_build.filename = image_filename
            print("IB: Image built")
            current_build.status = FINISHED
        except Exception as e:
            current_build.status = FAILED
            current_build.message = str(e)

    def request_build(self, workflow, step_id, machine, singularity, force):
        build_id = str(uuid.uuid4())
        built = Build()
        self.builds[build_id] = built
        self.executor.submit(self._check_and_build, build_id, workflow, step_id, machine, singularity, force)
        return build_id
    
    def check_build(self, build_id):
        built = self.builds[build_id]
        return {"status" : built.status, "image_id" : built.image_id , "filename": built.filename, "message": built.message }

    def get_filename(self, filename):
        if filename is None:
            return None
        else:
            return os.path.join(self.images_location, filename)





