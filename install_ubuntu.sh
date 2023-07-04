#!/bin/sh -e
# Tested in Ubuntu 22.04
apt-get update

# 1. Install Docker
apt-get install -y ca-certificates curl gnupg 
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg 
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce-cli docker-buildx-plugin 

# 2. Install Singularity
apt-get install -y \
   build-essential \
   libseccomp-dev \
   libglib2.0-dev \
   pkg-config \
   squashfs-tools \
   cryptsetup \
   runc \
   wget \
   git \
   golang-go

export VERSION=3.10.0 
wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    tar -xzf singularity-ce-${VERSION}.tar.gz && \
    cd singularity-ce-${VERSION}

./mconfig && \
    make -C ./builddir && \
    make -C ./builddir install

rm singularity-ce-${VERSION}*

# install python3 and pip
apt-get install -y python3 python3-dev python3-pip
apt-get autoclean && \
rm -rf /var/lib/apt/lists/* 



