# THETECHGUY Build Standard

This standard applies across THETECHGUY projects, including MIBU, Hunter, Builder, Tool, and related utilities.

## 1. Finish, then prove

- Complete the intended implementation first.
- Review it thoroughly.
- Freeze it.
- Then perform clean-clone and runtime proof.

The project should not move into runtime testing while the core implementation is still incomplete or knowingly inconsistent with the intended design.

## 2. Code should justify execution

- Do not run code hoping to discover whether it works.
- Run it expecting success because the reasoning, review, and implementation already support that conclusion.
- If it fails, that should be surprising.

Runtime should validate a well-reasoned implementation, not compensate for unfinished thinking.

## 3. Claims must match implementation

- Reviewer must compare documentation, submission claims, and UI promises against the actual code.
- If documentation says one thing and the implementation does another, that is a review finding before runtime testing.
- Example: if docs claim AI reasoning but the code is simple regex matching, the claim is wrong even if the app runs.

No release, demo, or proof statement may claim functionality that is not present in the code.

## 4. Evidence before conclusions

- Verify using live sources such as the current Git tree, raw files, built artifacts, logs, and actual runtime output.
- Do not rely on cached summaries or assumptions when source files are available.
- If sources conflict, report the conflict instead of choosing one blindly.

A review must be able to point to the exact evidence behind its conclusion.

## 5. Tests are proof, not discovery

- Runtime tests should confirm the engineering work.
- Most issues found after this stage should be polish, edge cases, or UX improvements.
- Runtime should not reveal fundamental design surprises that could have been caught by reading the code and comparing it against the plan.

Testing is the proof stage, not the design stage.

## 6. Reviewer responsibility

Before a claim is accepted as done, the reviewer must check:

- Does the implementation match the stated plan?
- Does the UI match the expected user flow?
- Are buttons wired to real actions, not static images only?
- Do docs and code agree?
- Are resources bundled safely?
- Are failure states honest?
- Is there evidence for every completion claim?

## 7. Release gate

A THETECHGUY build is not done until:

1. Intended implementation is complete.
2. Code review confirms claims match implementation.
3. Known gaps are documented honestly.
4. Clean build succeeds.
5. Runtime proof confirms the reviewed implementation.
6. Final notes say exactly what was proven and what remains unproven.

## Core rule

Finish first. Review hard. Freeze. Then prove.
