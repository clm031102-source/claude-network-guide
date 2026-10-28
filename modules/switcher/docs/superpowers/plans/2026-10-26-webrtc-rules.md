# WebRTC runtime rules repair

Approved design: default `proxy` policy, optional `reject` policy. Scope is the macOS Clash Verge integration; other clients retain their existing configuration ownership.

## Constraints

- Keep the installed core self-contained, using Python standard library only.
- Preserve existing global JavaScript and unrelated Merge.yaml contents. Back up changes; fail on ambiguous managed markers.
- Validate the configured proxy group instead of assuming `IpEqual` exists.
- Read only the local Mihomo API, supporting loopback TCP and its configured Unix socket. Never log its secret.
- Confirm rule mode, enabled rules at the beginning of `/rules`, and the selected proxy's UDP support before reporting proxy policy as ready.
- `WEBRTC_POLICY=proxy|reject` on `fix` selects and persists the policy. Invalid values stop before writes.
- No probe response is unknown, not proof of zero exposure. Explicit verified rejection can explain an expected lack of STUN responses.
- Do not deploy to the maintainer's installed application or access real account data.

## Task 1: Reproduce and repair rule installation

- [x] Add isolated tests reproducing text-only `stun_ok` success while runtime rules are absent.
- [x] Add an extracted embedded-Python harness with a fake loopback Mihomo API and Node evaluation of generated global scripts.
- [x] Verify the new expectations fail against the current core.
- [x] Implement a self-contained `clash_rules` helper for policy, script generation and runtime verification.
- [x] Compose with the existing global `main`, prepend UDP-only rules and the existing ecosystem domain rules, and migrate only old managed blocks.
- [x] Cover both policies, invalid policy/group, repeated writes, existing scripts, quoted group names, incorrect/missing/disabled rules, API failures and UDP support.

## Task 2: Integrate audit and repair reporting

- [x] Use runtime verification in `merge_ok` / `stun_ok`, remove the fake-IP fallback for Clash runtime-rule validation.
- [x] Share WebRTC assessment between `check`, `checkdetail` and `fix`; invalid, empty and nonzero probe output cannot pass.
- [x] Require successful rule writing and runtime verification after reload before showing repair success.
- [x] Update installer messages, README and AGENTS guidance for the supported script entry point and persisted policy.
- [x] Run isolated regression tests, shell/Python syntax checks and `git diff --check`.
- [x] Run `scripts/gen-sums.sh`, validate all eight manifest entries, and review changes before committing and pushing.

Verification: 29 isolated regressions passed. Review findings on early policy validation and exact domain matching were reproduced, fixed and reviewed again. On Windows, the checksum script used a `shasum -a 256` compatibility function backed by Git Bash `sha256sum --text`; all eight LF artifact hashes matched, with only the core and installer hashes changed.

The Windows host cannot independently verify a real macOS GUI/Clash restart. This limitation must be stated in the delivery.
