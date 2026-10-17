#!/bin/sh
# Source reconstruction attempt, not a reproducibility claim. Build-time Docker only.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
S="$ROOT/release/native-1.1.2-sources"
IMAGE=sha256:dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0
python3 - "$S" <<'PY'
import json,pathlib,sys,hashlib
s=pathlib.Path(sys.argv[1])
for x in json.loads((s/'alpine-acquisition.json').read_text())['files']:
 assert x['verified'] and hashlib.sha512((s/x['file']).read_bytes()).hexdigest()==x['sha512'],x['file']
for x in json.loads((s/'extra-acquisition.json').read_text()):
 assert hashlib.sha256((s/x['file']).read_bytes()).hexdigest()==x['sha256'],x['file']
PY
docker run --rm -i --cap-drop=ALL --security-opt=no-new-privileges --mount "type=bind,src=$S,dst=/sources,readonly" --entrypoint /bin/sh "$IMAGE" <<'SH'
set -eu
# Do not silently upgrade shared libraries: exact development inputs must match.
apk update
apk add cmake ninja g++ make openssl-dev=3.5.8-r0 zlib-dev=1.3.2-r0 pcre2-dev=10.48-r0 qt6-qtbase-dev=6.11.1-r0 qt6-qtbase-private-dev=6.11.1-r0 qt6-qttools-dev
mkdir /build; cd /build
tar xf /sources/boost_1_86_0.tar.gz
cd boost_1_86_0; ./bootstrap.sh; ./b2 stage --stagedir=./ --with-headers; cd ..
tar xf /sources/libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz
cmake -S libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9 -B libtorrent-build -G Ninja -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_STANDARD=20 -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DBOOST_ROOT=/build/boost_1_86_0/lib/cmake -Ddeprecated-functions=OFF
cmake --build libtorrent-build -j2; cmake --install libtorrent-build
tar xf /sources/qBittorrent-release-5.2.4.tar.gz
# WEBUI must stay ON: upstream switch controls API as well as pages.
cmake -S qBittorrent-release-5.2.4 -B qbt-build -G Ninja -DGUI=OFF -DWEBUI=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DBOOST_ROOT=/build/boost_1_86_0/lib/cmake
cmake --build qbt-build -j2
/build/qbt-build/qbittorrent-nox --version
SH
