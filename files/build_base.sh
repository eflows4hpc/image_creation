#!/bin/bash -e
image_id=$1
platform=$2
build_command=$3
force=$4
if [ "$force" == "True" ]; then
    extra_arg="--no-cache"
fi
if [ "${build_command}" == "buildx" ]; then 
    echo "docker ${build_command} build --push --progress plain ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base ."
    docker ${build_command} build --push --progress plain ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base .
else
    echo "docker ${build_command} ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base ."
    docker ${build_command} ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile.base .
fi



