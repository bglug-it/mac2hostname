#!/bin/bash

name=mac2hostname
version=1.1.0
tmpdir=/tmp/src_build/${name}-${version}

cwd=$(pwd)
mkdir -p ${tmpdir}
cp mac2hostname mac2hostname.py mac2hostname.ini README.md LICENSE ${tmpdir}
cd ${tmpdir}/..
tar czvf ${cwd}/${name}-${version}.tar.gz ${name}-${version}

# Cleanup
rm -rf /tmp/src_build
