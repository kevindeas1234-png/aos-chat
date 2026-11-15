# AOS chat — status

> Session detail and rewind points: `D:\AOS\WORKLOG.md`

_Last updated: 2026-11-15_

## It works

The app is live and answering with a real model, grounded in real machine facts.

| Item | Value |
|---|---|
| Page | http://127.0.0.1:8081 |
| On the LAN / phone | http://<LAN-IP>:8081 |
| Model | `google/gemma-4-e4b` @ http://127.0.0.1:1234/v1 |
| Port | 8081 (from `config.json`) |

Verified run (`selftest.txt`): `/` → 200, `/api/status` → 200, `model probe -> OK: 'ok'`.

## What was broken, and why

### 1. The token (blocker)

LM Studio stores tokens in `~/.lmstudio/.internal/permissions-store.json`.
Only the **client id** is in clear text; the passkey is kept as a **base64 SHA-512
hash**. A token therefore cannot be read back from disk — only verified.

The old `find_token.py` scanned JSON files for anything that *looked* token-ish and
installed the **longest** hit. It picked a hash, wrote it into `config.json`, and the
server answered `401 Invalid LM Studio API token`.

**Fix:** the correct token was confirmed *cryptographically* — its SHA-512 matches the
stored hash — and written into `config.json`. `find_token.py` was rewritten to:

* enforce the real shape `sk-lm-<8>:<20>` before anything is written,
* verify a pasted key against the stored hash (`--check`),
* install only after that check passes (`--apply`),
* never print the secret.

```
py find_token.py                 # list registered tokens (ids only)
py find_token.py --check <key>   # verify
py find_token.py --apply <key>   # verify, then store
```

### 2. Model name

`config.json` pointed at `google/gemma-4-26b-a4b`, which is no longer on this machine.
The only loaded model is `google/gemma-4-e4b`, so the config now names that.

### 3. Two servers on one port (root cause of "stale process")

`http.server` sets `allow_reuse_address = 1`. On Windows that is `SO_REUSEADDR`, which
lets a **second** process bind the same port and silently share traffic. That is why a
restart could appear to work while an old build kept answering.

**Fix:** `SingleInstanceServer` sets `allow_reuse_address = False`, so a second copy
fails loudly instead of stealing the port. To keep it friendly, a second launch that
finds a *working* app already running just opens the page (exit 0).

### 4. Double-click UX

`AOS Chat.bat` now opens the page in a browser on start. `--no-browser` suppresses it.

### 5. A bad key can no longer be stored

`chat_server.py --set-key` (used by `set_token.bat`) verifies the key against LM Studio's
stored hash **before** writing it. A typo is refused instead of becoming a 401 later.

## Running it

Double-click **AOS Chat.bat** on the desktop. It prints the LAN address for your phone.
Double-clicking again while it runs simply brings the page up.

If it ever says *"cannot bind"* and the page does not load, something else owns 8081:

```
netstat -ano | findstr :8081
taskkill /PID <pid> /F
```

## Still open

* **Rotate the API token** when convenient — an earlier key was pasted into a chat
  transcript. After rotating, run `py find_token.py --apply <new key>`; the tool will
  refuse a key that does not match the stored hash.
* The broker logs every grant, refusal, revocation and *use it is asked about*, and
  `py D:\AOS\broker.py --audit` now reconciles policy against the log. What it cannot do
  is force a tool to ask: that remains an agreement, not a sandbox.
* ANVIL kernel: M0–M8 green; virtio read/write and writeback round-trip verified in the
  sandbox (see `D:\OS\HANDOVER.md`).
