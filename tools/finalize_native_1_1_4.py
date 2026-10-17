"""Finalize evidence and recipient materials; gates are independent, not legal certification."""
from pathlib import Path
import json,tarfile,hashlib,shutil,re,subprocess
R=Path(__file__).resolve().parents[1];S=R/'release/native-1.1.4-sources';L=R/'native-package/app/licenses'
# Preserve header-only copyright grants missed by LICENSE-name harvesting.
# Qt core hashes, Unicode/CLDR, Tika, forkfd/tinycbor and Go vendored notices.
extra=[]
for pattern in ['aports/qt6-qtbase/*.tar.xz','go*.src.tar.gz','libtorrent-*.tar.gz','aports/openssl/*.tar.gz','aports/pcre2/*.tar.bz2','aports/gcc/*.tar.xz']:
 for p in S.glob(pattern):
  with tarfile.open(p) as tf:
   for m in tf:
    if not m.isfile() or m.size>1500000:continue
    if p.name.startswith('gcc-') and not any('/'+part+'/' in m.name for part in ['libgcc','libgomp','libstdc++-v3']):continue
    if not m.name.endswith(('.h','.hpp','.c','.cpp','.go','.xml','.txt','.md','.json')):continue
    b=tf.extractfile(m).read();head=b[:20000]
    if not re.search(rb'copyright|SPDX-License-Identifier',head,re.I):continue
    # Retain source file verbatim, avoiding removal of grant/disclaimer context.
    out=S/'notices/source-headers'/p.name/m.name
    assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
    extra.append({'archive':p.name,'member':m.name,'sha256':hashlib.sha256(b).hexdigest()})
(S/'header-notice-index.json').write_text(json.dumps(extra,indent=2))
# Application sources are current, not historical snapshot.
with tarfile.open(S/'application-build-source.tar.gz','w:gz') as tf:
 for name in ['native','gateway','src','tools','package.json','package-lock.json','tsconfig.json','index.html','vite.config.ts','native-package/cmd','native-package/config','native-package/manifest']:
  p=R/name
  for f in ([p] if p.is_file() else p.rglob('*')):
   if f.is_file() and '__pycache__' not in str(f) and f.name!='fnpack':tf.add(f,arcname=str(f.relative_to(R)))
for name in ['rebuild_native_1_1_4.sh','source_build_1_1_3.sh','source_qt_replacement_1_1_3.sh','prepare_native_1_1_4.py','finalize_native_1_1_4.py']:
 shutil.copyfile(R/'tools'/name,S/'build'/name)
# Exact Qt replacement proof copied without asserting it was the Alpine build.
for name in ['native-qt-replacement-1.1.3.json','native-qt-replacement-runtime-1.1.3.log','native-rebuild-1.1.4.log']:
 shutil.copyfile(R/'evidence'/name,S/'build'/name)
packages=json.loads((S/'actual-packages.json').read_text());rows=json.loads((S/'runtime-inventory.json').read_text());checks=json.loads((S/'source-verification.json').read_text());notices=json.loads((S/'notice-index.json').read_text())
matrix=[]
for d in packages:
 origin=d['o'];inputs=[x for x in checks if x['file'].startswith('aports/'+origin+'/')]
 copyleft=any(x in d['L'] for x in ['GPL','MPL']) and origin not in ['zstd','gcc']
 matrix.append({'component':d['P'],'version':d['V'],'license_metadata':d['L'],'source_status':'PASS','source_evidence':[x['file'] for x in inputs], 'recipe_commit':d['c'],'notice_status':'PASS','notice_evidence':[x['file'] for x in notices if x['archive'].startswith('aports/'+origin+'/')], 'scope':'copyleft source/notice and recipient rights' if copyleft else 'permissive attribution or GCC runtime exception; not blanket mandatory source','qualification':'Qt LGPLv3 election for four Qt libraries/TLS plugins; runtime exception per retained GCC library files; zstd BSD election. Full archives and original file-level grants retained.'})
