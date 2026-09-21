from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mibu_actions import Result, check_device_ready, run_tool
from mibu_update import CURRENT_VERSION


SLEEPER_CONTRACT_COMMIT = "25b2c6e26ee8258f601a5cbc03a17f8f88dd01b2"


def consumer_descriptor() -> dict[str, object]:
    return {
        "tool_id": "mibu",
        "name": "MIBU PC Helper",
        "version": CURRENT_VERSION,
        "product_family": "THETECHGUY TOOL",
        "repository": "jaydumisuni/MIBU",
        "host": os.environ.get("COMPUTERNAME") or socket.gethostname(),
        "capabilities": [
            "adb_transport",
            "fastboot_transport",
            "xiaomi_status_proof",
            "xiaomi_official_unlock_handoff",
            "browser_session_handoff",
            "reversible_system_updates",
            "shared_sleeper_query",
            "shared_learning_publish",
        ],
        "policy_tags": [
            "xiaomi_official_result_authoritative",
            "no_automatic_unlock_bypass",
            "no_token_logging",
            "user_authorised_device",
            "caller_selects_job",
            "partition_backup_before_write",
        ],
    }


def _activate_private_engine() -> tuple[bool, str]:
    try:
        import techguy_netunlock.sleeper.tool_context  # noqa: F401
        return True, "installed/bundled"
    except ImportError:
        pass

    configured = os.environ.get("SLEEPER_AGENT_ROOT", "").strip()
    repo_root = Path(__file__).resolve().parents[2]
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser().resolve())
    sibling = repo_root.parent / "Sleeper-agent"
    if sibling not in candidates:
        candidates.append(sibling)

    attempted: list[str] = []
    for candidate in candidates:
        src = candidate / "src"
        attempted.append(str(src))
        if not src.is_dir():
            continue
        value = str(src)
        if value not in sys.path:
            sys.path.insert(0, value)
        try:
            import techguy_netunlock.sleeper.tool_context  # noqa: F401
        except ImportError:
            continue
        return True, str(src)

    detail = ", ".join(attempted) if attempted else "no candidate paths"
    return False, f"no authorised Sleeper engine was found ({detail})"


@dataclass(frozen=True)
class MibuSleeperInspection:
    connected: bool
    consumer: dict[str, object]
    engine_source: str
    device_vendor: str = ""
    device_model: str = ""
    chipset_family: str = ""
    chipset: str = ""
    transports: tuple[str, ...] = ()
    entry_adapter: str = ""
    entry_qualification: str = ""
    knowledge_records: int = 0
    error: str = ""

    def message(self) -> str:
        consumer_name = str(self.consumer.get("name", "MIBU"))
        consumer_version = str(self.consumer.get("version", ""))
        if not self.connected:
            return f"Sleeper is not attached to {consumer_name} {consumer_version}: {self.error or self.engine_source}"
        tool = f"Sleeper attached to {consumer_name} {consumer_version} as tool_id={self.consumer.get('tool_id')}."
        if not self.device_model:
            return tool + " No ready ADB device is currently available for Sleeper observation."
        device = f"Device: {self.device_vendor} {self.device_model}".strip()
        chipset = f"; chipset={self.chipset or self.chipset_family or 'unknown'}"
        entry = f"; entry={self.entry_adapter or 'none'}"
        if self.entry_adapter and self.entry_qualification:
            entry += f" ({self.entry_qualification})"
        return tool + " " + device + chipset + entry + f"; matching knowledge={self.knowledge_records}."


