#!/bin/sh
# Run only inside the isolated qbt-native-113-build container.
set -eux
export PATH=/usr/lib/ninja-build/bin:$PATH
mkdir -p /build /out
cd /build
cmake --version > tool-versions.txt
c++ --version >> tool-versions.txt
ninja --version >> tool-versions.txt
apk info -v libssl3 libcrypto3 >> tool-versions.txt
sha256sum /sources/boost_1_86_0.tar.gz /sources/libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz /sources/qBittorrent-release-5.2.4.tar.gz /sources/aports/qt6-qtbase/* > source-inputs.SHA256
tar xf /sources/boost_1_86_0.tar.gz
tar xf /sources/libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz
cmake -S libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9 -B libtorrent-build -G Ninja -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=20 -DCMAKE_INSTALL_PREFIX=/usr -DBOOST_ROOT=/build/boost_1_86_0 -Ddeprecated-functions=OFF
cmake --build libtorrent-build -j4
cmake --install libtorrent-build
tar xf /sources/qBittorrent-release-5.2.4.tar.gz
cmake -S qBittorrent-release-5.2.4 -B qbt-build -G Ninja -DGUI=OFF -DWEBUI=ON -DCMAKE_BUILD_TYPE=Release -DBOOST_ROOT=/build/boost_1_86_0
cmake --build qbt-build -j4
./qbt-build/qbittorrent-nox --version
cp qbt-build/qbittorrent-nox /out/
sha256sum /out/qbittorrent-nox >/out/SHA256SUMS
ldd /out/qbittorrent-nox >/out/ldd.txt
