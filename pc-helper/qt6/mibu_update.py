from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

CURRENT_VERSION = "0.3.0"
LATEST_RELEASE_API = "https://api.github.com/repos/jaydumisuni/MIBU/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    release_url: str
    update_available: bool


def _version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().lstrip("v").split("-", 1)[0]
    try:
        return tuple(int(part) for part in clean.split("."))
    except ValueError:
        return (0,)


def check_for_update(timeout: int = 6) -> UpdateInfo:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"MIBU-PC-Helper/{CURRENT_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    latest = str(payload.get("tag_name") or "").strip().lstrip("v")
    if not latest:
        raise ValueError("GitHub latest release has no version tag")
    release_url = str(payload.get("html_url") or "https://github.com/jaydumisuni/MIBU/releases/latest")
    return UpdateInfo(CURRENT_VERSION, latest, release_url, _version_tuple(latest) > _version_tuple(CURRENT_VERSION))
