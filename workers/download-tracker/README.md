# anon-broadcast download tracker

Isolated Worker `anon-broadcast-download-tracker`. Project `anon-broadcast`.
Package `anon-broadcast-0.1.0.tar.gz` is the source tree built from this repo.

GET `/` is the landing. It increments page views.
GET `/download` increments downloads and returns the gzip package (HTTP 200, no redirect).
GET `/count` returns `{project, views, downloads, total}`. `total` is downloads.
GET `/stats` breaks counts down by repo, branch, and fork.
POST `/event` records a download from another branch or fork.
GET `/install.sh` prints the installer. The script's curl of `/download` is the counted fetch.

Create KV namespace `ANON_BROADCAST_DOWNLOADS` and put its id in `wrangler.toml` before deploy.
Do not reuse another product's KV id. Do not deploy from this tree if the id is still the placeholder.

Host after deploy: https://anon-broadcast-download-tracker.vibelock.workers.dev

Author: Aziel Eliab. Apache-2.0.
