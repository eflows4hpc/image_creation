
import uuid
import traceback
import argparse
import json
import os
import logging
import sys

from config import configuration
from image_builder.build import ImageBuilder 
from image_builder.utils import check_bool, check_machine 

builder = ImageBuilder(configuration.repositories_cfg, configuration.build_cfg, configuration.registry_cfg)


def image_path (name):
    return builder.get_filename(name)

def build_image (workflow_name, step_id, version, machine, force, push, path):
    try:
        if machine['container_engine'] == 'singularity':
            singularity = True
        else:
            singularity = False
        
        if workflow_name == 'BASE' and step_id == 'BASE':
            workflow_name = None
            step_id = None
        if version is None:
            version = 'latest'
        workflow = {"name" : workflow_name, "step" : step_id, "version" : version}
        check_machine(machine)
        image_id = builder.gen_image_id(workflow, machine)
        build_id = str(uuid.uuid4())
        tmp_folder = builder._get_build_folder(build_id)
        os.makedirs(tmp_folder)
        logger = logging.getLogger()
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.INFO)
        builder._check_and_build(build_id, image_id, workflow, machine,
                              singularity, force, push, tmp_folder, logger, None, None, path)
    except Exception as e:
        print(traceback.format_exc())
        raise e


def read_json_and_build(content):
    force = check_bool(content, 'force', False)
    push = check_bool(content, 'push', True)
    machine = content['machine']
    workflow = content['workflow']
    step_id = content['step_id']
    path = content.get('path', None)
    version = content.get('version', 'latest')
    build_image(workflow, step_id, version, machine, force, push, path)

if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-r", "--request", help="JSON file with the request",)
    args = argParser.parse_args()
    json_file = args.request
    if json_file is None:
        print("Requires to pass a request with --request")
        exit(1)
    with open(json_file) as f:
        content = json.load(f)
        read_json_and_build(content)

