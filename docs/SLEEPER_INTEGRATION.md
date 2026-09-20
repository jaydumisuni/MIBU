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

- tested Sleeper commit: c909d80c48ce27e68d246c8808991b263078cbad
- MIBU PC Helper can query sleeper status from its assistant.
- With ADB available, the bridge presents the connected Android observation to Sleeper and reports the selected entry adapter, its qualification state, and matching knowledge count.
- Consumer context never grants mutation authority; Sleeper qualification and safety gates remain authoritative.
