#!/bin/sh
# Build-only container; no container dependency on installed NAS.
# Tested against retained 1.1.3 build tree. No offline/bit-identical guarantee.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CONTAINER=${BUILD_CONTAINER:-qbt-native-113-build}
S="$ROOT/release/native-1.1.4-sources"
python3 - "$S" <<'PY'
import pathlib,json,hashlib,sys
s=pathlib.Path(sys.argv[1])
for row in json.loads((s/'source-verification.json').read_text()):
 p=s/row['file'];assert hashlib.sha512(p.read_bytes()).hexdigest()==row['sha512'],p
for row in json.loads((s/'build/apk-acquisition.json').read_text()):
 assert hashlib.sha256((s/row['file']).read_bytes()).hexdigest()==row['sha256']
PY
docker start "$CONTAINER" >/dev/null
docker cp "$S/build/apks/." "$CONTAINER:/locked-apks"
# Targeted verified extraction supplies actual LinguistTools/patch files, avoiding
# irrelevant GUI/QML dev dependencies. Explicitly NOT a complete apk transaction.
docker exec "$CONTAINER" sh -ec '
 for a in /locked-apks/qt6-qttools-dev-*.apk /locked-apks/patch-*.apk; do tar xzf "$a" -C /; done
 export PATH=/usr/lib/ninja-build/bin:$PATH
 test -f /usr/lib/cmake/Qt6LinguistTools/Qt6LinguistToolsConfig.cmake
 /usr/lib/qt6/bin/lrelease -version
 test -f /build/boost_1_86_0/boost/version.hpp
 cmake -S /build/libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9 -B /build/libtorrent-build -G Ninja -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 -DCMAKE_INSTALL_PREFIX=/usr -DBOOST_ROOT=/build/boost_1_86_0 -Ddeprecated-functions=OFF
 cmake --build /build/libtorrent-build -j4
 cmake --install /build/libtorrent-build
 cmake -S /build/qBittorrent-release-5.2.4 -B /build/qbt-build -G Ninja -DGUI=OFF -DWEBUI=ON -DCMAKE_BUILD_TYPE=Release -DBOOST_ROOT=/build/boost_1_86_0
 cmake --build /build/qbt-build -j4
 /build/qbt-build/qbittorrent-nox --version
 cp /build/qbt-build/qbittorrent-nox /out/qbittorrent-nox
 sha256sum /out/qbittorrent-nox
 '
# Full clean-tree extraction/compile command is retained in source_build_1_1_3.sh;
# this entry point validates and executes existing-tree rebuild and bootstrap fix.
