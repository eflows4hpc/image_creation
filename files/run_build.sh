#!/bin/bash -e
image_id=$1
tmpdir=$2
platform=$3
cont_registry=$4
cr_username=$5
cr_passwd=$6
build_command=$7

cd $tmpdir
echo ${cr_passwd} | docker login ${cont_registry}  --username ${cr_username} --password-stdin
echo "docker ${build_command} --platform ${platform} --rm -t ${image_id} -f Dockerfile ."
docker ${build_command} --platform ${platform} --rm -t ${image_id} -f Dockerfile .
docker push ${image_id}



