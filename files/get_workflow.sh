#!/bin/bash -e
tmp_folder=$1
workflow_registry=$2
name=$3
step=$4
version=$5
echo "Obtaining workflow ${name}/${step} branch ${version} form ${workflow_registry}"
echo "git clone --single-branch --branch ${version} ${workflow_registry} ${tmp_folder}/.workflow_registry"
git clone --single-branch --branch ${version} ${workflow_registry} ${tmp_folder}/.workflow_registry
mv ${tmp_folder}/.workflow_registry/${name}/${step} ${tmp_folder}/${step}
echo "Removing downloaded registry"
rm -rf ${tmp_folder}/.workflow_registry







