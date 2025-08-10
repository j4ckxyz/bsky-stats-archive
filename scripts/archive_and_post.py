#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import requests

try:
    from atproto import Client
except Exception as exc:  # pragma: no cover
    print(f"Failed to import atproto library: {exc}", file=sys.stderr)
    sys.exit(1)

STATS_URL = "https://bsky-stats.lut.li/"


def fetch_stats() -> dict:
    response = requests.get(STATS_URL, timeout=20)
    response.raise_for_status()
    data = response.json()
    # Basic validation
    required_keys = [
        "total_users",
        "total_posts",
        "total_follows",
        "total_likes",
        "users_growth_rate_per_second",
        "last_update_time",
        "next_update_time",
    ]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing key in response: {key}")
    return data


def ensure_archive_path(root: Path, dt: datetime) -> Path:
    archive_dir = root / "data" / dt.strftime("%Y") / dt.strftime("%m")
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / f"{dt.strftime('%Y-%m-%d')}.json"


def find_previous_snapshot(root: Path, exclude_path: Path) -> Optional[Path]:
    data_root = root / "data"
    if not data_root.exists():
        return None
    snapshots = sorted(data_root.rglob("*.json"))
    snapshots = [p for p in snapshots if p != exclude_path]
    if not snapshots:
        return None
    return snapshots[-1]


def load_json(path: Path) -> Optional[dict]:
    if not path or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def human_int(n: int) -> str:
    return f"{n:,}"


def human_rate(r: float) -> str:
    return f"{r:.4f}"


def compute_deltas(current: dict, previous: Optional[dict]) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    if not previous:
        return None, None, None
    du = int(current.get("total_users", 0)) - int(previous.get("total_users", 0))
    dl = int(current.get("total_likes", 0)) - int(previous.get("total_likes", 0))
    dr = float(current.get("users_growth_rate_per_second", 0.0)) - float(previous.get("users_growth_rate_per_second", 0.0))
    return du, dl, dr


def compose_post_text(now_utc: datetime, current: dict, deltas: Tuple[Optional[int], Optional[int], Optional[float]]) -> str:
    du, dl, dr = deltas
    parts = []
    parts.append(f"Bluesky Daily Stats — {now_utc.strftime('%Y-%m-%d %H:%M')} UTC")
    parts.append(f"Users: {human_int(int(current['total_users']))}" + (f" (↑{human_int(du)})" if du is not None else ""))
    parts.append(f"Likes: {human_int(int(current['total_likes']))}" + (f" (↑{human_int(dl)})" if dl is not None else ""))
    parts.append(
        "Growth rate: "
        + human_rate(float(current["users_growth_rate_per_second"]))
        + "/s"
        + (f" (Δ{human_rate(dr)}/s)" if dr is not None else "")
    )
    parts.append("Source: https://bsky-stats.lut.li/")
    return "\n".join(parts)


def post_to_bluesky(text: str) -> None:
    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_APP_PASSWORD")
    if not handle or not password:
        raise RuntimeError("Missing BSKY_HANDLE or BSKY_APP_PASSWORD environment variables")

    client = Client()
    client.login(handle, password)
    client.send_post(text)


def main() -> int:
    now_utc = datetime.now(timezone.utc)
    repo_root = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()

    stats = fetch_stats()

    # Archive
    target_path = ensure_archive_path(repo_root, now_utc)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Previous snapshot for deltas
    prev_path = find_previous_snapshot(repo_root, target_path)
    prev_stats = load_json(prev_path) if prev_path else None

    # Compose and post
    deltas = compute_deltas(stats, prev_stats)
    post_text = compose_post_text(now_utc, stats, deltas)

    # Print for logs
    print(post_text)

    # Post to Bluesky (best-effort; do not fail the job if posting fails)
    try:
        post_to_bluesky(post_text)
    except Exception as exc:
        print(f"Warning: Failed to post to Bluesky: {exc}", file=sys.stderr)
        # Continue without failing

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.HTTPError as http_err:
        print(f"HTTP error: {http_err}", file=sys.stderr)
        time.sleep(2)
        sys.exit(1)
    except Exception as e:
        print(f"Unhandled error: {e}", file=sys.stderr)
        sys.exit(1)
