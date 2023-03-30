import os
from platform import architecture
import time
import traceback
import docker
import shutil
import concurrent.futures

from yaml import full_load

from image_builder import utils

PENDING='PENDING'
STARTED='STARTED'
BUILDING='BUILDING'
CONVERTING='CONVERTING'
FINISHED='FINISHED'
FAILED = 'FAILED'



class ImageBuilder:
    def __init__(self, repositories_cfg, builder_cfg, registry_cfg):
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=builder_cfg['max_concurrent_builds'])
        #self.builds= dict()
        self.container_registry = registry_cfg
        self.workflow_repository = repositories_cfg["workflow_repository"]
        sr = repositories_cfg["software_repository"]
        if sr.endswith("/"):
            self.software_repository = sr[:-1]
        else:
            self.software_repository = sr
        print("Software Repo: " + str(self.software_repository))
        self.spack_cfg = builder_cfg['spack_cfg']
        self.base_image = self.container_registry["images_prefix"] + builder_cfg['base_image']
        self.images_location = os.path.join(builder_cfg["tmp_folder"], "images")
        if not os.path.exists(self.images_location):
            os.makedirs(self.images_location)
        self.builds_location = os.path.join(builder_cfg["tmp_folder"], "builds")
        if not os.path.exists(self.builds_location):
            os.makedirs(self.builds_location)
        self.packages_location = os.path.join(builder_cfg["tmp_folder"], "packages")
        if not os.path.exists(self.packages_location):
            os.makedirs(self.packages_location)
        self.dockerfile_template =  os.path.join(builder_cfg["builder_home"], "files", builder_cfg["dockerfile"])
        self.dockerfile_base =  os.path.join(builder_cfg["builder_home"], "files", "Dockerfile.base")
        self.builder_script = os.path.join(builder_cfg["builder_home"], "files", "run_build.sh")
        self.singularity_sudo = builder_cfg['singularity_sudo'] 
    

    def _update_dockerfile(self, tmp_folder, step_id, machine):
        #TODO: Change build according to building system (spack/easybuild)
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        to_replace = {"%BASE_IMG%": self.base_image,"%ARCH%": machine['architecture'], "%APPDIR%": step_id, "%CFG_DIR%": self.spack_cfg}
        utils.replace_in_file(self.dockerfile_template, dockerfile, to_replace)
       
    def _get_builder(self, machine):
        print("Platform is " +str(machine['platform']))
        if machine['platform'] == 'linux/amd64':
            return "build"
        else:
            return "buildx build"
    

    def _update_configuration(self, workflow_folder_path, machine):
        
        import yaml
        with open(os.path.join(workflow_folder_path,"spack.yaml"),'r') as file:
            environment = yaml.full_load(file)
        if 'spack' in environment:
            if 'architecture' in machine:
                arch = machine['architecture']
                target = []
                target.append(arch)
                if 'packages' in environment['spack']:
                    if 'all' in environment['spack']['packages']:
                        environment['spack']['packages']['all']['target'] = target
                else:
                    environment['spack']['packages']={'all': {'target': target }}
            if 'mpi' in machine:
                if 'specs' in environment['spack']:
                    environment['spack']['specs'].append(machine['mpi'])
                else:
                    environment['spack']['specs'] = [machine['mpi']]
            if 'gpu' in machine:
                if 'specs' in environment['spack']:
                    environment['spack']['specs'].append(machine['gpu'])
                else:
                    environment['spack']['specs'] = [machine['gpu']]
            environment['spack']['concretizer'] = {'unify': True}
            environment['spack']['view'] = "/opt/view"
        else:
            raise Exception("Incorrect spack environment. Not containing the spack tag.")
        with open(os.path.join(workflow_folder_path,"spack.yaml"),'w') as file:
            yaml.dump(environment, file, default_flow_style=False)

    def _generate_build_environment(self, tmp_folder, workflow, step_id, machine):
        print("Creating " + tmp_folder)
        os.makedirs(tmp_folder)
        workflow_repo_path = os.path.join(self.workflow_repository,workflow,step_id)
        workflow_folder_path = os.path.join(tmp_folder, step_id)
        print("Copying file " )
        shutil.copytree(workflow_repo_path, workflow_folder_path)
        self._update_configuration(workflow_folder_path, machine)
        software_repo_path = os.path.join(tmp_folder, os.path.basename(self.software_repository))
        shutil.copytree(self.software_repository, software_repo_path)
        spack_cfg_path = os.path.join(tmp_folder, ".spack")
        shutil.copytree(self.spack_cfg, spack_cfg_path)
        packages_path = os.path.join(tmp_folder, "packages")
        shutil.copytree(self.packages_location, packages_path)
        self._update_dockerfile(tmp_folder, step_id, machine)

    def _build_image_and_push(self, tmp_folder, workflow, step_id, image_id, machine, force):
 
        self._generate_build_environment(self, tmp_folder, workflow, step_id, machine)
        print("Generating run command")
        
        build_command = self._get_builder(machine)
        
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
            self.container_registry['url'], self.container_registry['user'], self.container_registry['token'], build_command, str(force)]
        print("Running build")
        utils.run_commands([' '.join(command)])
        print("Removing tmp_folder")
        command = ["rm","-rf", tmp_folder]
        utils.run_commands([' '.join(command)])


    def _build_base_and_push(self, tmp_folder, image_id, machine, force):
        os.makedirs(tmp_folder)
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        shutil.copy(self.dockerfile_base, dockerfile)
        build_command = self._get_builder(machine)
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
            self.container_registry['url'], self.container_registry['user'], self.container_registry['token'], build_command, str(force)]
        print("Running build " + str(command))
        utils.run_commands([' '.join(command)])

    def _to_singularity(self, image_id, singularity_image_path, built):
        print ("Checking if image is previously built (" + str(built) +")")
        if (not os.path.exists(singularity_image_path)) or built:
            env = os.environ.copy()
            env['SINGULARITY_DOCKER_USERNAME'] = self.container_registry['user']
            env['SINGULARITY_DOCKER_PASSWORD'] = self.container_registry['token']
            print("Running singularity conversion for image " +  str(singularity_image_path))
            print("Environ: " + str(env))
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
            utils.run_commands([' '.join(command)], env=env)
    
    def _check_and_build(self, build_id, workflow, step_id, machine, singularity, force, update_build_func):
        start_t = time.time()
        if step_id is None:
            image_id = self.base_image
        else:
            image_id = self.container_registry["images_prefix"] + step_id + '_' + machine["architecture"]
        update_build_func(id=build_id, status=STARTED, image=image_id)
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
                update_build_func(id=build_id, status=BUILDING)
                if step_id is None:
                    print("IB: Building Base Image")
                    self._build_base_and_push(tmp_folder, image_id, machine, force)
                else:
                    print("IB: Building Image " + str(image_id))
                    self._build_image_and_push(tmp_folder, workflow, step_id, image_id, machine, force)
                built=True
            else :
                built=False
            if singularity:
                image_filename = step_id + '_' + machine["architecture"] + '.sif'
                singularity_image_path = os.path.join(self.images_location, image_filename)
                update_build_func(id=build_id, status=CONVERTING, filename=image_filename)
                print("IB: Coverting " + image_id + " to Singularity " + singularity_image_path + "("+ str(built) +")")
                self._to_singularity(image_id, singularity_image_path, built)
            end_t = time.time()
            print("IB: Image built")
            update_build_func(id=build_id, status=FINISHED)
        except Exception as e:
            print(traceback.format_exc())
            update_build_func(id=build_id, status= FAILED, message = str(e))
        end_t = time.time()
        print("IB: Elaspsed time " + str(end_t-start_t) + " seconds.")

    def request_build(self, build_id, workflow, step_id, machine, singularity, force, update_build_func):
        self.executor.submit(self._check_and_build, build_id, workflow, step_id, machine, singularity, force, update_build_func)

    def get_filename(self, filename):
        if filename is None:
            return None
        else:
            return os.path.join(self.images_location, filename)





