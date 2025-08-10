# bsky-stats-archive

Archiving Bluesky/ATProto stats from `https://bsky-stats.lut.li/` and posting a daily summary to Bluesky.

## What this does
- Fetches JSON from `https://bsky-stats.lut.li/` every day at 06:00 UTC via GitHub Actions
- Archives the full JSON to `data/YYYY/MM/YYYY-MM-DD.json`
- Posts a summary (total users, total likes, growth rate per second, and deltas vs. previous archive) to Bluesky using the `atproto` Python library

## Repository structure
- `scripts/archive_and_post.py`: main script to fetch, archive, compute deltas, and post
- `data/`: archived daily snapshots (committed to the repo)
- `.github/workflows/daily.yml`: scheduled workflow
- `requirements.txt`: Python dependencies

## Setup
1. Fork this repository.
2. In the fork, go to Settings → Secrets and variables → Actions → New repository secret and add:
   - `BSKY_HANDLE`: your Bluesky handle (e.g. `name.bsky.social`)
   - `BSKY_APP_PASSWORD`: an app password generated in Bluesky settings
3. The workflow is already scheduled at 06:00 UTC daily. You can run it manually from the Actions tab with "Run workflow".

## Local run (optional)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BSKY_HANDLE="your.handle"
export BSKY_APP_PASSWORD="your-app-password"
python scripts/archive_and_post.py
```

## Notes
- Posting failures will not fail the workflow; archives are still saved and committed.
- Data source: `https://bsky-stats.lut.li/`.
