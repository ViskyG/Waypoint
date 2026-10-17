# Waypoint — local integration start

## Task

Use this completed Pro design and supplied runnable reference to finish **one** Waypoint observer on the owner's local Linux/Codex environment, under MIXED. Do not start a second alternative architecture. Preserve existing projects and source work. The private-IPC feasibility was demonstrated in earlier real Codex probes; the newly authored adapter still needs target acceptance.

## Minimal reading order

1. `README_RU.md` (delivery state), `design/ARCHITECTURE.md` (governing design), `design/DECISIONS_AND_DOUBTS.md`.
2. `design/WORK_PACKETS.md` C05–C07: exact remaining scope. C01–C04 source artifacts already exist; do not regenerate them as new work.
3. Read only relevant sections of `design/CONTRACTS.md` and target criteria in `design/ACCEPTANCE.md` for the chosen packet. Use source evidence only to resolve a concrete mapping question.

The complete original owner context and latest evidence are preserved under `sources/`; they are fallback reading for meaning, not a compulsory repeated context load. Appearance references are preferences; the functional block contract wins over mockup labels. Do not invent a public license or publish this private source package without authorization.

## Start safely

Inspect the actual destination workspace before changing anything. In a fresh unpacked folder this package is the starting source; in an existing repository compare actual contents and preserve unrelated edits. Do not run global installers, reset Git history, overwrite shared configuration, change Codex hooks/auth, restart the owner's clients, or spawn benchmark agents.

```bash
python3 tools/verify_package.py
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python tools/verify_http.py
python -m waypoint --data "$HOME/.local/share/waypoint-demo" serve --demo
```

`preview.html` runs without dependencies for appearance/interaction review. It contains fictional data. For a real local browser service test, install the optional browser-test dependency only in the venv, use an existing compatible browser or an authorized browser installation, and run `tests/browser_check.py` against the disposable demo service. The previous container denied browser navigation to localhost; do not assume that restriction exists on the owner's machine, and do not bypass an administrator policy if it does.

## Native integration

Use `wp observe` only with an explicitly selected existing root thread, its actual same-user socket and rollout root. Inspect current extension/CLI versions; use `payload.id` for the actor, never common `session_id`. The original successful profile/code is in `sources/feasibility-evidence-v3.zip` under `experiments/live_observation/`. It is evidence, not a generic license to read all private chats or invoke arbitrary IPC methods.

Finish C05's verified caller-binding/watermark and incremental parser, C06's continuous read behavior, then C07's assembled target check. A strict read-only command allowlist remains mandatory. The observer may change its own subscription/store, but not the actual agent execution state. Recover from a mismatch by inspecting actual frames/field names locally; return only sanitized types/counts/equality checks, not secret message contents.

## Return format

Fill `reports/RETURN_TO_CHAT_RU.md` from the supplied template. Distinguish authored code, locally checked fixtures, observed live behavior, installed bindings and publication. Include versions, commands, assertions, exact remaining limitations and integration commit. Do not label this design package “already deployed”. Do not repeat the full P00–P11 hypothesis campaign; test this implementation and affected changes.

No extra model inference or test subagents just to fill evidence counts. If a truly decisive behavior cannot occur naturally, state the exact missing case and bound any required permission request rather than declaring failure of the mechanism.
