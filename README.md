# AOS chat

One page, served on your own network, that answers questions about this machine using
facts it reads rather than facts it guesses.

Ask *"how much free space is left on D:"* and you get an answer plus a green block listing
exactly what the model was told. Ask for a joke and you get a joke, with no facts block,
because nothing about the machine was needed. The difference between those two replies is
the whole point of the project.

Works in a desktop browser and on a phone on the same network.

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.10 or newer | no third-party packages; standard library only |
| A local OpenAI-compatible endpoint | LM Studio on `:1234` (default) or Ollama on `:11434` |
| A model loaded in that endpoint | the self-test fails clearly if nothing is loaded |
| A browser, on this PC or a phone on the same network | no JavaScript libraries, no build step |
| ~1 MB of disk | the app is one Python file plus a config |

Nothing is sent to any remote service. The model runs on your machine, and so does the page.

## Quick start

```bash
copy config.example.json config.json      # then edit `model` if yours differs
py find_token.py --apply <api key>        # verified against the server's stored hash
py chat_server.py
```

It prints two addresses, one local and one for the LAN:

```
[chat] locally http://127.0.0.1:8081
[chat] on your network  http://<LAN-IP>:8081
```

The page opens automatically. `--no-browser` suppresses that.

You need a local OpenAI-compatible endpoint — LM Studio on `:1234` or Ollama on `:11434`.
Nothing is sent anywhere else.

## How grounding works

Before the model is called, the question is checked against a short list of words that
suggest it is about this computer (`disk`, `memory`, `cpu`, `kernel`, `storage`, …). If it
matches, real values are read from the machine and prepended to the prompt, and the same
list is shown to you in the page.

Verified facts come from two places:

- drive capacity and free space, read directly,
- the kernel's own last serial output, so ANVIL's device lines can be reported by the
  assistant without the assistant inventing them.

If a question is not about the machine, no facts are gathered — and if the model is asked
something the facts do not cover, it is instructed to say so rather than to fill the gap.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | the page |
| `GET` | `/api/status` | host name, platform, collected facts (JSON) |
| `POST` | `/api/chat` | `{"messages": [...]}` → `{"reply": ..., "grounding": ...}` |

`/` is served with `Cache-Control: no-store`, so a reload always gets the current build
rather than yesterday's page.

## Known behaviours

- **Authentication is opt-in, and off by default.** With no `auth_token`, the server binds
  all interfaces and any device on your network can read the page. Set one with
  `py chat_server.py --set-auth`, and clients must then send `Authorization: Bearer <token>`
  or use `?t=<token>` — the query form exists because a phone bookmark cannot send a header.
  Set it before exposing the page anywhere beyond your own network. See
  [SECURITY.md](SECURITY.md).
- **A second launch opens the page** instead of failing, because a double-click while it
  is already running is far more likely than a genuine port conflict.
- **The port is exclusive.** If something else holds it you get a clear message naming the
  command to find it, rather than a silent second server.

## Reaching it from outside your network

The LAN path above needs no configuration. Reaching it from the internet needs two
decisions, and they are separate: **encryption** and **access**.

**1. Encryption — a second listener on 8443.**

```bash
py tools/make_cert.py          # writes cert.pem / key.pem for this machine's names
```

then in `config.json`:

```json
"tls": {"port": 8443, "cert": "cert.pem", "key": "key.pem"}
```

Restart. The plain listener on 8081 is untouched — the LAN keeps working exactly as before,
and the encrypted listener is what you expose. The certificate is self-signed, so the phone
warns once; accept it knowingly.

**2. Access — a token, always.**

```bash
py chat_server.py --set-auth
```

The app prints a warning at startup if TLS is on without a token, because **encryption does
not authenticate anyone**. Both are needed.

**Before you forward a port**, know what you are choosing:

| Approach | Exposure | Notes |
|---|---|---|
| Tailscale or similar mesh | none | phone joins a private network; no router change, no public port |
| Tunnel (Cloudflare, ngrok) | a URL, TLS-terminated | no port forwarding; a third party is in the path |
| **Forward 8443 + TLS + token** | **public** | works, and is the most exposed of the three. Also needs a DDNS name, because a home IP changes |

All three are documented because all three are legitimate. The order is a recommendation, not
a prohibition — but the last one puts an AI endpoint on the public internet, and the token is
the only thing between it and anyone who finds it.

## Troubleshooting

**"Your connection is not private" in Chrome** — the browser is forcing HTTPS against a
plain HTTP server. Type the address with `http://` explicitly, or turn off *Settings →
Privacy and security → Security → Always use secure connections*. The word "private" there
refers to a certificate, not to the private IP range your network uses.

**The phone shows a certificate warning on https://…:8443** — expected: the certificate is
self-signed, so no authority vouches for it. Accept it once on that device. If you would
rather not see the warning at all, that is the argument for a tunnel that terminates TLS with
a real certificate.

**401 from the model endpoint** — the token is wrong. It cannot be recovered from disk,
because LM Studio stores only a hash of it; copy a fresh one from the Developer panel and
run `py find_token.py --apply <key>`, which verifies before storing.

**Nothing in the input box on a phone** — reload. Earlier builds rendered the text box in
the same colour as the background.

## Licence and credit

MIT — see [LICENSE](LICENSE). Who contributed what, and how the work was produced, is in
[CREDITS.md](CREDITS.md). Current state and history: [STATUS.md](STATUS.md),
[CHANGELOG.md](CHANGELOG.md).
