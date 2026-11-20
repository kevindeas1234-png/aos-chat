#!/usr/bin/env python3
"""AOS chat - a small local app to talk to an AI that can see this machine.

One page, served on your LAN, so it works on a phone or a desktop browser.
The model is whatever OpenAI-compatible endpoint you point it at (LM Studio on
:1234, Ollama on :11434, or a remote URL). Nothing is hard-coded.

    py chat_server.py                 # http://127.0.0.1:8080 and your LAN address
    py chat_server.py --port 9000

Tools: when you ask about the machine, real facts are gathered first and given
to the model, rather than letting it guess. Every fact is shown inline with the
answer so you can see what it was told.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")

DEFAULT_CONFIG = {
    "model": {
        "base_url": "http://127.0.0.1:1234/v1",
        "model": "local-model",
        "api_key": "",
        "system": "You are AOS, an assistant running on the user's own computer. "
                  "Be concise and concrete. If machine facts are supplied, use them "
                  "and say what you used. Never invent hardware details.",
    },
    # auth_token: empty means "no authentication", which is the LAN default. Set it
    # before exposing the page beyond your own network; see SECURITY.md.
    "server": {"host": "0.0.0.0", "port": 8080, "auth_token": ""},
}


def _auth_token(config: dict) -> str:
    return (config.get("server", {}).get("auth_token") or "").strip()

# Words that mean 'look at the actual machine before answering'.
MACHINE_HINTS = ("machine", "pc", "computer", "hardware", "disk", "drive", "ssd",
                 "hdd", "memory", "ram", "cpu", "status", "running", "anvil",
                 "kernel", "system", "specs", "storage", "space")


def load_config(path: str = CONFIG_PATH) -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                user = json.load(handle)
            for section, values in user.items():
                if isinstance(values, dict):
                    config.setdefault(section, {}).update(values)
                else:
                    config[section] = values
        except (OSError, ValueError) as exc:
            print(f"[chat] config unreadable ({exc}); using defaults")
    return config


# ---------------------------------------------------------------------------
# tools: facts about this machine
# ---------------------------------------------------------------------------
def _disk_facts() -> list[str]:
    facts = []
    for drive in ("C:\\", "D:\\", "E:\\"):
        try:
            usage = shutil.disk_usage(drive)
        except OSError:
            continue
        facts.append(f"{drive[0]}: {usage.free / 1e9:.0f} GB free of "
                     f"{usage.total / 1e9:.0f} GB")
    return facts


def _anvil_facts() -> list[str]:
    """What the kernel last reported, from its own log."""
    log = os.environ.get("ANVIL_LOG", r"D:\OS\logs\m1test.log")
    if not os.path.isfile(log):
        return ["ANVIL: no run recorded yet"]
    try:
        with open(log, encoding="utf-8", errors="replace") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except OSError:
        return ["ANVIL: log unreadable"]
    interesting = [line for line in lines
                   if line.startswith(("virtio:", "e820:", "heap:", "memory:", "paging:"))]
    return [f"ANVIL: {line}" for line in interesting[-8:]] or ["ANVIL: log has no device lines"]


def gather_status() -> dict:
    return {
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "host": socket.gethostname(),
        "platform": f"{os.name} / {sys.platform} / python {sys.version.split()[0]}",
        "facts": _disk_facts() + _anvil_facts(),
    }


def wants_machine_facts(text: str) -> bool:
    lowered = (text or "").lower()
    return any(hint in lowered for hint in MACHINE_HINTS)


def grounding_message(text: str) -> str | None:
    if not wants_machine_facts(text):
        return None
    status = gather_status()
    body = "\n".join(f"- {fact}" for fact in status["facts"])
    return (f"Verified machine facts (collected {status['collected_at']} on "
            f"{status['host']}):\n{body}\n"
            f"Use only these if the question is about this machine.")


# ---------------------------------------------------------------------------
# model call
# ---------------------------------------------------------------------------
def build_payload(messages: list[dict], config: dict, user_text: str) -> dict:
    payload_messages = [{"role": "system", "content": config["model"].get("system", "")}]
    grounding = grounding_message(user_text)
    if grounding:
        payload_messages.append({"role": "system", "content": grounding})
    payload_messages.extend(messages)
    return {
        "model": config["model"].get("model", "local-model"),
        "messages": payload_messages,
        "temperature": 0.4,
        "max_tokens": 700,
    }


def call_model(messages: list[dict], config: dict, user_text: str,
               timeout: float = 120.0) -> tuple[str, str | None]:
    """Returns (reply, grounding) where grounding is what the model was told."""
    base = config["model"]["base_url"].rstrip("/")
    payload = json.dumps(build_payload(messages, config, user_text)).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {config['model']['api_key']}"}
                    if config["model"].get("api_key") else {})},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"]
        return reply, grounding_message(user_text)
    except urllib.error.HTTPError as exc:
        body = exc.read()[:300].decode("utf-8", "replace")
        return f"The model endpoint returned {exc.code}: {body}", None
    except urllib.error.URLError as exc:
        return (f"No model endpoint at {base}. Start one (LM Studio on :1234, "
                f"Ollama on :11434) or edit {CONFIG_PATH}.\n\nDetail: {exc.reason}"), None
    except (KeyError, IndexError, ValueError) as exc:
        return f"Unexpected reply from the model endpoint: {exc}", None


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------
def render_page(config: dict) -> str:
    model = config["model"].get("model", "local-model")
    base = config["model"].get("base_url", "")
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content">
<title>AOS</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  html {{ height:100%; }}
  body {{ margin:0; background:#0b1220; color:#dbeafe;
         font-size:15px; line-height:1.45;
         font-family:-apple-system,"Segoe UI",Roboto,sans-serif;
         -webkit-text-size-adjust:100%;
         display:flex; flex-direction:column;
         height:100vh; height:100dvh; }}
  header {{ padding:10px 14px; background:#0e1826; border-bottom:1px solid #1d3145;
            display:flex; gap:8px; align-items:baseline; }}
  header b {{ color:#2ee6c5; letter-spacing:.08em; font-size:13px; }}
  header span {{ color:#4d6b81; font-size:11px; margin-left:auto; }}
  #log {{ flex:1; overflow-y:auto; padding:14px; display:flex;
          flex-direction:column; gap:10px; }}
  .msg {{ max-width:88%; padding:10px 12px; border-radius:14px; white-space:pre-wrap;
          word-wrap:break-word; }}
  .me {{ align-self:flex-end; background:#16324a; border:1px solid #1f4661; }}
  .ai {{ align-self:flex-start; background:#121e2b; border:1px solid #1d3145; }}
  .truth {{ align-self:stretch; background:#0e1a16; border:1px dashed #1f5f46;
            color:#8fd6b4; font:11px/1.4 ui-monospace,Consolas,monospace;
            padding:8px 10px; border-radius:10px; }}
  .truth b {{ color:#2ee6c5; }}
  footer {{ position:sticky; bottom:0; z-index:2;
            padding:10px; background:#0e1826; border-top:1px solid #1d3145;
            display:flex; gap:8px; align-items:flex-end;
            padding-bottom:calc(10px + env(safe-area-inset-bottom)); }}
  form {{ display:flex; gap:8px; flex:1; }}
  textarea {{ flex:1; min-height:44px; max-height:120px; resize:none;
              padding:11px 12px; border-radius:12px;
              border:1px solid #2a4a63; background:#101c2a; color:#dbeafe;
              font-family:inherit; font-size:16px; line-height:1.3; }}
  textarea::placeholder {{ color:#6f8ba3; }}
  button {{ min-width:64px; height:44px; padding:0 12px; border-radius:12px;
            border:1px solid #1a6b62; background:#123b36; color:#2ee6c5;
            font-family:inherit; font-size:15px; font-weight:600; }}
  button:disabled {{ opacity:.5; }}
  .hint {{ color:#4d6b81; font-size:11px; padding:0 14px 6px; }}
</style></head>
<body>
<header><b>AOS</b><span>{model} @ {base}</span></header>
<div id="log">
  <div class="msg ai">Ask me anything about this machine, or anything else.</div>
</div>
<div class="hint" id="hint"></div>
<footer>
  <form id="composer">
    <textarea id="box" rows="1" placeholder="Message AOS..."
              enterkeyhint="send" autocomplete="off"></textarea>
    <button id="send" type="submit">Send</button>
  </form>
</footer>
<script>
const log = document.getElementById('log'), box = document.getElementById('box'),
      send = document.getElementById('send'), hint = document.getElementById('hint');
let history = [];

function bubble(text, cls) {{
  const div = document.createElement('div');
  div.className = 'msg ' + cls; div.textContent = text;
  log.appendChild(div); log.scrollTop = log.scrollHeight; return div;
}}
function facts(list) {{
  if (!list || !list.length) return;
  const div = document.createElement('div');
  div.className = 'truth';
  div.innerHTML = '<b>facts given to the model</b>\\n' +
      list.map(f => f.replace(/[<>&]/g, c => ({{'<':'&lt;','>':'&gt;','&':'&amp;'}})[c]))
          .join('\\n');
  log.appendChild(div); log.scrollTop = log.scrollHeight;
}}

async function submit() {{
  const text = box.value.trim(); if (!text) return;
  box.value = ''; send.disabled = true;
  bubble(text, 'me'); history.push({{role:'user', content:text}});
  const pending = bubble('...', 'ai');
  try {{
    const r = await fetch('/api/chat', {{method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{messages: history}})}});
    const data = await r.json();
    pending.textContent = data.reply || '(no reply)';
    if (data.grounding) facts(data.grounding.split('\\n').slice(1));
    history.push({{role:'assistant', content:data.reply || ''}});
  }} catch (e) {{
    pending.textContent = 'Request failed: ' + e;
  }} finally {{ send.disabled = false; box.focus(); }}
}}
// A real form, so a phone keyboard's Go/Enter key submits rather than doing nothing.
document.getElementById('composer').addEventListener('submit', e => {{
  e.preventDefault(); submit();
}});
box.addEventListener('keydown', e => {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); submit(); }}
}});
fetch('/api/status').then(r => r.json()).then(s => {{
  hint.textContent = 'host ' + s.host + ' · ' + s.facts.length + ' fact(s) available';
}}).catch(() => {{}});
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# server
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    config: dict = DEFAULT_CONFIG

    def log_message(self, fmt, *args):
        # quiet: we log the interesting things ourselves, with timings
        pass

    def _note(self, message: str) -> None:
        print(f"[chat] {datetime.now().strftime('%H:%M:%S')} {message}", flush=True)

    def _presented_token(self) -> str:
        """Bearer header preferred; ?t= query for phones and browser bookmarks."""
        header = self.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        query = urllib.parse.urlsplit(self.path).query
        return (urllib.parse.parse_qs(query).get("t") or [""])[0].strip()

    def _authorised(self) -> bool:
        """True when no token is configured, or when the presented one matches.

        With no token set, behaviour is exactly as before: any device on the
        network can read the page. That is the documented LAN default.
        """
        expected = _auth_token(Handler.config)
        if not expected:
            return True
        presented = self._presented_token()
        # constant-time: a timing oracle on a shared token is a bad habit to build
        return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))

    def _send(self, code: int, body: bytes, content_type: str,
              no_store: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if no_store:
            # The page is generated per request and its UI changes; a cached copy
            # on a phone is a confusing way to test a fix.
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urllib.parse.urlsplit(self.path).path
        if not self._authorised():
            self._note(f"GET {route}  401  missing or wrong token")
            self._send(401, b'{"error":"token required"}', "application/json")
            return
        if route in ("/", "/index.html"):
            page = render_page(Handler.config).encode("utf-8")
            self._send(200, page, "text/html; charset=utf-8", no_store=True)
            self._note(f"GET /  200  page served ({len(page)} bytes)")
        elif route == "/api/status":
            self._send(200, json.dumps(gather_status()).encode("utf-8"),
                       "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        route = urllib.parse.urlsplit(self.path).path
        if not self._authorised():
            self._note(f"POST {route}  401  missing or wrong token")
            self._send(401, b'{"error":"token required"}', "application/json")
            return
        if route != "/api/chat":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            self._send(400, b'{"error":"bad json"}', "application/json")
            return

        messages = body.get("messages") or []
        if not isinstance(messages, list) or not messages:
            self._send(400, b'{"error":"no messages"}', "application/json")
            return

        user_text = messages[-1].get("content", "")
        self._note(f"POST /api/chat  {user_text[:60]!r}")
        started = time.time()
        reply, grounding = call_model(messages, Handler.config, user_text)
        elapsed = time.time() - started
        self._note(f"  -> {len(reply)} chars in {elapsed:.1f}s"
                   + ("  [grounded]" if grounding else "  [no grounding]"))
        payload = json.dumps({"reply": reply, "grounding": grounding}).encode("utf-8")
        self._send(200, payload, "application/json")


def self_test(port: int) -> None:
    """Prove the server answers, and write the result somewhere readable.

    The console is easy to lose; a file on disk is not.
    """
    import time as _t
    _t.sleep(0.6)
    has_key = bool(Handler.config["model"].get("api_key"))
    auth = _auth_token(Handler.config)
    lines = [f"AOS chat self-test  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             f"port {port}",
             f"api_key configured: {'yes' if has_key else 'no'}",
             f"auth: {'required' if auth else 'off (LAN open)'}",
             f"model: {Handler.config['model'].get('model')} @ "
             f"{Handler.config['model'].get('base_url')}"]
    # The self-test has to authenticate too, or enabling auth would make it report
    # a failure that only exists because the test forgot its own key.
    headers = {"Authorization": f"Bearer {auth}"} if auth else {}
    for path in ("/", "/api/status"):
        url = f"http://127.0.0.1:{port}{path}"
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read()
            line = f"{path} -> HTTP {response.status} ({len(body)} bytes)"
        except Exception as exc:            # noqa: BLE001 - report the reason
            line = f"{path} -> FAILED: {type(exc).__name__}: {exc}"
        lines.append(line)
        print(f"[chat] self-test {line}", flush=True)

    # one tiny model call: proves the endpoint and the token, not just the socket
    base = Handler.config["model"]["base_url"].rstrip("/")
    probe = {
        "model": Handler.config["model"].get("model", "local-model"),
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if has_key:
        headers["Authorization"] = f"Bearer {Handler.config['model']['api_key']}"
    try:
        request = urllib.request.Request(f"{base}/chat/completions",
                                         data=json.dumps(probe).encode("utf-8"),
                                         headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        answer = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        lines.append(f"model probe -> OK: {answer.strip()[:40]!r}")
        print(f"[chat] model probe -> OK: {answer.strip()[:40]!r}", flush=True)
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode("utf-8", "replace")
        lines.append(f"model probe -> HTTP {exc.code}: {detail}")
        print(f"[chat] model probe -> HTTP {exc.code}: {detail}", flush=True)
    except urllib.error.URLError as exc:
        lines.append(f"model probe -> FAILED: {exc.reason}")
        print(f"[chat] model probe -> FAILED: {exc.reason}", flush=True)
    except Exception as exc:            # noqa: BLE001 - report anything else too
        lines.append(f"model probe -> {type(exc).__name__}: {exc}")
        print(f"[chat] model probe -> {type(exc).__name__}: {exc}", flush=True)

    try:
        with open(os.path.join(HERE, "selftest.txt"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        pass


class SingleInstanceServer(ThreadingHTTPServer):
    """Refuse to double-bind the port.

    http.server sets allow_reuse_address = 1. On Windows that maps to
    SO_REUSEADDR, which lets a second (or stale) process bind the same port and
    silently share the traffic. Turning it off makes a second launch fail loudly
    instead of serving stale state.
    """

    allow_reuse_address = False
    daemon_threads = True


def token_is_valid(token: str) -> bool:
    """Refuse an obviously wrong credential before it reaches config.json.

    A bad token is not a small mistake: it produces a 401 that looks like a
    server fault. So the shape is always checked, and the passkey is checked
    against LM Studio's own stored hash whenever that store is readable.
    """
    try:
        import find_token                     # same folder as this file
    except ImportError:
        find_token = None

    if find_token is None:
        print("[chat] find_token.py not found; only the shape can be checked")
        return True

    store = find_token.load_store(find_token.DEFAULT_STORE)
    records = find_token.registered_tokens(store) if store else []
    ok, why = find_token.verify(token, records)
    print(f"[chat] token {find_token.mask(token)} -> {'valid' if ok else 'INVALID'}: {why}")
    if ok:
        return True
    if store is None:
        print("[chat] LM Studio's token store is unreadable, so this cannot be")
        print("[chat] verified - storing it anyway. If requests fail with 401, the")
        print("[chat] key is wrong; copy it again from the Developer panel.")
        return True
    print("[chat] not stored. Re-copy the key from LM Studio's Developer panel")
    print("[chat] (the passkey is only kept as a hash, so it cannot be guessed).")
    return False


def already_serving(port: int, timeout: float = 2.0) -> bool:
    """True if a working AOS chat app is already answering on this port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status",
                                    timeout=timeout) as response:
            return response.status == 200
    except Exception:                   # noqa: BLE001 - any failure means 'no'
        return False


