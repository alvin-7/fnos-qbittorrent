"""Generate explicit per-component evidence, never infer compliance from SPDX alone."""
from pathlib import Path
import json,hashlib,tarfile,re,shutil,subprocess
R=Path(__file__).resolve().parents[1];S=R/'release/native-1.1.2-sources';L=R/'native-package/app/licenses';L.mkdir(exist_ok=True)
a=json.loads((S/'alpine-acquisition.json').read_text());old=json.loads((R/'evidence/native-compliance-1.1.1.json').read_text())
notices=[]
archives=list(S.glob('*.tar.gz'))+[S/x['file'] for x in a['files'] if x['verified'] and x['file'].endswith(('.tar.gz','.tar.xz','.tar.bz2','.tgz'))]
for p in archives:
 with tarfile.open(p) as tf:
  for m in tf:
   base=Path(m.name).name.lower()
   if m.isfile() and m.size<2000000 and re.match(r'^(copying|copyright|licen[cs]e|notice|authors)([._-]|$)',base) and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts:
    b=tf.extractfile(m).read();out=S/'notices'/p.name/m.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b);notices.append({'archive':p.name,'member':m.name,'sha256':hashlib.sha256(b).hexdigest()})
(S/'notice-index.json').write_text(json.dumps(notices,indent=2))
rows=[]
for x in old['packages']:
 o=x['source_origin'];inputs=[f for f in a['files'] if f['origin']==o];copyleft=any(v in x['license'] for v in ['GPL','MPL'])
 rows.append({**x,'corresponding_source_retained':all(f['verified'] for f in inputs),'source_files':[f['file'] for f in inputs], 'notice_files_retained':sum(n['archive'] in [Path(f['file']).name for f in inputs] for n in notices),'license_scope':'APK metadata; aggregate expression is NOT exact shipped-library election','obligation_class':'copyleft source/notice/recipient rights; exceptions and file scope must be reviewed' if copyleft else 'permissive notice/attribution; source retained as conservative engineering input','remaining_review':['file-level/embedded-component notice closure','recipe build dependency closure/toolchain inputs not completely retained']})
