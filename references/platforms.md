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
| pinterest | caption + 1 image + **board** | Pass the board as the target's `board_id` (boards are listed by `accounts` like Facebook Pages). |
| bluesky | caption (≤300) | Text, or 1–4 images. No video. |
| zalo | caption | Text article; immediate only (no scheduling). |
| twitter (X) | caption (≤280) | 1–4 images, or 1 video, or 1 GIF. Needs X connected first. |

<!-- PUBLISH-ALL-FORMATS-20261024 -->
## Formats and options (`platform_data` on the target)

Put these in the target, e.g. `--target '{"platform":"facebook","account_id":"...","platform_data":{"content_type":"reel"}}'`.
A wrong value is rejected at draft time with the key named; unknown keys are ignored.

- **instagram** `content_type`: `feed` (1 image) · `reel` (1 video) · `carousel` (2–10) · `stories` (1 image or a 3–60 s video; no caption shown).
  Options: `share_to_feed`, `alt_text`, `location_id`, `collaborators` (≤3 usernames), `cover_url`, `thumb_offset`,
  `user_tags` `[{"username","x","y"}]`, `is_ai_generated`, `audio_name`, `trial_params` `{"graduation_strategy":"MANUAL"|"SS_PERFORMANCE"}`.
- **facebook** no media = text post (add `link` for a link post); 1 image = photo; 2–10 images = album; 1 video = video.
  `content_type`: `reel` (vertical 3–90 s video) · `stories` (1 photo or a vertical 9:16 video ≥540×960, 3–90 s; no caption).
  Options: `cta_type` + `cta_link` (together), `title` (video/reel), `share_to_feed`, `alt_text`, `no_story`,
  `content_category`, `child_attachments` (2–10 links → link carousel).
- **tiktok** `media_type`: `video` or `photo` (2–35 JPEG/WebP). Options: `privacy_level`, `disable_comment`,
  `disable_duet`, `disable_stitch`, `is_aigc`, `auto_add_music` (photo), `photo_cover_index` (photo),
  `video_cover_timestamp_ms` (video), `brand_content_toggle`, `brand_organic_toggle`, `post_mode` (`direct`|`inbox` = save as a draft in the TikTok app).
- **youtube** video only, `--title` required. Options: `tags` (list), `category_id` (e.g. `"22"`), `made_for_kids`.
  Vertical videos up to 3 minutes become Shorts on YouTube's side.
- **linkedin** text, 1 image, 2–20 images, 1 video, or a link post: `article_url` + `article_title` (+ `article_description`).
  Options: `cta_label` + `cta_url` (need `article_url`), `alt_text`, `alt_texts`, `media_title`, `disable_reshare`.
- **threads** text, 1 image/video, or 2–20 items. Options: `topic_tag`, `link_attachment`, `alt_text`,
  `poll_attachment` `{"option_a","option_b","option_c?","option_d?"}` (text-only post), `reply_control`, `is_spoiler_media`.
- **google** `topicType`: `STANDARD` (default) · `EVENT` (needs `event` `{"title","schedule":{"startDate":{"year","month","day"},"endDate":{...}}}`)
  · `OFFER` (`offer` `{"couponCode","redeemOnlineUrl","termsConditions"}`, dates in `event`) · `ALERT` (`alertType`).
  Button: `callToAction` `{"actionType":"BOOK"|"ORDER"|"SHOP"|"LEARN_MORE"|"SIGN_UP"|"CALL","url"}` (`CALL` has no url). Text plus at most 1 image, no video.
- **pinterest** Options: `title` (≤100), `description` (≤800), `link`, `alt_text`; board as the target's `board_id`.
- **twitter (X)** Options: `reply_settings`, `made_with_ai`, `paid_partnership`.
- **First comment** (Instagram, Facebook, YouTube): `--first-comment "…"` on the draft.
- Not available through the API: TikTok/Threads/YouTube Stories, YouTube Community posts, LinkedIn documents and polls.

## Media

- Images: jpg / png / webp / gif. Videos: mp4.
- Media must be uploaded via the `upload` command first — the API only accepts
  its own hosted URLs.
- Identical files dedupe to the same URL (content-addressed) — re-uploading is
  harmless.

### File size

Large files are uploaded straight to object storage rather than through the
API, so multi-megabyte images and videos are fine. A 3.38MB image was verified
end-to-end on 2026-08-05. `upload` accepts up to 100MB.

Per-platform limits still apply (each platform enforces its own duration,
dimension, and size rules) — a rejection at draft time names the platform and
the reason; relay it to the user.

## Scheduling

- `--schedule` takes RFC3339 UTC (`2026-08-01T09:00:00Z`), at least 5 minutes
  ahead.
- Scheduling support varies by platform; unsupported combinations are rejected
  at draft time with an explanation.

## Limits

- Your workspace plan includes a monthly publishing quota; exceeding it returns
  a clear error.
- There is a daily safety cap per workspace (default 30 posts/day).