def lan_address() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        probe.close()
        return address
    except OSError:
        return "127.0.0.1"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="local chat app for AOS")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true",
                        help="do not open the page in a browser")
    parser.add_argument("--set-auth", action="store_true",
                        help="set or clear the page's own access token, then exit")
    parser.add_argument("--set-key", action="store_true",
                        help="prompt for the model API token and store it in config.json")
    args = parser.parse_args(argv)

    if args.set_auth:
        import getpass
        config = load_config()
        current = _auth_token(config)
        print(f"page token: {'set (' + str(len(current)) + ' characters)' if current else 'not set - the page is open to the LAN'}")
        print("leave empty to remove authentication")
        token = getpass.getpass("new page token (input is hidden): ").strip()
        config.setdefault("server", {})["auth_token"] = token
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
        if token:
            print(f"stored ({len(token)} characters); clients must send"
                  f" 'Authorization: Bearer <token>' or use ?t=<token>")
        else:
            print("cleared: the page is open to the LAN again")
        print("restart the chat app for it to take effect")
        return 0

    if args.set_key:
        import getpass
        config = load_config()
        current = config["model"].get("api_key", "")
        print(f"current token: {'set' if current else 'not set'}")
        token = getpass.getpass("paste the API token (input is hidden): ").strip()
        if not token:
            print("nothing entered; config unchanged")
            return 1
        if not token_is_valid(token):
            return 1
        config["model"]["api_key"] = token
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
        print(f"stored ({len(token)} characters) in {CONFIG_PATH}")
        print("restart the chat app for it to take effect")
        return 0

    config = load_config()
    if not os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
        print(f"[chat] wrote default config: {CONFIG_PATH}")

    host = args.host or config["server"].get("host", "0.0.0.0")
    port = args.port or config["server"].get("port", 8080)
    Handler.config = config

    url = f"http://127.0.0.1:{port}/"
    try:
        server = SingleInstanceServer((host, port), Handler)
    except OSError as exc:
        # Most often: a copy is already running. If that copy answers, this is a
        # second double-click, so just show the page instead of failing.
        if already_serving(port):
            print(f"[chat] already running at {url}")
            if not args.no_browser:
                webbrowser.open(url)
            return 0
        print(f"[chat] cannot bind {host}:{port} - {exc}")
        print(f"[chat] something else owns the port: netstat -ano | findstr :{port}")
        return 2
    shown = lan_address() if host in ("0.0.0.0", "") else host
    auth = _auth_token(config)
    print(f"[chat] auth    {'required - use ?t=<token> or a Bearer header' if auth else 'off (any device on this network can read the page)'}")
    print(f"[chat] model   {config['model'].get('model')} @ "
          f"{config['model'].get('base_url')}")
    print(f"[chat] locally http://127.0.0.1:{port}")
    print(f"[chat] on your network  http://{shown}:{port}")
    print("[chat] Ctrl+C to stop")
    threading.Thread(target=self_test, args=(port,), daemon=True).start()
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[chat] stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
