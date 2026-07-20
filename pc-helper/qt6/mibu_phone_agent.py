from __future__ import annotations

import re
import time
from dataclasses import dataclass

from mibu_actions import Result, check_device_ready, run_tool


@dataclass(frozen=True)
class PhoneNetworkState:
    cellular_connected: bool
    cellular_validated: bool
    wifi_enabled: bool
    sim_ready: bool
    operator: str
    raw_summary: str

    @property
    def ready_for_xiaomi(self) -> bool:
        return self.cellular_connected and self.cellular_validated and not self.wifi_enabled and self.sim_ready


def _parse_network_state(connectivity: str, wifi: str, sim: str, operator: str) -> PhoneNetworkState:
    cellular_connected = bool(re.search(r"MOBILE\[[^]]+\]\s+CONNECTED", connectivity, re.IGNORECASE))
    cellular_validated = cellular_connected and bool(
        re.search(r"Transports:\s*CELLULAR[^\n\r]*Capabilities:[^\n\r]*VALIDATED", connectivity, re.IGNORECASE)
        or re.search(r"MOBILE\[[^]]+\]\s+CONNECTED[\s\S]{0,1800}?IS_VALIDATED", connectivity, re.IGNORECASE)
    )
    wifi_enabled = "wifi is enabled" in wifi.lower() and "wifi is disabled" not in wifi.lower()
    sim_ready = any(value.strip().upper() in {"READY", "LOADED"} for value in sim.split(","))
    clean_operator = operator.strip().strip(",") or "unknown"
    summary = (
        f"Cellular connected: {'yes' if cellular_connected else 'no'}\n"
        f"Cellular validated: {'yes' if cellular_validated else 'no'}\n"
        f"Wi-Fi enabled: {'yes' if wifi_enabled else 'no'}\n"
        f"SIM ready: {'yes' if sim_ready else 'no'}\n"
        f"Operator: {clean_operator}"
    )
    return PhoneNetworkState(cellular_connected, cellular_validated, wifi_enabled, sim_ready, clean_operator, summary)


def read_phone_network_state() -> tuple[Result, PhoneNetworkState | None]:
    ready = check_device_ready()
    if not ready.ok:
        return ready, None
    connectivity = run_tool(["shell", "dumpsys", "connectivity"], timeout=30)
    wifi = run_tool(["shell", "cmd", "wifi", "status"], timeout=15)
    sim = run_tool(["shell", "getprop", "gsm.sim.state"], timeout=10)
    operator = run_tool(["shell", "getprop", "gsm.operator.alpha"], timeout=10)
    if not connectivity.ok:
        return Result(False, "Android connectivity state could not be read: " + connectivity.message), None
    state = _parse_network_state(connectivity.message, wifi.message, sim.message, operator.message)
    return Result(True, state.raw_summary), state


def set_mobile_data(enabled: bool, wait_seconds: int = 20) -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    command = run_tool(["shell", "svc", "data", "enable" if enabled else "disable"], timeout=15)
    if not command.ok:
        return Result(False, f"Android rejected the mobile-data command: {command.message}")
    deadline = time.monotonic() + max(1, wait_seconds)
    last: PhoneNetworkState | None = None
    while time.monotonic() < deadline:
        result, state = read_phone_network_state()
        if result.ok and state is not None:
            last = state
            if enabled and state.cellular_connected and state.cellular_validated:
                return Result(True, "Mobile data is enabled, connected and validated.\n" + state.raw_summary)
            if not enabled and not state.cellular_connected:
                return Result(True, "Mobile data is disabled and the cellular network disconnected.\n" + state.raw_summary)
        time.sleep(0.75)
    desired = "connected and validated" if enabled else "disconnected"
    return Result(False, f"Android accepted the command but mobile data was not verified {desired}.\n" + (last.raw_summary if last else "No network state returned."))


def set_wifi(enabled: bool, wait_seconds: int = 12) -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    command = run_tool(["shell", "svc", "wifi", "enable" if enabled else "disable"], timeout=15)
    if not command.ok:
        return Result(False, f"Android rejected the Wi-Fi command: {command.message}")
    deadline = time.monotonic() + max(1, wait_seconds)
    last: PhoneNetworkState | None = None
    while time.monotonic() < deadline:
        result, state = read_phone_network_state()
        if result.ok and state is not None:
            last = state
            if state.wifi_enabled == enabled:
                return Result(True, f"Wi-Fi is {'enabled' if enabled else 'disabled'}.\n" + state.raw_summary)
        time.sleep(0.6)
    return Result(False, f"Android accepted the command but the Wi-Fi state was not verified.\n" + (last.raw_summary if last else "No network state returned."))


def prepare_xiaomi_mobile_network() -> Result:
    state_result, state = read_phone_network_state()
    if not state_result.ok or state is None:
        return state_result
    if not state.sim_ready:
        return Result(False, "A ready SIM is required for the Xiaomi application request.\n" + state.raw_summary)
    if state.wifi_enabled:
        wifi = set_wifi(False)
        if not wifi.ok:
            return wifi
    refreshed, state = read_phone_network_state()
    if not refreshed.ok or state is None:
        return refreshed
    if not (state.cellular_connected and state.cellular_validated):
        mobile = set_mobile_data(True)
        if not mobile.ok:
            return mobile
    verified, final = read_phone_network_state()
    if not verified.ok or final is None:
        return verified
    if not final.ready_for_xiaomi:
        return Result(False, "Phone network preparation did not reach the required state.\n" + final.raw_summary)
    return Result(True, "Xiaomi request network verified: SIM ready, Wi-Fi off, mobile data connected and validated.\n" + final.raw_summary)
