#!/usr/bin/env python3
"""Check or install an LM Studio API token - without guessing.

LM Studio keeps its tokens in ``~/.lmstudio/.internal/permissions-store.json``.
Only the *client identifier* is stored in clear text; the passkey is kept as a
base64 SHA-512 hash. So a token cannot be recovered from disk - it can only be
*verified*. That is what this tool does.

    py find_token.py                      # list the registered tokens
    py find_token.py --check <token>      # verify a pasted token
    py find_token.py --apply <token>      # verify, then store it in config.json

Earlier versions of this script scanned JSON files for anything that looked
token-ish and installed the longest hit. That silently wrote a hash into
config.json and produced a broken credential. Format and hash are now both
checked before anything is written.

The token is never printed, only its client identifier and a masked form.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
DEFAULT_STORE = os.path.join(os.path.expanduser("~"), ".lmstudio", ".internal",
                             "permissions-store.json")

# The shape LM Studio itself enforces: sk-lm-<8 alnum>:<20 alnum>
# The placeholder text deliberately avoids looking like a real token, so a secret
# scanner does not have to be taught about this file.
TOKEN_RE = re.compile(r"^sk-lm-(?P<client>[A-Za-z0-9]{8}):(?P<passkey>[A-Za-z0-9]{20})$")


def mask(token: str) -> str:
    """A safe rendering: enough to recognise, not enough to reuse."""
    match = TOKEN_RE.match(token)
    if not match:
        return "***malformed***"
    return f"sk-lm-{match.group('client')}:{'*' * 20}"


def load_store(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def registered_tokens(store: dict) -> list[dict]:
    body = store.get("json", store) if isinstance(store, dict) else {}
    tokens = body.get("tokens")
    return tokens if isinstance(tokens, list) else []


def expected_hash(record: dict) -> str:
    return (record.get("clientPasskeySHA512Base64") or "").strip()


def verify(token: str, records: list[dict]) -> tuple[bool, str]:
    """True if the token matches a registered client id *and* its passkey hash."""
    match = TOKEN_RE.match(token or "")
    if not match:
        return False, ("wrong shape - expected the form sk-lm-<8 alnum>:<20 alnum>"
                       " (e.g. sk-lm-AbCd1234: plus 20 more characters)")
    client = match.group("client")
    record = next((r for r in records if r.get("clientIdentifier") == client), None)
    if record is None:
        known = ", ".join(r.get("clientIdentifier", "?") for r in records) or "none"
        return False, f"no registered token with client id {client} (known: {known})"
    digest = base64.b64encode(
        hashlib.sha512(match.group("passkey").encode("utf-8")).digest()
    ).decode("ascii")
    if not hmac.compare_digest(digest, expected_hash(record)):
        return False, f"passkey does not match the stored hash for {client}"
    return True, f"valid for client id {client}"


def install(token: str) -> int:
    config = {}
    if os.path.isfile(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8") as handle:
                config = json.load(handle)
        except (OSError, ValueError):
            print("[token] config.json unreadable; writing a fresh one")
            config = {}
    config.setdefault("model", {})["api_key"] = token
    try:
        with open(CONFIG, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
    except OSError as exc:
        print(f"[token] could not write {CONFIG}: {exc}")
        return 2
    print(f"[token] stored {mask(token)} in {CONFIG}")
    print("[token] restart the chat app for it to take effect")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check or install an LM Studio token")
    parser.add_argument("--store", default=DEFAULT_STORE,
                        help="path to permissions-store.json")
    parser.add_argument("--check", metavar="TOKEN", default=None,
                        help="verify a token against the stored hash")
    parser.add_argument("--apply", metavar="TOKEN", default=None,
                        help="verify a token, then write it into config.json")
    args = parser.parse_args(argv)

    store = load_store(args.store)
    if store is None:
        print(f"[token] cannot read {args.store}")
        print("[token] LM Studio writes it on first launch. If it is missing,")
        print("[token] copy the key from LM Studio's Developer panel with set_token.bat")
        return 2

    records = registered_tokens(store)
    body = store.get("json", store) if isinstance(store, dict) else {}
    print(f"[token] store   {args.store}")
    print(f"[token] mode    {body.get('tokenMode', '?')}")
    print(f"[token] tokens  {len(records)}")
    for record in records:
        created = record.get("createdAt")
        label = record.get("label") or "(no label)"
        print(f"  client {record.get('clientIdentifier', '?'):8}  {label}"
              f"  hash {'present' if expected_hash(record) else 'MISSING'}"
              + (f"  created {created}" if created else ""))
    if not records:
        print("[token] no tokens registered - create one in LM Studio's Developer panel")

    token = args.check or args.apply
    if not token:
        print("\n[token] the passkey is stored only as a hash, so it cannot be read back.")
        print("[token] paste your key to verify it:  py find_token.py --check <token>")
        return 0

    ok, why = verify(token.strip(), records)
    print(f"\n[token] {mask(token.strip())}  ->  {'VALID' if ok else 'INVALID'}: {why}")
    if not ok:
        return 1
    if args.apply:
        return install(token.strip())
    print("[token] add --apply to write it into config.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
