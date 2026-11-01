#!/usr/bin/env python3
"""Push the tiles in tiles/ to a TV running Aerial, through Aerial's own phone page.

Aerial listens on port 8790 for as long as it runs. The address, token included, is shown
on the TV: Control Center -> 个性化 (press BACK on Home to open the Control Center).
It looks like  http://192.168.1.20:8790/abc12345/

Usage:
    python install.py http://192.168.1.20:8790/abc12345/
    python install.py http://192.168.1.20:8790/abc12345/ --only tv.huan.aliyunpan
    python install.py http://192.168.1.20:8790/abc12345/ --reset tv.huan.aliyunpan

--reset puts an app back to the icon Aerial draws for it, undoing a custom picture.
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def post_multipart(url: str, fields: dict, files: dict) -> str:
    boundary = "----aerial" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode()
        body += str(value).encode() + b"\r\n"
    for name, path in files.items():
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (name, filename)).encode()
        body += ("Content-Type: %s\r\n\r\n" % ctype).encode()
        with open(path, "rb") as fh:
            body += fh.read()
        body += b"\r\n"
    body += ("--%s--\r\n" % boundary).encode()

    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def post_form(url: str, fields: dict) -> str:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="http://<tv-ip>:8790/<token>/")
    ap.add_argument("--only", nargs="*", help="only these package names")
    ap.add_argument("--reset", nargs="*", metavar="PACKAGE", help="restore these apps' own art")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    manifest = json.load(open(os.path.join(ROOT, "manifest.json"), encoding="utf-8"))

    if args.reset:
        for pkg in args.reset:
            print("reset", pkg, "...", end=" ")
            if args.dry_run:
                print("(dry run)")
                continue
            try:
                post_form(base + "/api/icon/reset", {"app": pkg})
                print("ok")
            except urllib.error.URLError as exc:
                print("failed:", exc)
        return

    for item in manifest["tiles"]:
        pkg = item["package"]
        if args.only and pkg not in args.only:
            continue
        path = os.path.join(ROOT, "tiles", item["file"])
        print("%-34s %-10s" % (pkg, item["label"]), end=" ")
        if args.dry_run:
            print("(dry run)")
            continue
        try:
            out = post_multipart(base + "/api/icon", {"app": pkg}, {"photo": path})
            print("ok" if json.loads(out).get("saved") else "refused")
        except urllib.error.URLError as exc:
            print("failed:", exc)
            sys.exit(1)


if __name__ == "__main__":
    main()
