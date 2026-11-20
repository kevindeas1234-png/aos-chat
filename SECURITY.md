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
| **Plain HTTP by default** | The LAN listener speaks HTTP, so a token on an untrusted network is readable in transit. |
| **TLS is opt-in** | `tools/make_cert.py` plus a `tls` block in `config.json` starts a second HTTPS listener (default port 8443). Self-signed, so clients warn once. It encrypts; it does not authenticate - pair it with a token. |
| **Private key on disk** | `key.pem` is generated beside the app, gitignored and never banked. Treat it as a secret; the certificate is machine-specific and worthless elsewhere. |

## General

The documentation states plainly what each tool does at its edges. Where a risk is inherent
to the design rather than an oversight, it is described there rather than left to be
discovered.