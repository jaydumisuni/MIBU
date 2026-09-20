# MIBU ↔ Sleeper consumer qualification — 2026-09-20

## Frozen revisions

- MIBU integration commit: `4a771f8f615e4c6f9d7e45332f9477b8fdfe04e8`
- Sleeper consumer-context + Qualcomm correction commit: `c909d80c48ce27e68d246c8808991b263078cbad`

## Architecture proven

MIBU PC Helper consumes the canonical Sleeper Agent without copying or forking private Sleeper source. Public MIBU remains buildable without private repository access. Internal KRATOS MIBU auto-discovers the sibling `Sleeper-agent` project; authorised deployments may instead use an installed/bundled package or `SLEEPER_AGENT_ROOT`.

Sleeper receives the following consumer identity:

- tool_id: `mibu`
- name: `MIBU PC Helper`
- PC-helper version: `0.3.0`
- product family: `THETECHGUY TOOL`
- repository: `jaydumisuni/MIBU`

The consumer context is separate from device capabilities and does not grant mutation authority.

## Live physical observation

With Nodie and the Redmi both connected through ADB, MIBU's existing device selector chose the Xiaomi target without stopping or restarting the shared ADB server.

Observed through the MIBU → Sleeper bridge:

- vendor: Xiaomi
- model: `23076RA4BC`
- chipset: `SM4450`
- chipset family: Qualcomm
- transport: ADB
- matching Sleeper knowledge records: 13
- selected entry adapter: `android.adb-poweroff-cold-capture`
- entry qualification: candidate

No entry adapter was executed by this qualification. The candidate route was reported only as knowledge/routing evidence.

## Feedback into canonical Sleeper

The first MIBU live attachment exposed a generic Sleeper classifier defect: `SM4450` classified as Qualcomm alone but not when combined with the real signals `parrot + qcom + SM4450`. The correction was made in canonical Sleeper main, not locally in MIBU, and is frozen at `c909d80`.

## Proof

- Sleeper focused consumer/context + identity set: 29/29 PASS
- Sleeper full suite: 257/257 PASS
- Sleeper compileall: PASS
- Sleeper git diff --check: PASS
- MIBU focused Sleeper/contract set: 38/38 PASS
- MIBU full PC-helper suite with declared Selenium dependency: 48/48 PASS
- MIBU source-contract review: PASS
- MIBU compileall: PASS
- MIBU git diff --check: PASS
- live MIBU → canonical Sleeper attachment: PASS
- live Xiaomi observation: PASS
- destructive operations performed: false

The optional Qt offscreen construction check was not rerun on KRATOS because PySide6 is not installed on that host. MIBU's static source-contract review passed; Windows/Qt release qualification remains a separate platform proof.
