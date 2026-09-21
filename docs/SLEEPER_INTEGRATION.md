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

- tested Sleeper commit: 25b2c6e26ee8258f601a5cbc03a17f8f88dd01b2
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
