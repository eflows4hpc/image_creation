import os
from platform import architecture
import time
import traceback
from xml.etree.ElementTree import PI
import docker
import shutil
import concurrent.futures
import logging

from yaml import full_load

from image_builder import utils

PENDING = 'PENDING'
STARTED = 'STARTED'
BUILDING = 'BUILDING'
CONVERTING = 'CONVERTING'
FINISHED = 'FINISHED'
FAILED = 'FAILED'

APT_GET_INSTALL_COMMAND = "apt-get update && apt-get install -y"
NO_APT_GET = 'echo "Nothing to install from apt-get"'
APT_GET_CLEAN_COMMAND = "apt-get clean all && rm -rf /var/lib/apt/lists/*"
PIP_INSTALL_COMMAND = "python -m pip install --no-cache-dir"
NO_PIP = 'echo "Nothing to install from pip"'


class ImageBuilder:
    def __init__(self, repositories_cfg, builder_cfg, registry_cfg):
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=builder_cfg['max_concurrent_builds'])
        # self.builds= dict()
        self.container_registry = registry_cfg
        self.workflow_repository = repositories_cfg["workflow_repository"]
        self.workflow_default_branch = repositories_cfg.get(
            "default_workflow_repository_branch", "main")
        sr = repositories_cfg["software_repository"]
        if sr.endswith("/"):
            self.software_repository = sr[:-1]
        else:
            self.software_repository = sr
        print("Software Repo: " + str(self.software_repository))
        self.spack_cfg = builder_cfg['spack_cfg']
        self.base_image = builder_cfg['base_image']
        self.images_location = os.path.join(
            builder_cfg["tmp_folder"], "images")
        if not os.path.exists(self.images_location):
            os.makedirs(self.images_location)
        self.builds_location = os.path.join(
            builder_cfg["tmp_folder"], "builds")
        if not os.path.exists(self.builds_location):
            os.makedirs(self.builds_location)
        self.packages_location = os.path.join(
            builder_cfg["tmp_folder"], "packages")
        if not os.path.exists(self.packages_location):
            os.makedirs(self.packages_location)
        self.dockerfile_template = os.path.join(
            builder_cfg["builder_home"], "files", builder_cfg["dockerfile"])
        self.dockerfile_base = os.path.join(
            builder_cfg["builder_home"], "files", "Dockerfile.base")
        self.builder_script = os.path.join(
            builder_cfg["builder_home"], "files", "run_build.sh")
        self.get_workflow_script = os.path.join(
            builder_cfg["builder_home"], "files", "get_workflow.sh")
        self.spack_build_script = os.path.join(
            builder_cfg["builder_home"], "files", "build_spack.sh")
        self.singularity_sudo = builder_cfg['singularity_sudo']

    def _update_dockerfile(self, tmp_folder, step_id, machine, debs, pips):
        # TODO: Change build according to building system (spack/easybuild)
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        to_replace = {"%BASE_IMG%": self.base_image,
                      "%ARCH%": machine['architecture'], "%APPDIR%": step_id, "%CFG_DIR%": self.spack_cfg}
        if debs:
            to_replace['%APTGET_INSTALL%'] = APT_GET_INSTALL_COMMAND + \
                ' ' + ' '.join(debs) + ' && ' + APT_GET_CLEAN_COMMAND
        else :
            to_replace['%APTGET_INSTALL%'] = NO_APT_GET
        if pips:
            to_replace['%PIP_INSTALL%'] = PIP_INSTALL_COMMAND + \
                ' ' + ' '.join(pips)
        else :
            to_replace['%PIP_INSTALL%'] = NO_PIP
        utils.replace_in_file(self.dockerfile_template, dockerfile, to_replace)

    def _get_builder(self, machine):
        if machine['platform'] == 'linux/amd64':
            return "build"
        else:
            return "buildx"

    def _update_configuration(self, workflow_folder_path, machine):
        debs = None
        pips = None
        pip_reqs_path = os.path.join(workflow_folder_path, "requirements.txt")
        environment = {}
        import yaml
        with open(os.path.join(workflow_folder_path, "eflows4hpc.yaml"), 'r') as file:
            eflows_environment = yaml.full_load(file)
        if 'apt' in eflows_environment:
            debs = eflows_environment['apt']
        if 'pip' in eflows_environment:
            pips = eflows_environment['pip']
        elif os.path.exists(pip_reqs_path): 
            pips = ["-r", pip_reqs_path]
        if 'spack' in eflows_environment:
            environment['spack'] = eflows_environment['spack']
            if 'architecture' in machine:
                arch = machine['architecture']
                target = []
                target.append(arch)
                if 'packages' in environment['spack']:
                    if 'all' in environment['spack']['packages']:
                        environment['spack']['packages']['all']['target'] = target
                else:
                    environment['spack']['packages'] = {
                        'all': {'target': target}}
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
            environment['spack']['concretizer'] = {
                'unify': True, 'reuse': True, 
                'targets': {'granularity': 'microarchitectures', 'host_compatible': False}
            }
            environment['spack']['config'] = {
                'shared_linking': {'type': 'runpath'}}
            environment['spack']['view'] = "/opt/view"
            with open(os.path.join(workflow_folder_path, "spack.yaml"), 'w') as file:
                yaml.dump(environment, file, default_flow_style=False)
        return debs, pips

    def _generate_build_environment(self, logger, tmp_folder, workflow, machine, path):
        
        workflow_folder_path = self._get_workflow_version(
            logger, tmp_folder, workflow, path)
        debs, pips = self._update_configuration(workflow_folder_path, machine)
        software_repo_path = os.path.join(
            tmp_folder, os.path.basename(self.software_repository))
        shutil.copy2(self.spack_build_script, tmp_folder)
        shutil.copytree(self.software_repository, software_repo_path)
        spack_cfg_path = os.path.join(tmp_folder, ".spack")
        shutil.copytree(self.spack_cfg, spack_cfg_path)
        packages_path = os.path.join(tmp_folder, "packages")
        shutil.copytree(self.packages_location, packages_path)
        self._update_dockerfile(
            tmp_folder, workflow['step'], machine, debs, pips)

    def _get_workflow_version(self, logger, tmp_folder, workflow, path):
        if path is None:
            branch = workflow.get("version", "latest")
            if branch == "latest":
                branch = self.workflow_default_branch
            command = [self.get_workflow_script, tmp_folder,
                       self.workflow_repository, workflow["name"], workflow["step"], branch]
            logger.info("Getting workflow version")
            utils.run_commands([' '.join(command)],
                           logger=logger, check_error=True)
            return os.path.join(tmp_folder, workflow['step'])
        else:
            workflow_folder_path = os.path.join( tmp_folder, workflow["step"])
            shutil.copytree(path, workflow_folder_path)
            return workflow_folder_path
    

    def _build_image_and_push(self, logger, tmp_folder, workflow, image_id, machine, force, push, path):

        self._generate_build_environment(logger, tmp_folder, workflow, machine, path)
        logger.info("Generating run command")

        build_command = self._get_builder(machine)

        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
                   str(self.container_registry['url']), str(self.container_registry['user']), str(self.container_registry['token']), build_command, str(force), str(push)]
        logger.info("Running build "+  str(command))
        utils.run_commands([' '.join(command)],
                           logger=logger, check_error=True)
        # print("Removing tmp_folder")
        # command = ["rm","-rf", tmp_folder]
        # utils.run_commands([' '.join(command)])

    def _build_base_and_push(self, logger, tmp_folder, image_id, machine, force, push):
        dockerfile = os.path.join(tmp_folder, "Dockerfile")
        shutil.copy(self.dockerfile_base, dockerfile)
        build_command = self._get_builder(machine)
        command = [self.builder_script, image_id, tmp_folder, machine['platform'],
                   str(self.container_registry['url']), str(self.container_registry['user']), str(self.container_registry['token']), build_command, str(force), str(push)]
        logger.info("Running build " + str(command))
        utils.run_commands([' '.join(command)], logger=logger)

    def _to_singularity(self, logger, image_id, singularity_image_path, built):
        if self.container_registry['user'] is None:
            env = os.environ.copy()
        else:
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
            if self.container_registry['user'] is None:
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
            image_id = self.container_registry["images_prefix"] + \
                self._gen_image_name(workflow, machine)
        return image_id

    def _gen_image_name(self, workflow, machine):
        # return workflow['step'] + '_' + machine['architecture'] +':'+ workflow['version']
        image = workflow['name']+ '_' + workflow['step'] + '_' + machine['architecture'] + '_' + self._get_machine_key("mpi", machine) + '_' + self._get_machine_key("gpu", machine) + ":" + workflow['version']
        return image.lower()

    def _get_machine_key(self, key, machine):
        value = machine.get(key, "no"+key)
        if value == "":
            return "no"+key
        return value.replace('@', '_')

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

    def _check_and_build(self, build_id, image_id, workflow, machine, singularity, force, push, tmp_folder, logger, update_build_func, update_image_func, path):
        start_t = time.time()
        if update_build_func:
            update_build_func(id=build_id, status=STARTED)
        try:
            if (force):
                rd = None
            else:
                logger.info("IB: Checking if image " + image_id + " exists")

                client = docker.from_env()
                registry_url=self.container_registry['url']
                try:
                    if registry_url is None:
                        if push:
                            raise Exception("Push is selected but no registry url defined")
                        rd= client.images.get(image_id)
                        logger.info("IB:Image already in the localhost. Nothing to do.")
                    else:
                        username=self.container_registry['user']
                        if username is None:
                            auth_config = None
                        else:
                            auth_config = dict(
                            username=username, password=self.container_registry['token'])
                        rd = client.images.get_registry_data(image_id, auth_config)
                        logger.info("IB:Image already in registry. Nothing to do.")
                except docker.errors.ImageNotFound as ex:
                    logger.info("IB:Image not found: " + str(ex))
                    rd = None
                except docker.errors.NotFound as ex:
                    logger.info("IB:Image not found: " + str(ex))
                    rd = None
            if rd is None:
                logger.info("IB: Building Image")
                if update_build_func:
                    update_build_func(id=build_id, status=BUILDING)
                if workflow.get('step') is None:
                    logger.info("IB: Building Base Image")
                    self._build_base_and_push(
                        logger, tmp_folder, image_id, machine, force, push)
                else:
                    logger.info("IB: Building Image " + str(image_id))
                    self._build_image_and_push(
                        logger, tmp_folder, workflow, image_id, machine, force, push, path)
                built = True
            else:
                built = False
            if singularity:
                image_filename = self._gen_image_name(
                    workflow, machine).replace(":", "_v_") + '.sif'
                singularity_image_path = os.path.join(
                    self.images_location, image_filename)
                if update_build_func:
                    update_build_func(id=build_id, status=CONVERTING, filename=image_filename)
                logger.info(
                    "IB: Checking if image is previously built (" + str(built) + ")")
                if (not os.path.exists(singularity_image_path)) or built:
                    logger.info("IB: Coverting " + image_id + " to Singularity " +
                                singularity_image_path + "(" + str(built) + ")")
                    self._to_singularity(
                        logger, image_id, singularity_image_path, built)
                logger.info("IB: Updating Image")
                if update_image_func:
                    update_image_func(image_id, filename=image_filename)
            end_t = time.time()
            logger.info("IB: Image built")
            if update_build_func:
                update_build_func(id=build_id, status=FINISHED)
        except Exception as e:
            logger.error("Error building request " + str(build_id))
            logger.error(traceback.format_exc())
            if update_build_func:
                update_build_func(id=build_id, status=FAILED, message=str(e))
        end_t = time.time()
        logger.info("IB: Elaspsed time " + str(end_t-start_t) + " seconds.")

    def request_build(self, build_id, image_id, workflow, machine, singularity, force, update_build_func, update_image_func, push=True):
        tmp_folder = self._get_build_folder(build_id)
        os.makedirs(tmp_folder)
        logger = self._gen_logger(build_id)
        self.executor.submit(self._check_and_build, build_id, image_id, workflow,
                             machine, singularity, force, push, tmp_folder, logger, update_build_func, update_image_func, None)

    def get_filename(self, filename):
        if filename is None:
            return None
        else:
            return os.path.join(self.images_location, filename)

    def get_build_logs_path(self, build_id):
        return os.path.join(self._get_build_folder(build_id), 'logs')

    def delete_build(self, build_id):
        # TODO: cancel if running
        tmp_folder = self._get_build_folder(build_id)
        print("Removing tmp_folder")
        command = ["rm", "-rf", tmp_folder]
        utils.run_commands([' '.join(command)])
    
    def delete_build(self, image_id, filename):
        commands = []
        if filename:
            sing_filename = self.get_filename(filename)
            print("Removing sif file" + sing_filename)
            command = ["rm", "-f", sing_filename]
            commands.append(' '.join(command))
        print("Deleting docker image " + image_id)
        command = ["docker", "rmi", image_id]
        commands.append(' '.join(command))
        utils.run_commands(commands)
