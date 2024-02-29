#!/bin/bash -e 

APPDIR=$1
PYTHON_VER=$2
if [ -f "${APPDIR}/spack.yaml" ]; then
    echo "Installing spack packages" 
    spack -C /.spack find 
    cat ${APPDIR}/spack.yaml 
    spack -C /.spack compiler find 
    spack -C /.spack external find 
    spack -C /.spack -e ${APPDIR} install --fail-fast --no-checksum --keep-stage -j2
    # Test with binary caches...
    # spack -C /.spack mirror add binary_mirror_dev https://binaries.spack.io/develop \
    # spack -C /.spack buildcache keys --install --trust \
fi
if [ -f ${APPDIR}/post_inst.sh ]; then
    sh ${APPDIR}/post_inst.sh 
fi
spack gc -y
if [ -f "${APPDIR}/spack.yaml" ]; then
    spack -C /.spack env activate $APPDIR --sh >> /etc/profile.d/z10_spack_environment.sh
fi
echo "export PYTHONPATH=/opt/view/local/lib/python$PYTHON_VER/site-packages/:\$PYTHONPATH" >> /etc/profile.d/z10_spack_environment.sh
echo "export PATH=/usr/local/bin/:\$PATH" >> /etc/profile.d/z10_spack_environment.sh
