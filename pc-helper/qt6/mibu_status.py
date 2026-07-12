from __future__ import annotations

import re
import time
from dataclasses import dataclass

from mibu_actions import PROOF_NONCE_EXTRA, Result, _proof_nonce, check_device_ready, run_tool

STATUS_ENTRY = "com.thetechguy.mibu/.StatusActivity"
STATUS_TAG = "MIBU_STATUS"


@dataclass(frozen=True)
class PhoneStatus:
    nonce: str
    captures: str
    verification: str
    community: str
    lanes: str
    raw: str

    @property
    def captures_ready(self) -> bool:
        return self.captures == "READY"

    @property
    def timing_complete(self) -> bool:
        return self.verification in {"TIMING_WINDOW_REACHED", "READY_FOR_MI_UNLOCK_VERIFICATION"}


_STATUS_PATTERN = re.compile(
    r"STATUS\s+nonce=(\S+)\s+captures=(\S+)\s+verification=(\S+)\s+community=(\S+)\s+lanes=(.+)$"
)


def _parse_status(line: str, expected_nonce: str | None = None) -> PhoneStatus | None:
    match = _STATUS_PATTERN.search(line.strip())
    if not match:
        return None
    nonce = match.group(1)
    if expected_nonce is not None and nonce != expected_nonce:
        return None
    return PhoneStatus(
        nonce=nonce,
        captures=match.group(2),
        verification=match.group(3),
        community=match.group(4),
        lanes=match.group(5),
        raw=line.strip(),
    )


def query_phone_status(wait_seconds: int = 6) -> tuple[Result, PhoneStatus | None]:
    ready = check_device_ready()
    if not ready.ok:
        return ready, None
    nonce = _proof_nonce()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", STATUS_ENTRY,
        "--es", PROOF_NONCE_EXTRA, nonce,
    ], timeout=30)
    if not started.ok:
        return Result(False, started.message or "Android status activity did not start."), None

    deadline = time.monotonic() + max(1, wait_seconds)
    last = ""
    while time.monotonic() < deadline:
        logs = run_tool(["logcat", "-d", "-s", f"{STATUS_TAG}:I", "*:S"], timeout=10)
        last = logs.message
        if logs.ok:
            for line in reversed(logs.message.splitlines()):
                parsed = _parse_status(line, expected_nonce=nonce)
                if parsed:
                    return Result(True, parsed.raw), parsed
        time.sleep(0.35)
    return Result(False, f"Android status proof for nonce {nonce} was not returned. Last filtered log: {last or 'none'}"), None
