#!/usr/bin/env python3
"""Create a known API token for the local LM Studio server.

Why this exists
---------------
LM Studio keeps only a SHA-512 hash of a token's passkey. The key is shown once,
at creation. If that moment is missed - or the panel offers nowhere to copy it -
there is nothing left to recover, and no UI tour will help.

So this writes a token entry directly into LM Studio's own store, using the same
shape and the same hash it expects. The passkey is generated here, so we know it,
and it never has to be typed, printed, or copied from a dialog.

    py tools\\make_lm_token.py              # add a token, store it in config.json
    py tools\\make_lm_token.py --dry-run    # show what would happen
    py tools\\make_lm_token.py --restore    # put the store back from the newest backup

Safety
------
* The store is copied to `permissions-store.json.bak-<timestamp>` before any write.
* Existing tokens are left untouched; this appends one labelled `aos-chat`.
* `--restore` puts back the newest backup, so the change is reversible.
* Restart LM Studio afterwards: it reads this file when its server starts.
"""

from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import io
import json
import os
import secrets
import shutil
import string
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
CONFIG = os.path.join(APP, "config.json")
sys.path.insert(0, APP)

import find_token                                   # noqa: E402

ALPHABET = string.ascii_letters + string.digits


def store_path() -> str:
    return find_token.DEFAULT_STORE


def backup(store: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = f"{store}.bak-{stamp}"
    shutil.copy2(store, target)
    return target


def newest_backup(store: str) -> str | None:
    candidates = sorted(glob.glob(store + ".bak-*"))
    return candidates[-1] if candidates else None


def make_pair() -> tuple[str, str]:
    client = "".join(secrets.choice(ALPHABET) for _ in range(8))
    passkey = "".join(secrets.choice(ALPHABET) for _ in range(20))
    return client, passkey


def hash_passkey(passkey: str) -> str:
    return base64.b64encode(
        hashlib.sha512(passkey.encode("utf-8")).digest()).decode("ascii")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="create a known LM Studio API token")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--label", default="aos-chat")
    args = parser.parse_args(argv)

    store = store_path()
    if not os.path.isfile(store):
        print(f"[token] no store at {store} - has LM Studio been started at least once?")
        return 2

    if args.restore:
        latest = newest_backup(store)
        if not latest:
            print("[token] no backup to restore from")
            return 2
        shutil.copy2(latest, store)
        print(f"[token] restored {store} from {os.path.basename(latest)}")
        print("[token] restart LM Studio")
        return 0

    data = json.load(io.open(store, encoding="utf-8"))
    body = data.setdefault("json", {})
    tokens = body.setdefault("tokens", [])
    template = tokens[0] if tokens else {}

    client, passkey = make_pair()
    entry = {
        "clientIdentifier": client,
        "clientPasskeySHA512Base64": hash_passkey(passkey),
        "label": args.label,
        "createdAt": int(time.time() * 1000),
        "lastUsedAt": None,
        "permissions": template.get("permissions") or {
            "dynamicRemoteMcpServer": "allowAll", "pluginUse": "allowAll"},
    }

    print(f"[token] store    {store}")
    print(f"[token] existing {[t.get('clientIdentifier') for t in tokens]}")
    print(f"[token] adding   {client} (label {args.label!r})")

    if args.dry_run:
        print("[token] dry run: nothing written")
        return 0

    saved = backup(store)
    print(f"[token] backed up to {os.path.basename(saved)}")

    tokens.append(entry)
    body["tokenMode"] = body.get("tokenMode") or "required"
    json.dump(data, io.open(store, "w", encoding="utf-8", newline="\n"), indent=2)
    print("[token] store written")

    token = f"sk-lm-{client}:{passkey}"
    config = json.load(io.open(CONFIG, encoding="utf-8"))
    config.setdefault("model", {})["api_key"] = token
    json.dump(config, io.open(CONFIG, "w", encoding="utf-8", newline="\n"), indent=2)
    print(f"[token] config.json updated with {find_token.mask(token)}")

    # verify against the store we just wrote, the same check everything else uses
    ok, why = find_token.verify(token, tokens)
    print(f"[token] self-check: {'VALID' if ok else 'INVALID'} - {why}")

    print()
    print("[token] now restart LM Studio, then start the chat app.")
    print(f"[token] to undo: py tools\\make_lm_token.py --restore")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