static=[{'name':'qBittorrent','version':'5.2.4','license':'source GPL-2.0-or-later; binary GPL-3.0-or-later + OpenSSL exception','evidence':'qBittorrent COPYING/AUTHORS retained verbatim','source_retained':True,'build_verified':False},{'name':'libtorrent-rasterbar','commit':'c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9','license':'BSD-3-Clause; LICENSE also lists embedded puff, Boost and ed25519 notices','source_retained':True,'notice_retained':True,'not_GPL':True},{'name':'Boost','version':'1.86.0','license':'BSL-1.0 (not GPL); per-library exceptions/embedded components require review','source_retained':True,'note':'BSL machine-executable object exception means full Boost source is not independently mandated solely by Boost license; retained for rebuild/GPL combined-work completeness.'},{'name':'Go','version':subprocess.check_output(['go','env','GOVERSION']).decode().strip(),'license':'BSD-3-Clause plus embedded third-party notices','source_retained':True,'note':'No generic GPL source duty from Go. Entire source/toolchain retained conservatively, licenses under src/vendor and runtime preserved.'}]
blockers=['Exact original qB builder image/toolchain/cache/options and static embedded closure not attested; original Dockerfile uses alpine:latest, rolling apk and libtorrent RC_1_2.','Locked self-build attempted: current Alpine repository upgrades openssl/pcre2/zlib and exact matching -dev versions unavailable (see locked-build-blocker log). Refuse to silently pair new headers with old shipped libraries. No successful source rebuild claimed.','Alpine archive+patch bytes verified, but complete build-time dependency/toolchain archives and embedded/file-level copyright coverage remain unverified.','Qt runtime election LGPL-3.0-only for eligible Core/Network/Xml and TLS plugins, subject to per-file and bundled third-party audit. Actual replacement with rebuilt ABI-compatible Qt not exercised; no relink materials claimed.','NAS install/ACL/upgrade/uninstall/real gateway identity not tested.']
report={'version':'1.1.2','distributable':False,'status':'DO NOT DISTRIBUTE: functional local test artifact, incomplete compliance gates','runtime_files':old['runtime_files'],'packages':rows,'static_components':static,'source_acquisition':{'origins':len(a['origins']),'files':len(a['files']),'verified_sha512':sum(f['verified'] for f in a['files']),'notice_members':len(notices)},'blockers':blockers,'legal_warranty':False}
for p in [S/'NATIVE-COMPLIANCE.json',L/'NATIVE-COMPLIANCE.json',R/'evidence/native-compliance-1.1.2.json']:p.write_text(json.dumps(report,indent=2))
text='''# Native 1.1.2 notices and recipient rights — NOT DISTRIBUTABLE

This is an incomplete local engineering candidate, not legal assurance. Sources and verbatim notices are in native-1.1.2-sources; never replace original copyright text with SPDX templates.

qBittorrent source GPLv2-or-later, distributed binary GPLv3-or-later, OpenSSL exception (see COPYING). libtorrent BSD-3-Clause, not GPL; embedded puff/ed25519/Boost notices in its LICENSE also retained. Boost BSL-1.0, Go BSD-3-Clause with embedded notices: full standalone source retention is conservative engineering, not a blanket copyleft requirement. GPL corresponding-source scope for the combined qB build is separate.

musl MIT, OpenSSL Apache-2.0, curl curl, ICU ICU, zlib Zlib, libb2 CC0, double-conversion/PCRE2 BSD, most other dependencies MIT; these are NOT generically GPL. ca-certificates MPL-2.0 AND MIT: certificate data/source/build recipe retained; modified MPL files would require source availability. glib, libmount/blkid, libintl, libproxy LGPL; libidn2/libunistring offer LGPL/GPL alternatives; zstd BSD/GPL alternative. GCC APK metadata is aggregate: runtime libraries carry GCC Runtime Library Exception 3.1 where file-level grants apply; do not claim all GCC output GPL or all GCC files excepted. Review retained gcc COPYING.RUNTIME and library notices.

Qt election: use LGPLv3 for eligible shipped Qt Core/Network/Xml + TLS libraries; Alpine's aggregate LGPL2.1 AND LGPL3 AND GPL3 AND Qt exception expression covers more than these binaries. No commercial license asserted. Qt third-party per-file terms still apply. Libraries are dynamically loaded under app/runtime/usr/lib/libQt6*.so.6 and app/runtime/usr/lib/qt6/plugins/tls with private app/runtime/lib/ld-musl-x86_64.so.1 and --library-path. No signature/hash runtime enforcement. Recipient may stop app, back up libraries, replace ABI-compatible same-SONAME libraries/plugins and restart; debugging modifications/reverse engineering for that purpose is not prohibited here. ABI replacement has NOT been proven with a rebuilt different Qt. LGPLv3 suitable shared-library mechanism can avoid application object-code relink delivery; this is conditional, not proof. qB source/build scripts retained; no complete tested relink kit claimed. NAS installation-information restrictions remain unverified. Static resources are retained in the original qB executable; upstream has WEBUI=OFF but that disables the API too, not an acceptable removal. No unsupported resource-stripping performed.

Only custom public/private WebUI trees are configured; API stays enabled, loopback-only and password protected. There is no upstream administration link. Hiding/removing UI never removes Qt/GPL obligations.

Official references reviewed: https://doc.qt.io/qt-6/licensing.html ; https://www.qt.io/licensing/open-source-lgpl-obligations ; https://wiki.alpinelinux.org/wiki/Creating_an_Alpine_package ; qB 5.2.4 CMakeLists/COPYING and official docker-qbittorrent-nox Dockerfile retained. No written source offer issued. This file does not add recipient restrictions to upstream license rights.
'''
(S/'NOTICE.md').write_text(text);(L/'NOTICE.md').write_text(text);(L/'NATIVE-SOURCES.md').write_text(text)
(L/'DO-NOT-DISTRIBUTE.txt').write_text('\n'.join(blockers)+'\n')
if (L/'component-notices').exists():shutil.rmtree(L/'component-notices')
shutil.copytree(S/'notices',L/'component-notices')
(S/'SBOM.json').write_text(json.dumps({'format':'project per-file/component inventory (not certified SPDX)','components':rows+static,'files':old['runtime_files']},indent=2));shutil.copyfile(S/'SBOM.json',L/'SBOM.json')
print(json.dumps(report['source_acquisition']))
