FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y ca-certificates curl gnupg wget git vim \
   build-essential libseccomp-dev libglib2.0-dev pkg-config squashfs-tools cryptsetup runc golang-go \
   python3 python3-dev python3-pip && apt-get autoclean && rm -rf /var/lib/apt/lists/*
   
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \ 
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && apt-get install -y docker-ce-cli docker-buildx-plugin && apt-get autoclean && rm -rf /var/lib/apt/lists/* 

RUN export VERSION=3.10.0 && wget https://github.com/sylabs/singularity/releases/download/v${VERSION}/singularity-ce-${VERSION}.tar.gz && \
    tar -xzf singularity-ce-${VERSION}.tar.gz && \
    cd singularity-ce-${VERSION} && \
    ./mconfig && \
    make -C ./builddir && \
    make -C ./builddir install && \
    cd .. && rm -r singularity-ce-${VERSION}* 

RUN git clone https://github.com/eflows4hpc/image_creation.git /image_creation && mv /image_creation/config/configuration.docker.py /image_creation/config/configuration.py && pip3 --no-cache-dir install -r /image_creation/requirements-library.txt
RUN git clone https://github.com/eflows4hpc/software-catalog.git /software-catalog

ENV PYTHONPATH=/image_creation:$PYTHONPATH