class MibuSleeperBridge:
    def __init__(self) -> None:
        self.consumer = consumer_descriptor()
        available, source = _activate_private_engine()
        self.available = available
        self.engine_source = source
        self.error = "" if available else source
        self.context: Any | None = None
        self.brain: Any | None = None
        if not available:
            return
        from techguy_netunlock.sleeper.brain import SleeperBrain
        from techguy_netunlock.sleeper.tool_context import ConsumerToolContext

        self.context = ConsumerToolContext(
            tool_id=str(self.consumer["tool_id"]),
            name=str(self.consumer["name"]),
            version=str(self.consumer["version"]),
            product_family=str(self.consumer["product_family"]),
            repository=str(self.consumer["repository"]),
            host=str(self.consumer["host"]),
            capabilities=frozenset(str(v) for v in self.consumer["capabilities"]),
            policy_tags=frozenset(str(v) for v in self.consumer["policy_tags"]),
        )
        self.brain = SleeperBrain(consumer_tool=self.context)

    @staticmethod
    def _getprop(name: str) -> str:
        result = run_tool(["shell", "getprop", name], timeout=10)
        return result.message.strip() if result.ok else ""

    def _current_observation(self):
        ready = check_device_ready()
        if not ready.ok:
            return None

        from techguy_netunlock.core.bootstrap import EntryObservation, infer_chipset_family

        vendor = self._getprop("ro.product.manufacturer")
        model = self._getprop("ro.product.model")
        bootmode = self._getprop("ro.bootmode") or "normal"
        board = self._getprop("ro.board.platform")
        hardware = self._getprop("ro.hardware")
        soc = self._getprop("ro.soc.model")
        chipset_family = infer_chipset_family(board, hardware, soc)
        chipset = soc or board or hardware
        return EntryObservation(
            vendor=vendor,
            platform="android",
            model=model,
            modes=frozenset({bootmode}),
            transports=frozenset({"adb"}),
            chipset_family=chipset_family,
            chipset=chipset,
        )

    def inspect(self) -> MibuSleeperInspection:
        if not self.available or self.brain is None:
            return MibuSleeperInspection(False, self.consumer, self.engine_source, error=self.error)

        ready = check_device_ready()
        if not ready.ok:
            return MibuSleeperInspection(True, self.consumer, self.engine_source, error=ready.message)

        self.brain.refresh_knowledge()
        observation = self._current_observation()
        if observation is None:
            return MibuSleeperInspection(True, self.consumer, self.engine_source, error=ready.message)

        vendor = observation.vendor
        model = observation.model
        chipset_family = observation.chipset_family
        chipset = observation.chipset
        entry = self.brain.entry_for(observation, allow_candidate=True)
        knowledge = self.brain.knowledge_vault.select(observation)
        return MibuSleeperInspection(
            True,
            self.consumer,
            self.engine_source,
            device_vendor=vendor,
            device_model=model,
            chipset_family=chipset_family,
            chipset=chipset,
            transports=("adb",),
            entry_adapter=entry.adapter_id if entry else "",
            entry_qualification=entry.qualification.value if entry else "",
            knowledge_records=len(knowledge),
        )

    def status_result(self) -> Result:
        inspection = self.inspect()
        return Result(inspection.connected, inspection.message())

    def ask_result(self, message: str) -> Result:
        if not self.available or self.brain is None:
            return Result(False, f"Sleeper is not attached: {self.error or self.engine_source}")

        self.brain.refresh_knowledge()
        observation = self._current_observation()
        records = self.brain.query_knowledge(message, observation=observation, limit=6)
        if not records:
            return Result(
                True,
                "Sleeper has no matching shared knowledge yet. The caller still owns the job; "
                "Sleeper will use new evidence after it is published to the shared vault.",
            )

        lines = ["Sleeper shared knowledge:"]
        for record in records:
            provides = ", ".join(sorted(record.provides)[:4]) or "no capability labels"
            lines.append(f"- {record.record_id} [{record.state.value}]: {provides}")
        return Result(True, "\n".join(lines))

    def publish_knowledge(self, record) -> Result:
        if not self.available or self.brain is None:
            return Result(False, f"Sleeper is not attached: {self.error or self.engine_source}")
        try:
            changed = self.brain.publish_knowledge(record)
        except Exception as exc:
            return Result(False, f"Sleeper rejected learned knowledge: {exc}")
        action = "published" if changed else "already current"
        sync = getattr(self.brain, "last_sync_status", None)
        if sync is None:
            return Result(True, f"Sleeper shared knowledge {action}: {record.record_id}")
        synced, detail = sync
        suffix = f"; sync {'ok' if synced else 'pending'}: {detail}"
        return Result(True, f"Sleeper shared knowledge {action}: {record.record_id}{suffix}")
