# Sleeper Agent integration

MIBU is a consumer of the canonical private Sleeper Agent engine; it does not vendor or fork Sleeper source.

## Consumer identity

- tool_id: mibu
- name: MIBU PC Helper
- version source: mibu_update.CURRENT_VERSION
- repository: jaydumisuni/MIBU
- product family: THETECHGUY TOOL

MIBU declares its host-side capabilities and guardrails through Sleeper ConsumerToolContext. Sleeper keeps this consumer identity separate from device capabilities and carries it in its brain/COG state.

## Public versus internal builds

The public MIBU repository must remain buildable without access to the private Sleeper Agent repository. mibu_sleeper.py therefore attaches Sleeper only when the package is already installed/bundled, SLEEPER_AGENT_ROOT points to an authorised local Sleeper-agent checkout, or a sibling Sleeper-agent project exists beside the MIBU project (the KRATOS layout).

Public standalone mode does not invent Sleeper results. Internal attached mode uses the canonical engine and current shared knowledge.

## Current contract

- tested Sleeper commit: 19d69a1cbbe8a4d4b76239097d4876530d06943b
- MIBU PC Helper can query sleeper status from its assistant.
- With ADB available, the bridge presents the connected Android observation to Sleeper and reports the selected entry adapter, its qualification state, and matching knowledge count.
- Consumer context never grants mutation authority; Sleeper qualification and safety gates remain authoritative.

## Shared learning and assistant routing

MIBU does not own a private Sleeper brain. In internal attached mode it uses the canonical SleeperBrain from the Sleeper-agent repository.

- Sleeper status checks the canonical engine, shared knowledge and current observation.
- Other assistant messages addressed to Sleeper are routed to the canonical Sleeper knowledge query surface.
- MIBU may publish structured learned knowledge through the canonical Sleeper brain. The host vault is updated first, then the existing GitHub runtime-vault sync is attempted.
- Every attached Sleeper consumer refreshes merged peer knowledge instead of carrying a tool-local learned copy.
- The tool/user selects the requested job. Sleeper supplies known implementation/capability knowledge and does not autonomously choose a different job.
- Before any partition write/erase/repartition plan, Sleeper requires the matching partition backup capability. The planner inserts a compatible backup primitive when available; otherwise the mutation plan is rejected.

### Assistant dialogue behavior

The MIBU assistant now uses Sleeper's canonical dialogue layer rather than raw keyword retrieval.

- Questions are classified before knowledge lookup.
- Planning questions do not become active jobs.
- Explicit job statements are remembered for the current Sleeper session.
- Real MIBU assistant operations publish their caller-selected job to Sleeper before dispatch.
- Code/pseudocode supplied in chat can be structurally inspected and discussed, but is not executed automatically or promoted to shared knowledge without evidence.
- Comparisons are scoped to the current device identity so evidence from a different vendor/model/chipset is not mixed into the answer.

## Plain assistant operation language

MIBU's direct built-in controls keep priority. Other operation/research phrases are delegated to the canonical Sleeper dialogue engine even when the user does not prefix the message with "Sleeper".

Examples include `unlock bootload`, `unlock network`, `wipe`, `bypass this`, `delete this`, `check this`, `research ...`, `find a way ...`, and `see what can happen ...`.

MIBU only performs routing here. Semantic meaning, target/referent resolution, mutation/destructive classification and exploratory objective parsing remain owned by canonical Sleeper.

## Third-party 17Unlock donor finding (2026-10-21)

Canonical donor review: `jaydumisuni/bootloader-tokenit` commit `8b8c19a`, `docs/evidence/V0_6_17UNLOCK_DONOR_OBSERVATION_20261021.md` and `17UNLOCK_DONOR_CAPABILITY_MANIFEST.json`.

The observed unsigned `17Unlockv1.0.3.exe` is not a general Xiaomi unlock engine. Its decompiled local exploit eligibility is limited to `pudding`, `popsicle`, `pandora`, `nezha`, and `myron`, with security patches no later than 2026-07-13. On the observed Redmi Note 12R `sky / OS2.0.204.0.VMWCNXM`, it reports **unsupported** and disables Unlock; the handset remains locked at the observed checkpoint.

The donor's method attempts temporary root, ABL slot substitution, an `efisp` write, FRP erase, a `misc` wipe-data write, and eventual ABL restoration. Its success condition is invalid because FRP erase success alone can trigger a success message even without independently confirmed bootloader unlock.

**MIBU/Sleeper contract:** classify this donor as read-only knowledge, not executable authority. Do not reuse or bundle the donor exploit images, issue cross-model ABL/efisp/FRP/misc writes, or treat reported success as proof. Continue using the existing canonical Sleeper Director, MIBU-owned device transport, backup qualification, and exact device/firmware guards. TTG Reverse Engineering owns any subsequent offline analysis; TokenIt owns eligibility/authorization evidence. A real integration would require independent device-specific proof, verified backups/rollback, and post-reboot physical bootloader-state readback. This finding does **not** qualify an unlock operation for `sky`.
