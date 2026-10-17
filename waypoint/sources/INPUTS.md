# Evidence used

The three native Docs were read on 2026-10-16. Full text snapshots of Design Context and Findings were materialized; the two owner-selected appearance images are included separately. Their original historical layers are retained, not duplicated as requirements. Latest owner decisions take precedence; old “live access unproven” statements are superseded by rev3.

- Design Context: https://docs.google.com/document/d/19xpj5t9d92nqir3x2FmqWmyK5_eT0G9MNjsb7dShcgs/edit
- Findings: https://docs.google.com/document/d/1avN7nfm1jrHhg0RRKGc0lDRhhn8EE3D0hkHCdt6Kq0A/edit
- Appearance: https://docs.google.com/document/d/1n1qCof7PmsDV_ehdvi1DfV8FajglTpc8N2OvvWYXmtg/edit
- Latest source archive: WAYPOINT_EVIDENCE_SANITIZED(2).zip; SHA256 51fa3627053ea6c9e5e75046401274d08d0d069a806620ad75d57d1028960698. Archive CRC verified and live_observation source read in this pass. No experiment against the owner's live machine was performed here.

Targeted external source verification (not a new research campaign):
- https://developers.openai.com/codex/app-server/ (redirects to https://learn.chatgpt.com/docs/app-server): official read API, NOT a guarantee of private VS Code IPC stability.
- https://sqlite.org/wal.html : local write-ahead log behavior and single-writer constraints.
- https://docs.python.org/3/library/sqlite3.html : transactions and connection behavior.
- https://fastapi.tiangolo.com/advanced/events/ : app lifespan setup/cleanup.
- https://reactflow.dev/examples/interaction/contextual-zoom : analogous semantic-zoom technique, not a mandatory dependency.
- https://datatracker.ietf.org/doc/html/rfc6902 : JSON Patch semantics. The VS Code private patch uses path ARRAYS, so it is not blindly treated as a standards-compliant JSON Pointer wire format.
