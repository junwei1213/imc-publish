# Platform notes

Server-side validation is fail-closed: if a platform rejects the payload or
doesn't support scheduling, the draft/confirm call returns a clear 4xx — relay
it to the user.

| Platform | Required | Notes |
|---|---|---|
| instagram | caption | Feed post by default. Video: mp4. |
| tiktok | caption | Defaults to public visibility. Photo posts and videos supported. |
| facebook | caption | Posts to the account's **default Page** unless a `page_id` is passed in the target: `{"platform":"facebook","account_id":"...","page_id":"1234567890"}`. Pages are listed by `accounts`. |
| youtube | caption + **title** | `--title` is mandatory. |
| linkedin | caption | Personal profile by default. |
| threads | caption | Text-first; media optional. |
| google | caption + media | Google Business Profile post. |
| telegram | caption + explicit target | Must pass a target with the group chat id: `{"platform":"telegram","account_id":"...","platform_data":{"chat_id":"-100123456789"}}`. Telegram publishes immediately (no scheduling) and must be the only platform in its draft. |

## Media

- Images: jpg / png / webp / gif. Videos: mp4.
- Media must be uploaded via the `upload` command first — the API only accepts
  its own hosted URLs.
- Identical files dedupe to the same URL (content-addressed) — re-uploading is
  harmless.

### Current size limit (important)

`upload` accepts files up to 100MB, but the publishing channel currently caps
each file at **about 1MB**. Anything larger is accepted by `upload` and then
rejected at draft time with a 413 explaining the limit.

In practice this means **video publishing is not available through this API
right now** — a usable mp4 is far over 1MB. If the user wants to publish a
video, don't burn their time uploading it: tell them video publishing goes
through their workspace's managed publishing (ask their InstallMyClaw contact),
and use this API for text and small images in the meantime. This limit is
expected to be raised; check by publishing a >1MB image if unsure.

## Scheduling

- `--schedule` takes RFC3339 UTC (`2026-08-01T09:00:00Z`), at least 5 minutes
  ahead.
- Scheduling support varies by platform; unsupported combinations are rejected
  at draft time with an explanation.

## Limits

- Your workspace plan includes a monthly publishing quota; exceeding it returns
  a clear error.
- There is a daily safety cap per workspace (default 30 posts/day).
