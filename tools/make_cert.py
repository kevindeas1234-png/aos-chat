#!/usr/bin/env python3
"""Make a self-signed certificate for the chat app's HTTPS listener.

    py tools/make_cert.py

Writes cert.pem and key.pem beside the app, valid for this machine's names and
addresses: localhost, 127.0.0.1, the LAN address, and the hostname.

Why self-signed: a phone reaching this machine from outside needs *encryption*,
not a public identity, and getting a trusted certificate means owning a domain and
proving control of it. A self-signed certificate encrypts exactly as well; the
phone will warn once, and you accept it knowingly. If that warning bothers you,
that is a reasonable instinct - a tunnel that terminates TLS with a real
certificate is the better answer, and SECURITY.md says so.

The private key is written with owner-only permissions where the platform allows
it, and neither file is ever committed or banked.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
CERT = os.path.join(APP, "cert.pem")
KEY = os.path.join(APP, "key.pem")


def lan_address() -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        probe.close()
        return address
    except OSError:
        return "127.0.0.1"


def main() -> int:
    openssl = shutil.which("openssl")
    if not openssl:
        print("[cert] openssl was not found on PATH")
        print("[cert] on Windows it ships with Git for Windows, in Git\\usr\\bin")
        return 2

    host = socket.gethostname()
    lan = lan_address()
    san = f"DNS:localhost,DNS:{host},IP:127.0.0.1,IP:{lan}"

    if os.path.isfile(CERT) and "--force" not in sys.argv:
        print(f"[cert] {CERT} already exists; pass --force to replace it")
        print("[cert] replacing it means a phone must accept the new certificate again")
        return 1

    command = [
        openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", KEY, "-out", CERT,
        "-days", "825",
        "-subj", f"/CN={host}",
        "-addext", f"subjectAltName={san}",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("[cert] openssl failed:")
        print(result.stderr.strip()[:500])
        return 2

    try:                                  # best effort; Windows ignores this
        os.chmod(KEY, 0o600)
    except OSError:
        pass

    fingerprint = subprocess.run(
        [openssl, "x509", "-in", CERT, "-noout", "-fingerprint", "-sha256"],
        capture_output=True, text=True)
    print(f"[cert] wrote {CERT}")
    print(f"[cert] wrote {KEY}")
    print(f"[cert] valid for: localhost, {host}, 127.0.0.1, {lan}")
    if fingerprint.returncode == 0:
        print(f"[cert] {fingerprint.stdout.strip()}")
    print()
    print("[cert] add to config.json:")
    print('       "tls": {"port": 8443, "cert": "cert.pem", "key": "key.pem"}')
    print("[cert] the phone will warn once - that is what 'self-signed' means")
    return 0


if __name__ == "__main__":
    sys.exit(main())
