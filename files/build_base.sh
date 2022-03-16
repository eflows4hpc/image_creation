#!/bin/bash -e
image_id=$1
platform=$2
build_command=$3


echo "docker ${build_command} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base ."
docker ${build_command} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base .




