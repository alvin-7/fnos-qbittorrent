#!/bin/sh
# Isolated source-built Qt replacement, same 6.11.1 SONAME; not old OCI reproduction.
set -eux
export PATH=/usr/lib/ninja-build/bin:$PATH
cd /build
tar xf /sources/aports/qt6-qtbase/qtbase-everywhere-src-6.11.1.tar.xz
cd qtbase-everywhere-src-6.11.1
for p in 0001-qt6-qtbase-lfs64.patch 0002-qt6-qtbase-dns-resolver.patch symlinks.patch; do patch -p1 < /sources/aports/qt6-qtbase/$p; done
cmake -S . -B /build/qt-replacement -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/qt-replacement -DQT_BUILD_TESTS=OFF -DQT_BUILD_EXAMPLES=OFF -DQT_FEATURE_gui=OFF -DQT_FEATURE_widgets=OFF -DQT_FEATURE_openssl_linked=ON -DQT_FEATURE_libproxy=ON -DQT_FEATURE_reduce_relocations=OFF -DQT_FEATURE_relocatable=ON -DQT_FEATURE_dbus=OFF -DQT_FEATURE_icu=ON
cmake --build /build/qt-replacement -j4
cmake --install /build/qt-replacement
sha256sum /opt/qt-replacement/lib/libQt6Core.so.6.11.1 /opt/qt-replacement/lib/libQt6Network.so.6.11.1 /opt/qt-replacement/lib/libQt6Xml.so.6.11.1 >/build/qt-replacement.SHA256
