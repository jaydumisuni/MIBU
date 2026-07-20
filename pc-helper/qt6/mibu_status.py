from __future__ import annotations

import re
import time
from dataclasses import dataclass

from mibu_actions import EXPECTED_APP_VERSION, PROOF_NONCE_EXTRA, Result, _proof_nonce, check_device_ready, run_tool

STATUS_ENTRY = "com.thetechguy.mibu/.StatusActivity"
STATUS_TAG = "MIBU_STATUS"
EXPECTED_PROOF_PROTOCOL = 3


@dataclass(frozen=True)
class PhoneStatus:
    nonce: str
    protocol: int
    app_version: str
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
        return self.verification == "READY_FOR_MI_UNLOCK_VERIFICATION"

    @property
    def contract_current(self) -> bool:
        return self.protocol == EXPECTED_PROOF_PROTOCOL and self.app_version == EXPECTED_APP_VERSION


_STATUS_PATTERN = re.compile(
    r"STATUS\s+nonce=(\S+)\s+protocol=(\d+)\s+app=(\S+)\s+captures=(\S+)\s+verification=(\S+)\s+community=(\S+)\s+lanes=(.+)$"
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
        protocol=int(match.group(2)),
        app_version=match.group(3),
        captures=match.group(4),
        verification=match.group(5),
        community=match.group(6),
        lanes=match.group(7),
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
                if not parsed:
                    continue
                if parsed.protocol != EXPECTED_PROOF_PROTOCOL:
                    return Result(
                        False,
                        f"MIBU proof protocol {parsed.protocol} is incompatible; expected {EXPECTED_PROOF_PROTOCOL}. Install the bundled APK.",
                    ), None
                if parsed.app_version != EXPECTED_APP_VERSION:
                    return Result(
                        False,
                        f"Installed MIBU version {parsed.app_version} is not the required {EXPECTED_APP_VERSION}. Install/update the bundled APK.",
                    ), None
                return Result(True, parsed.raw), parsed
        time.sleep(0.35)
    return Result(False, f"Android status proof for nonce {nonce} was not returned. Last filtered log: {last or 'none'}"), None
