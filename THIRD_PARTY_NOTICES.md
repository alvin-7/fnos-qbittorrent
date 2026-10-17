# Third-party notices and provenance

Original application code, UI, artwork, configuration, tests and adaptation scripts are Copyright (C) 2026 alvin-7 and licensed under GPL-3.0-or-later (see LICENSE). This applies only to original work and does not relicense, replace, or grant additional rights in third-party code or upstream materials. Historical artifacts are preserved unchanged. This status does not change any third-party license.

## Native runtime

The application uses qBittorrent-nox 5.2.4 and its Qt/libtorrent/musl dependency
closure. qB upstream COPYING distinguishes GPL-2.0-or-later source from
GPL-3.0-or-later binary distribution terms; inspect the exact corresponding source
and component notices rather than applying a blanket license to all dependencies.
Libtorrent uses BSD terms, Boost uses BSL-1.0 and Go uses BSD-style terms.
Qt components have component-specific LGPL/GPL/commercial terms; a link to Qt is
not a replacement for retaining exact notices and meeting applicable obligations.

Retained provenance inputs (not newly fetched or independently re-certified here):
- https://github.com/qbittorrent/docker-qbittorrent-nox
- Image tag: `ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1`
- OCI index: `sha256:92bfd78d731e254ba64f62b77b0696add6447a33642ee5feda106a26b285aa7f`
- Docker recipe revision: `99a2044d7f4f7d36da559cbc6439934a80502967`
- qB source: https://github.com/qbittorrent/qBittorrent/tree/release-5.2.4

The latest native FPK **does contain native runtime binaries**. Statements in old
Docker documentation that qB is downloaded only at installation do not describe
the 1.4.0 native artifact. Exact source/header/notice/recipe material remains in
local source bundles and package license inventories, outside the Git upload set.
See docs/SOURCE_DELIVERY.md; this concise document is not a replacement for those
full notices or complete corresponding source.

## Frontend and tooling

`package-lock.json` pins React/React DOM 19.1.1, scheduler and build/test tooling.
React, React DOM and scheduler are MIT-licensed; retain exact installed package
license/copyright texts when distributing the compiled UI. TypeScript (Apache-2.0),
Vite (MIT), and Playwright (Apache-2.0) are development dependencies; review their
transitive notices if redistributed. No external font/icon CDN is used.

The source repository is an independent fnOS adaptation, not an upstream endorsed
release. Original artwork is GPL-3.0-or-later, Copyright (C) 2026 alvin-7. Do not
replace authentic upstream notices with synthetic license text or assume that
excluding source archives from Git removes binary redistribution obligations.
