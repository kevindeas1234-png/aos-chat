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

## Troubleshooting

**"Your connection is not private" in Chrome** — the browser is forcing HTTPS against a
plain HTTP server. Type the address with `http://` explicitly, or turn off *Settings →
Privacy and security → Security → Always use secure connections*. The word "private" there
refers to a certificate, not to the private IP range your network uses.

**401 from the model endpoint** — the token is wrong. It cannot be recovered from disk,
because LM Studio stores only a hash of it; copy a fresh one from the Developer panel and
run `py find_token.py --apply <key>`, which verifies before storing.

**Nothing in the input box on a phone** — reload. Earlier builds rendered the text box in
the same colour as the background.

## Licence and credit

MIT — see [LICENSE](LICENSE). Who contributed what, and how the work was produced, is in
[CREDITS.md](CREDITS.md). Current state and history: [STATUS.md](STATUS.md),
[CHANGELOG.md](CHANGELOG.md).
