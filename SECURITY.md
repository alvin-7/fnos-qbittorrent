# Security boundaries and reporting

- fnOS must authenticate requests before the private Unix socket and enforce socket ACLs. X-Trim headers alone on TCP are not authentication. Test-only local identity injectors must never be deployed.
- Keep qB Web API loopback-only on 18080 with Host/CSRF/authentication enabled. A public CSRF marker is not a secret and cannot replace protected Unix ingress.
- MoviePilot's optional 18081 listener requires independent credentials and a verified source/network boundary. Do not forward it to the Internet. Wildcard LAN mode deliberately delegates network filtering to the NAS firewall. BT listening ports are separate.
- Backend/connector password, encrypted secret storage and keys, cookies, signed PT URLs, task names/paths and NAS addresses must not enter source control, console output, screenshots or public issues. Do not request a user's full PT URL to diagnose errors.
- `evidence/`, `.runtime/`, historical staging and `release/` remain private local material. Ignoring does not sanitize them or revoke previously leaked credentials. Never force-add these trees. Rotate any real credential if it was previously exposed.
- Do not run historical reset/build scripts against live application profiles or downloads. Test harnesses create isolated fixtures but use fixed ports; stop on conflicts, never kill unrelated services.
- Business mutations must not be automatically replayed after ambiguous transport/auth failures. Confirm task/backend state by protected read-back.

There is no configured private vulnerability-reporting mailbox or GitHub Security Advisory repository yet. Until the owner supplies one, report only sanitized category/file/line details to the maintainer through an existing private channel; never open a public issue with a working exploit secret, cookie, private host or signed URL. Repository visibility and disclosure channel remain owner decisions.

## Known dependency gate

Current lock pins @playwright/test and playwright 1.55.1 (fixes GHSA-7mvr-c777-76hp), Vite 7.3.7 and esbuild 0.28.2. Official-registry npm audit for all and production dependencies reports 0 vulnerabilities at this validation. Vite 7.3.5 removed the reported high issues but retained an esbuild low advisory; the final compatible lock uses Vite 7.3.7 plus a non-force transitive esbuild update. This is a point-in-time advisory check, not a guarantee against unknown vulnerabilities. Keep dev/test servers loopback-only and do not download untrusted browser binaries. Historical artifacts remain unchanged and are not covered by the new lock. npm emits an install-script approval warning for esbuild and Node emits DEP0205 in browser tests; neither is hidden as a zero-warning result.
