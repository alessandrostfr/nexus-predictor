# V3 extraction policy

This policy controls APIs, tools, scraping and manual fallback in Nexus Predictor V3.

## Allowed order

1. Official API.
2. Existing maintained open-source tool.
3. Controlled static scraping with `httpx` + `BeautifulSoup`.
4. Browser scraping only as last resort.
5. CSV/manual fallback with traceable evidence.

## Forbidden behavior

- No login bypass.
- No credential exposure.
- No aggressive scraping.
- No audio or video download.
- No scraping without cache and rate limits.
- No feature generation from low-confidence or pending identity matches.
- No frontend invented values.

## yt-dlp policy

`yt-dlp` is evaluated in V3.4-A and prepared for V3.4-C.

Allowed future mode:

- metadata-only;
- `skip_download`;
- no audio download;
- no video download;
- cache required;
- timeout required;
- artist/source limit required;
- `feature_candidate=false` by default until review.

## SoundCloud policy

SoundCloud is a priority source for the hard dance/hard techno niche, but V3.4-A does not assume official access.

The path is:

1. Try official access/probe.
2. If unavailable, document `access_unconfirmed` or `access_unavailable`.
3. Prepare metadata-only fallback.
4. Require identity review before metrics become feature candidates.

## Manual fallback

Manual data is allowed only when it contains source, confidence and notes. Manual values are evidence, not predictions.
