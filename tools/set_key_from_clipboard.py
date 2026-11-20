#!/usr/bin/env python3
"""Store the model API key that is currently on the clipboard.

The key is a credential, and the safest place for it to travel is nowhere. So:
copy it in LM Studio, run this, and it is verified and written without ever being
typed into a prompt, printed, or pasted into a chat.

    py tools\\set_key_from_clipboard.py            # read, verify, store
    py tools\\set_key_from_clipboard.py --dry-run  # read and report, change nothing
    py tools\\set_key_from_clipboard.py --from-text "sk-lm-..."   # for testing

Verification is the same check the rest of the tooling uses: the passkey must hash
to what LM Studio stored. A wrong key is refused here rather than becoming a 401
later, and nothing is written unless it passes.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
CONFIG = os.path.join(APP, "config.json")
sys.path.insert(0, APP)

import find_token                                   # noqa: E402


def clipbrush() -> str:
    """Read the clipboard without printing it. PowerShell, because Windows."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
        capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="store the model API key from the clipboard")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-text", default=None, help="use this value instead of the clipboard")
    args = parser.parse_args(argv)

    token = (args.from_text if args.from_text is not None else clipbrush()).strip()
    if not token:
        print("[key] nothing on the clipboard")
        return 2

    # never echo the value, only its shape
    print(f"[key] clipboard holds {len(token)} character(s)")

    store = find_token.load_store(find_token.DEFAULT_STORE)
    if store is None:
        print("[key] cannot read LM Studio's token store - is LM Studio installed?")
        return 2
    records = find_token.registered_tokens(store)
    print(f"[key] registered: {[r.get('clientIdentifier') for r in records]}")

    ok, why = find_token.verify(token, records)
    print(f"[key] {find_token.mask(token)} -> {'VALID' if ok else 'INVALID'}: {why}")
    if not ok:
        print("[key] refused: nothing was written")
        return 1

    config = json.load(io.open(CONFIG, encoding="utf-8"))
    previous = config.get("model", {}).get("api_key", "")
    if previous == token:
        print("[key] config.json already holds this key; nothing to do")
        return 0

    if args.dry_run:
        print(f"[key] dry run: would replace {len(previous)}-character key with this one")
        return 0

    config.setdefault("model", {})["api_key"] = token
    json.dump(config, io.open(CONFIG, "w", encoding="utf-8", newline="\n"), indent=2)
    print(f"[key] stored in {CONFIG}")
    print("[key] restart the chat app for it to take effect")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
