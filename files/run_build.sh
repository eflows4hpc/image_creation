#!/bin/bash -e
image_id=$1
tmpdir=$2
platform=$3
cont_registry=$4
cr_username=$5
cr_passwd=$6
build_command=$7
force=$8
push=$9
if [ "$force" == "True" ]; then
    extra_arg="--no-cache"
fi
cd $tmpdir
echo ${cr_passwd} | docker login ${cont_registry}  --username ${cr_username} --password-stdin
if [ "${build_command}" == "buildx" ]; then 
    if [ "$push" == "True" ]; then
        push_flag="--push"
    else 
        push_flag="--save"
    fi
    echo "docker ${build_command} build --progress plain --builder mybuilder ${extra_arg} --platform ${platform} ${push_flag} --rm -t ${image_id} -f Dockerfile ."
    docker ${build_command} build --progress plain --builder mybuilder ${extra_arg} --platform ${platform} ${push_flag} --rm -t ${image_id} -f Dockerfile .
else
    echo "docker ${build_command} ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile ."
    docker ${build_command} ${extra_arg} --platform ${platform} --rm -t ${image_id} -f Dockerfile .
    if [ "$push" == "True" ]; then
       docker push ${image_id}
    fi
fi


