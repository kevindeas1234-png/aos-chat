# Security

No security review has been performed on this project. It is a hobby-scale codebase with
no security response process and no guarantee of a fix.

## Reporting

Open an issue titled `[security] ...` with a description but without a working exploit.
Expect no particular response time.

## Known exposures, by design

| Unauthenticated page on all interfaces | Reachable by every device on the network, by design, so a phone can use it. Set `host` to `127.0.0.1` for local-only use. The API token is stored in `config.json` in plain text: gitignored, not encrypted. |

## General

The documentation states plainly what each tool does at its edges. Where a risk is inherent
to the design rather than an oversight, it is described there rather than left to be
discovered.