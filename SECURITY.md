# Security

No security review has been performed on this project. It is a hobby-scale codebase with
no security response process and no guarantee of a fix.

## Reporting

Open an issue titled `[security] ...` with a description but without a working exploit.
Expect no particular response time.

## Known exposures, by design

| **Unauthenticated page by default** | With no `auth_token` set, the server binds all interfaces and every device on the network can read the page. A phone needs this. |
| **Auth is opt-in** | `py chat_server.py --set-auth` stores a token; clients then send `Authorization: Bearer <token>` or `?t=<token>`. Compared in constant time. Set it before exposing the page beyond your own network, and note that `?t=` puts the token in a URL, which lands in browser history. |
| **Model API token in plain text** | Stored in `config.json`: gitignored, but not encrypted. |
| **No TLS** | Traffic is plain HTTP, so a token on an untrusted network is readable. Use a VPN or a tunnel that terminates TLS if that matters. |

## General

The documentation states plainly what each tool does at its edges. Where a risk is inherent
to the design rather than an oversight, it is described there rather than left to be
discovered.