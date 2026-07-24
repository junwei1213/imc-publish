#!/usr/bin/env python3
"""IMC Publishing API client (stdlib only).

Environment:
  IMC_PUBLISH_API_KEY   required, workspace publishing key
  IMC_PUBLISH_BASE      optional, default https://dashboard.installmyclaw.com

Commands:
  accounts                                 List connected social accounts
  upload <file>                            Upload local media, prints hosted URL
  draft --caption C --platforms a,b [...]  Create a draft, prints preview + confirm token
  confirm <draft_id> <confirm_token>       Publish a prepared draft
  post --caption C --platforms a,b [...]   One-call publish (trusted keys only)
  status <post_id>                         Check publish status (per-platform results)
  list [--limit N]                         Recent posts from this workspace
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("IMC_PUBLISH_BASE", "https://dashboard.installmyclaw.com").rstrip("/")


def _load_key() -> str:
    key = os.environ.get("IMC_PUBLISH_API_KEY", "").strip()
    if key:
        return key
    path = os.path.expanduser("~/.config/imc-publish/key")
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return ""


KEY = _load_key()

MEDIA_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
}


def _die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _request(method: str, path: str, *, body: bytes | None = None, headers: dict | None = None):
    if not KEY:
        _die("IMC_PUBLISH_API_KEY is not set. Ask your workspace owner for a publishing key.")
    request = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Accept": "application/json",
            "User-Agent": "imc-publish-skill/1.0",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            detail = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
        except ValueError:
            detail = raw[:2000]
        _die(f"HTTP {exc.code} {path}\n{detail}", 2)
    except urllib.error.URLError as exc:
        _die(f"cannot reach publishing service: {exc.reason}", 3)


def _json_request(method: str, path: str, payload: dict):
    return _request(
        method,
        path,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def _print(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_accounts(_args) -> None:
    _print(_request("GET", "/v1/publish/accounts"))


def cmd_upload(args) -> None:
    path = args.file
    if not os.path.isfile(path):
        _die(f"file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    mime = MEDIA_MIME.get(ext) or mimetypes.guess_type(path)[0]
    if mime not in set(MEDIA_MIME.values()):
        _die(f"unsupported media type: {ext} (use jpg/png/webp/gif/mp4)")
    size = os.path.getsize(path)
    if size > 100 * 1024 * 1024:
        _die("file exceeds the 100MB upload limit")
    with open(path, "rb") as handle:
        raw = handle.read()
    _print(
        _request(
            "POST",
            "/v1/publish/media",
            body=raw,
            headers={"Content-Type": mime, "X-Filename": os.path.basename(path)},
        )
    )


def _draft_payload(args) -> dict:
    payload = {
        "caption": args.caption,
        "platforms": [item.strip() for item in args.platforms.split(",") if item.strip()],
        "publish_now": not args.schedule,
    }
    if args.title:
        payload["title"] = args.title
    if args.media:
        payload["media_urls"] = [item.strip() for item in args.media.split(",") if item.strip()]
    if args.schedule:
        payload["scheduled_at"] = args.schedule
    if args.language:
        payload["language"] = args.language
    targets = []
    for raw in args.target or []:
        try:
            targets.append(json.loads(raw))
        except ValueError:
            _die(f"--target must be JSON, got: {raw}")
    if targets:
        payload["targets"] = targets
    return payload


def cmd_draft(args) -> None:
    _print(_json_request("POST", "/v1/publish/drafts", _draft_payload(args)))


def cmd_confirm(args) -> None:
    _print(
        _json_request(
            "POST",
            f"/v1/publish/drafts/{int(args.draft_id)}/confirm",
            {"confirm_token": args.confirm_token},
        )
    )


def cmd_post(args) -> None:
    _print(_json_request("POST", "/v1/publish/posts", _draft_payload(args)))


def cmd_status(args) -> None:
    _print(_request("GET", f"/v1/publish/posts/{int(args.post_id)}"))


def cmd_list(args) -> None:
    _print(_request("GET", f"/v1/publish/posts?limit={int(args.limit)}"))


def _add_draft_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--caption", required=True)
    parser.add_argument("--platforms", required=True, help="comma-separated, e.g. instagram,tiktok")
    parser.add_argument("--title", help="required for youtube")
    parser.add_argument("--media", help="comma-separated hosted media URLs (from `upload`)")
    parser.add_argument("--schedule", help="RFC3339 UTC time, e.g. 2026-08-01T09:00:00Z")
    parser.add_argument("--language", help="content language hint, e.g. en / zh")
    parser.add_argument(
        "--target",
        action="append",
        help='JSON per platform when needed, e.g. \'{"platform":"telegram","account_id":"...","platform_data":{"chat_id":"-100123456"}}\'',
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="imc-publish", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("accounts").set_defaults(fn=cmd_accounts)

    upload = sub.add_parser("upload")
    upload.add_argument("file")
    upload.set_defaults(fn=cmd_upload)

    draft = sub.add_parser("draft")
    _add_draft_args(draft)
    draft.set_defaults(fn=cmd_draft)

    confirm = sub.add_parser("confirm")
    confirm.add_argument("draft_id")
    confirm.add_argument("confirm_token")
    confirm.set_defaults(fn=cmd_confirm)

    post = sub.add_parser("post")
    _add_draft_args(post)
    post.set_defaults(fn=cmd_post)

    status = sub.add_parser("status")
    status.add_argument("post_id")
    status.set_defaults(fn=cmd_status)

    listing = sub.add_parser("list")
    listing.add_argument("--limit", default=20)
    listing.set_defaults(fn=cmd_list)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