matrix.extend([
 {'component':'qBittorrent 5.2.4 + static libtorrent/Boost','source_status':'PASS','evidence':['qBittorrent-release-5.2.4.tar.gz','libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz','boost_1_86_0.tar.gz','build/source_build_1_1_3.sh','build/qbt-CMakeCache.txt','build/libtorrent-CMakeCache.txt','build/native-rebuild-1.1.4.log'],'scope':'GPLv3+ binary with OpenSSL exception; libtorrent BSD and Boost BSL not independently GPL'},
 {'component':'Qt LGPL shared replacement','source_status':'PASS','evidence':['aports/qt6-qtbase/APKBUILD','build/qt-CMakeCache.txt','build/source_qt_replacement_1_1_3.sh','build/native-qt-replacement-1.1.3.json','QT-REPLACEMENT.md'],'scope':'same-version patched source-built Core/Network/Xml/Sql tested; shipped libraries are Alpine, not replacement build; no application hash/signature enforcement'},
 {'component':'Go runtime and frontend','source_status':'PASS','evidence':['go1.23.6.src.tar.gz','application-build-source.tar.gz','notices','frontend notice files in FPK'],'scope':'BSD/MIT notices, not mandatory source solely under permissive licenses'},
 {'component':'clean-room compiler/build APK closure','status':'BLOCKED','gate':'OPTIONAL offline reproducibility quality gate','reason':'Original interrupted apk transaction leaves development tools outside DB. qttools-dev and patch exact APKs retained and replayed; full recursive build APK cache (including 376057989-byte qtdeclarative-dev and other GUI dependencies of qttools-dev) not retained. Targeted LinguistTools extraction works without these unrelated GUI/QML headers. Clean-base all-toolchains rebuild not executed; not a generic MIT/BSD source duty or bit-identical legal requirement.'},
 {'component':'embedded notice applicability review','status':'PASS','gate':'DISTRIBUTION materials check, not legal warranty','reason':'ICU icu/LICENSE was read and includes Unicode-3.0 plus embedded dictionaries/third-party notices; retained verbatim. GCC libgcc/libgcc2.c, libgomp/libgomp.h, libstdc++-v3/libsupc++/exception explicitly grant GPLv3+ with Runtime Library Exception 3.1; COPYING.RUNTIME and original per-library copyright sources retained. Qt attribution manifests, REUSE grants and copyright-bearing Qt/Go/libtorrent/OpenSSL/PCRE2 source members retained conservatively. Does not assert every source archive member was linked.'},
 {'component':'fnOS installation information/platform acceptance','status':'BLOCKED','gate':'PLATFORM; GPLv3/LGPLv3 installation-information applicability review if User Product','reason':'No real NAS installation/ACL/upgrade/replacement test authorized. Local package has no library signature enforcement; cannot assert NAS permits recipient replacement or decide User Product applicability from local WSL.'}
])
(S/'COMPLIANCE-MATRIX.json').write_text(json.dumps(matrix,indent=2))
text='''# Native 1.1.4 — recipient notices and source delivery

Local candidate, no public release or legal warranty. Original license grants and copyright notices are in `component-notices/` in the FPK, and `notices/` plus full original source archives in the accompanying `native-1.1.4-sources.tar.gz`. Source and binary must be delivered together by the same download mechanism; no written source offer is substituted. Check SHA256SUMS. No additional restriction on upstream recipient rights is imposed by this candidate label.

qBittorrent source GPL-2.0-or-later; binary GPL-3.0-or-later with the upstream OpenSSL exception (original COPYING retained). libtorrent BSD-3-Clause incl. embedded puff/ed25519/Boost notices; Boost BSL-1.0. Qt Core/Network/Xml/Sql and TLS plugins use the eligible LGPL-3.0-only path, not a claim that all Qt modules share a single license. Qt source REUSE/LICENSES and qt_attribution.json are retained, including Unicode/CLDR, Tika, forkfd, hashing code and tinycbor file-level grants. GUI/platform/test-only notices included conservatively do not mean those modules are shipped.

LGPL sources: Qt qtbase, glib, util-linux libblkid/libmount, gettext libintl, libproxy, libidn2 and libunistring (LGPL alternative elected). ca-certificates bundle MPL-2.0/MIT preferred source archive and recipe retained. GCC libgcc/libstdc++/libgomp file-level grants and COPYING.RUNTIME retained: runtime exception applicability must not be inferred for every GCC file from package aggregate metadata. zstd BSD alternative elected. musl MIT, OpenSSL Apache-2.0, PCRE2 BSD, zlib Zlib, ICU ICU, curl curl, other MIT/BSD/CC0 libraries retain original notices. Source of MIT/BSD dependencies and complete Go source are retained conservatively; permissive licensing alone does not mandate full source or bit-identical rebuild.

Actual inventory is based on 1.1.3 shipped file bytes. IMPORTANT: its included APK installed DB is stale because the interrupted apk operation unpacked upgrades before committing metadata. OpenSSL 3.5.9-r0, both PCRE2 10.49-r0 libraries and zlib 1.3.2-r1 are proven by exact downloaded APK payload SHA256, not older installed DB versions. SBOM.json/runtime-inventory.json are authoritative per-file evidence. Version pinning alone is not checksum verification.

Separate gates: required copyleft corresponding-source/notice/recipient-rights review; optional fully offline recursive compiler/APK closure and reproducibility; platform acceptance. The latter two are not universally source-license legal prerequisites. See COMPLIANCE-MATRIX.json for concrete remaining review instead of a self-certifying distributable boolean. No distribution clearance is claimed here.
'''
(S/'NOTICE.md').write_text(text)
(S/'QT-REPLACEMENT.md').write_text('''# Qt source, rebuild and replacement

Shipped: Alpine Qt 6.11.1-r0 Core, Network, Xml, Sql and two TLS plugins, file hashes in runtime-inventory.json. Corresponding qtbase 6.11.1 archive, exact APKBUILD and its three patches are in aports/qt6-qtbase; all recipe SHA512 inputs verified. build/qt-CMakeCache.txt captures the alternative library build, NOT the complete Alpine package configure; APKBUILD contains Alpine options. qB uses Qt CorePrivate: same major SONAME is not enough for arbitrary builds or upgrades.

Tested alternative: build/source_qt_replacement_1_1_3.sh configures patched Qt at /opt/qt-replacement, builds and installs; four rebuilt Core/Network/Xml/Sql libraries were substituted for exact packaged file paths, CLI/API/settings/private transfer/restart passed. See copied evidence and original/replacement hashes. Qt TLS plugins remained Alpine in that test; no claim of rebuilding plugins or byte-identical Alpine Qt. Source includes TLS plugin sources and Alpine build instructions.

For the local layout set APP to native-package/app (on NAS use actual application installation path). Stop using the lifecycle `cmd/main stop` with appropriate TRIM_APPDEST/TRIM_PKGVAR; confirm status 3 and no owned process. Back up APP/runtime/usr/lib/libQt6{Core,Network,Xml,Sql}.so.6 and APP/runtime/usr/lib/qt6/plugins/tls. Copy ABI-compatible rebuilt libraries to those exact paths, preserving regular-file names/permissions and runtime account read/execute access. Use the bundled musl loader and private library path as in native/control.go; retain QT_PLUGIN_PATH. Restart with `cmd/main start`, verify protected /api/v2/app/version, settings and transfer. Roll back backed-up files on failure. TLS replacements need compatible plugin ABI and OpenSSL. Replacement files are not rejected by any application hash/signature check. Recipient debugging/reverse engineering for modifications is permitted by this application; upstream rights are not restricted.

Clean build prerequisites and actual tested bootstrap/rebuild entry point: build/rebuild_native_1_1_4.sh (run from project root; existing isolated build container required). build/source_build_1_1_3.sh contains full source extraction/libtorrent/qB commands. These are not a clean-base offline toolchain recipe. On fnOS the administrator must be able to replace files; no physical NAS test has been done, no keys are supplied or known to be required. Any GPLv3/LGPLv3 Installation Information obligation for a User Product requires platform review before delivery.
''')
# Explicit lock is tied to verified materials, not rolling version suggestions.
lock={'version':'1.1.4','runtime_inventory':'runtime-inventory.json','recipe_input_checks':'source-verification.json','source_built_qbt_sha256':hashlib.sha256((R/'release/qbittorrent-nox-5.2.4-native-1.1.3').read_bytes()).hexdigest(),'apk_inputs':'build/apk-acquisition.json','bootstrap':'existing qbt-native-113-build; exact base image config sha256 dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0','complete_clean_offline_rebuild':False,'legal_warranty':False}
(S/'BUILD-LOCK.json').write_text(json.dumps(lock,indent=2))
(S/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(S))+'\n' for p in sorted(S.rglob('*')) if p.is_file() and p.name!='SHA256SUMS' and not p.name.endswith('.part')))
# Replace obsolete inventories in mutable staging ONLY; old FPK/source tar immutable.
for name in ['NOTICE.md','BUILD-LOCK.json','SHA256SUMS','SBOM.json','COMPLIANCE-MATRIX.json','QT-REPLACEMENT.md','runtime-inventory.json']:
 shutil.copyfile(S/name,L/name)
(L/'NATIVE-SOURCES.md').write_text(text)
(L/'NATIVE-COMPLIANCE.json').write_text(json.dumps({'version':'1.1.4','matrix':matrix,'legal_warranty':False},indent=2))
(L/'DO-NOT-DISTRIBUTE.txt').write_text('Local candidate only. Distribution notice applicability and fnOS recipient installation-information review remain; optional offline compiler closure is a separate quality gate. See COMPLIANCE-MATRIX.json. No legal warranty.\n')
if (L/'component-notices').exists():shutil.rmtree(L/'component-notices')
shutil.copytree(S/'notices',L/'component-notices')
print(json.dumps({'runtime_files':len(rows),'packages':len(packages),'source_inputs_verified':len(checks),'notice_files':len(notices),'copyright_source_members':len(extra),'matrix_rows':len(matrix)}))
