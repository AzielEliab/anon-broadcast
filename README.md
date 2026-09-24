# AnonBroadcast

Local communique renderer. Text in, a small English formant voice, a desk reel, a metadata-culled MP4, and a SHA-256 receipt.

Author: Aziel Eliab. Apache-2.0.

The reel is rendered on the computer where you run it. Python 3.11+ and ffmpeg are required. The MP4 stays on that computer.

## Render

```bash
python3 -m anonbroadcast render --text "The note stays on this desk." --out communique.mp4
```

A file named `communique.receipt.json` is written beside the MP4. Its `sha256` is the digest of that MP4. The container is written without a title, comment, artist, date, location, or encoder name.

The voice reads basic Latin letters, digits, and simple punctuation, up to 480 characters. It is one local formant voice at 16 kHz, not a recording of a person.

## Download

The counted package is `anon-broadcast-0.1.0.tar.gz`, built from this repo by `python3 scripts/build_assets.py`.

There is no live landing in this repo yet. A teammate deploys the Worker after creating an isolated KV namespace:

- Worker name: `anon-broadcast-download-tracker`
- Route: `https://anon-broadcast-download-tracker.vibelock.workers.dev/`
- Config: `workers/download-tracker/wrangler.toml`
- KV binding: `DOWNLOADS`, namespace `ANON_BROADCAST_DOWNLOADS` (replace the placeholder id; do not reuse another product's KV)

`GET /download` returns the gzip package and counts the download, including other branches and forks. `GET /` is the landing.

## Tests

```bash
python3 scripts/build_assets.py
python3 -m unittest discover -s tests -v
node --test tests/worker.test.mjs
```
