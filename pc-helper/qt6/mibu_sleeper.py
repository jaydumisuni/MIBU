from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mibu_actions import (
    Result,
    adb_path,
    check_device_ready,
    run_tool,
    selected_adb_serial,
)
from mibu_update import CURRENT_VERSION


SLEEPER_CONTRACT_COMMIT = "671a2f752a953e4e5c765c9c284d8a449983d4c0"


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
            "smart_play_engine",
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
        from techguy_netunlock.sleeper.conversation import SleeperDialogueEngine
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
        self.dialogue = SleeperDialogueEngine(self.brain)

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

    def _smart_play_descriptor(self) -> Path | None:
        configured = os.environ.get("TTG_SMART_PLAY_DESCRIPTOR", "").strip()
        if configured:
            path = Path(configured).expanduser().resolve()
            return path if path.is_file() else None

        candidates: list[Path] = []
        if self.engine_source and self.engine_source not in {"installed/bundled"}:
            source = Path(self.engine_source).expanduser().resolve()
            for parent in (source, *source.parents):
                if parent.name == "Sleeper-agent":
                    candidates.append(
                        parent
                        / ".workspace"
                        / "smart-play-engine-build"
                        / "engine-manifest.json"
                    )
                    break

        sleeper_root = os.environ.get("SLEEPER_AGENT_ROOT", "").strip()
        if sleeper_root:
            candidates.append(
                Path(sleeper_root).expanduser().resolve()
                / ".workspace"
                / "smart-play-engine-build"
                / "engine-manifest.json"
            )

        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def smart_play_result(self) -> Result:
        """Run the canonical Sleeper Smart Play transaction.

        MIBU selects the job and reports the result. Sleeper owns the device,
        Service Mode, installer broker, proof, rollback, and release.
        """
        if not self.available:
            return Result(
                False,
                f"Sleeper is not attached: {self.error or self.engine_source}",
            )

        ready = check_device_ready()
        if not ready.ok:
            return ready
        serial = selected_adb_serial()
        if not serial:
            return Result(False, "Smart Play has no selected ADB target.")

        descriptor_path = self._smart_play_descriptor()
        if descriptor_path is None:
            return Result(
                False,
                "TTG Smart Play Engine descriptor is not available. "
                "Set TTG_SMART_PLAY_DESCRIPTOR or install the Sleeper engine bundle.",
            )
        tool = adb_path()
        if not tool:
            return Result(False, "ADB is not available for Smart Play.")

        from uuid import uuid4

        from techguy_netunlock.sleeper.adb_transport import ADBPosixTransport
        from techguy_netunlock.sleeper.android import AndroidADBResidentSleeper
        from techguy_netunlock.sleeper.service_lease import ServiceAuthorityLease
        from techguy_netunlock.sleeper.smart_play import SmartPlayServiceSession
        from techguy_netunlock.sleeper.smart_play_engine import (
            SmartPlayEngineDescriptor,
            TTGSmartPlayEngineStrategy,
        )

        try:
            descriptor = SmartPlayEngineDescriptor.load(descriptor_path)
            transport = ADBPosixTransport(
                serial,
                adb_path=tool,
                timeout_seconds=90.0,
                reconnect_window_seconds=45.0,
            )
            sleeper = AndroidADBResidentSleeper(transport)
            strategy = TTGSmartPlayEngineStrategy(sleeper, descriptor)

            # Recover evidence before mutation. A foreign GMS signer, unknown
            # account state, or other migration blocker must stop Smart Play
            # before Service Mode itself is upgraded.
            preflight = strategy.qualify()
            if not preflight.viable:
                return Result(
                    False,
                    "Smart Play stopped safely: "
                    + preflight.reason
                    + ". No package migration or Service Mode broker upgrade "
                    "was performed.",
                )

            sleeper.ensure_service_mode_package(
                descriptor.service_mode_apk,
                expected_sha256=descriptor.service_mode_sha256,
                expected_version_code=descriptor.service_mode_version_code,
            )
            sleeper.start()
            lease = ServiceAuthorityLease(
                "smart-play-" + uuid4().hex[:20],
                "mibu",
                serial,
            )
            session = SmartPlayServiceSession(
                sleeper,
                (strategy,),
                lease,
            )

            # Production release gate is Play Store. Qualification builds
            # add Gmail as the second real Google-app proof so we do not claim
            # compatibility from package presence or Play alone.
            if (
                descriptor.qualification_build
                and descriptor.gmail_proof_apk is not None
                and descriptor.gmail_proof_apk.is_file()
            ):
                proof_package = descriptor.gmail_proof_package
            else:
                proof_package = descriptor.qualification_proof_package

            result = session.run(proof_package=proof_package)
            if not result.success:
                attempt = result.attempts[-1] if result.attempts else None
                reason = (
                    attempt.error
                    if attempt and attempt.error
                    else next(
                        (
                            item.split("not-qualified:", 1)[1]
                            for item in (attempt.evidence if attempt else ())
                            if "not-qualified:" in item
                        ),
                        result.error or "qualification did not pass",
                    )
                )
                return Result(
                    False,
                    "Smart Play stopped safely: "
                    + reason
                    + ". No unqualified package migration was performed.",
                )

            completion = session.release(result)
            if not completion.committed:
                return Result(
                    False,
                    "Smart Play verification passed but commit proof was not completed.",
                )

            return Result(
                True,
                "Smart Play complete: TTG Smart Play Engine is provisioned, "
                "Google account integration is ready, Google Play Store opened "
                "host-native, and the qualification proof app opened successfully.",
            )
        except Exception as exc:
            return Result(False, f"Smart Play failed closed: {exc}")

    def ask_result(self, message: str) -> Result:
        if not self.available or self.brain is None or not hasattr(self, "dialogue"):
            return Result(False, f"Sleeper is not attached: {self.error or self.engine_source}")

        observation = self._current_observation()
        reply = self.dialogue.respond(message, observation=observation)
        return Result(True, reply.message)

    def set_current_job(self, job: str) -> Result:
        if not self.available or not hasattr(self, "dialogue"):
            return Result(False, f"Sleeper is not attached: {self.error or self.engine_source}")
        self.dialogue.set_job(job)
        return Result(True, f"Sleeper current caller-selected job: {self.dialogue.session.current_job}")

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
