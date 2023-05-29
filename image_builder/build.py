import os
from platform import architecture
import time
import traceback
import docker
import shutil
import concurrent.futures
import logging

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

    def _generate_build_environment(self, logger, tmp_folder, workflow, machine):
        # TODO add version
        workflow_repo_path = os.path.join(self.workflow_repository,workflow['name'],workflow['step'])
        workflow_folder_path = os.path.join(tmp_folder, workflow['step'])
        logger.info("Copying file " )
        shutil.copytree(workflow_repo_path, workflow_folder_path)
        self._update_configuration(workflow_folder_path, machine)
        software_repo_path = os.path.join(tmp_folder, os.path.basename(self.software_repository))
        shutil.copytree(self.software_repository, software_repo_path)
        spack_cfg_path = os.path.join(tmp_folder, ".spack")
        shutil.copytree(self.spack_cfg, spack_cfg_path)
        packages_path = os.path.join(tmp_folder, "packages")
        shutil.copytree(self.packages_location, packages_path)
        self._update_dockerfile(tmp_folder, workflow['step'], machine)

    def _build_image_and_push(self, logger, tmp_folder, workflow, image_id, machine, force):
 
        self._generate_build_environment( logger, tmp_folder, workflow, machine)
        logger.info("Generating run command")
        
        build_command = self._get_builder(machine)
        
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
            self.container_registry['url'], self.container_registry['user'], self.container_registry['token'], build_command, str(force)]
        logger.info("Running build")
        utils.run_commands([' '.join(command)], logger=logger, check_error=True)
        #print("Removing tmp_folder")
        #command = ["rm","-rf", tmp_folder]
        #utils.run_commands([' '.join(command)])


    def _build_base_and_push(self, logger, tmp_folder, image_id, machine, force):
        os.makedirs(tmp_folder)
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        shutil.copy(self.dockerfile_base, dockerfile)
        build_command = self._get_builder(machine)
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
            self.container_registry['url'], self.container_registry['user'], self.container_registry['token'], build_command, str(force)]
        logger.info("Running build " + str(command))
        utils.run_commands([' '.join(command)], logger=logger)

    def _to_singularity(self, logger, image_id, singularity_image_path, built):
        env = os.environ.copy()
        env['SINGULARITY_DOCKER_USERNAME'] = self.container_registry['user']
        env['SINGULARITY_DOCKER_PASSWORD'] = self.container_registry['token']
        logger.info("Running singularity conversion for image " +
                str(singularity_image_path))
        logger.info("Environ: " + str(env))
        if os.path.exists(singularity_image_path):
            os.remove(singularity_image_path)
        if built:
            source = 'docker-daemon://' + image_id 
        else:
            source = 'docker://' + image_id 
        if self.singularity_sudo:
            command = ['sudo', 'singularity', 'build',
                        singularity_image_path, source]
        else:
            command = ['singularity', 'build',
                        singularity_image_path, source]
        utils.run_commands([' '.join(command)], env=env, logger=logger)
    
    def gen_image_id(self, workflow, machine):
        if workflow['step'] is None:
            image_id = self.base_image
        else:
            image_id = self.container_registry["images_prefix"] + self._gen_image_name(workflow,machine)
        return image_id

    def _gen_image_name(self, workflow, machine):
        #return workflow.name + '_' + workflow.step + '_' + machine.architecture +':'+ workflow.version
        return workflow['step'] + '_' + machine['architecture'] +':'+ workflow['version']

    def _get_build_folder(self, build_id):
        return os.path.join(self.builds_location, build_id)
    
    def _gen_logger(self, build_id):
        logger = logging.getLogger(build_id)
        logger.setLevel(logging.INFO)
        file = self.get_build_logs_path(build_id)
        file_handler = logging.FileHandler(file)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        return logger
    
    def _check_and_build(self, build_id, image_id, workflow, machine, singularity, force, update_build_func, update_image_func):
        start_t = time.time()
        update_build_func(id=build_id, status=STARTED)
        tmp_folder = self._get_build_folder(build_id)
        os.makedirs(tmp_folder)
        logger = self._gen_logger(build_id)
        try:
            if (force):
                rd=None
            else:
                logger.info("IB: Checking if image exists")
            
                client = docker.from_env()
                auth_config = dict(username=self.container_registry['user'], password=self.container_registry['token'])
                try:
                    rd = client.images.get_registry_data(image_id, auth_config)
                    logger.info("IB:Image already in registry. Nothing to do.")
                except docker.errors.NotFound as ex:
                    logger.info("IB:Image not found: " + str(ex))
                    rd=None
            if rd is None:
                logger.info("IB: Building Image")
                update_build_func(id=build_id, status=BUILDING)
                if workflow.get('step') is None:
                    logger.info("IB: Building Base Image")
                    self._build_base_and_push(logger, tmp_folder, image_id, machine, force)
                else:
                    logger.info("IB: Building Image " + str(image_id))
                    self._build_image_and_push(logger,tmp_folder, workflow, image_id, machine, force)
                built=True
            else :
                built=False
            if singularity:
                image_filename = self._gen_image_name(workflow, machine).replace(":","_v_") + '.sif'
                singularity_image_path = os.path.join(self.images_location, image_filename)
                update_build_func(id=build_id, status=CONVERTING, filename=image_filename)
                logger.info("IB: Checking if image is previously built (" + str(built) +")")
                if (not os.path.exists(singularity_image_path)) or built:
                    logger.info("IB: Coverting " + image_id + " to Singularity " + singularity_image_path + "("+ str(built) +")")
                    self._to_singularity(logger,image_id, singularity_image_path, built)
                logger.info("IB: Updating Image")
                update_image_func(image_id, filename=image_filename)
            end_t = time.time()
            logger.info("IB: Image built")
            update_build_func(id=build_id, status=FINISHED)
        except Exception as e:
            logger.error("Error building request " + str(build_id))
            logger.error(traceback.format_exc())
            update_build_func(id=build_id, status= FAILED, message = str(e))
        end_t = time.time()
        logger.info("IB: Elaspsed time " + str(end_t-start_t) + " seconds.")

    def request_build(self, build_id, image_id, workflow, machine, singularity, force, update_build_func, update_image_func):
        
        self.executor.submit(self._check_and_build, build_id, image_id, workflow, machine, singularity, force, update_build_func, update_image_func)

    def get_filename(self, filename):
        if filename is None:
            return None
        else:
            return os.path.join(self.images_location, filename)
    
    def get_build_logs_path(self, build_id):
            return os.path.join(self._get_build_folder(build_id), 'logs')
    
    def delete_build(self, build_id):
        #TODO: cancel if running
        tmp_folder = self._get_build_folder(build_id)
        print("Removing tmp_folder")
        command = ["rm","-rf", tmp_folder]
        utils.run_commands([' '.join(command)])





