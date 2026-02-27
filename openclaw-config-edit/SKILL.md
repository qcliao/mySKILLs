---
name: openclaw-config-edit
description: Safe editing of openclaw.json configuration. Activate when asked to modify openclaw settings, add/change tools config, set allowFrom, update elevated permissions, or any change to openclaw.json. Prevents config corruption by enforcing backup-validate-edit workflow.
---

# openclaw-config-edit

Safe SOP for modifying `~/.openclaw/openclaw.json` without breaking the gateway.

## Workflow

### 1. Backup first (always)
```bash
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d_%H%M%S)
```

### 2. Check docs before editing

Read the relevant doc under `/usr/lib/node_modules/openclaw/docs/tools/` before touching any field. Never assume a field type — always verify.

### 3. Edit the config

Use `edit` (surgical) or `read` + `write` for larger changes. Never guess field types.

### 4. Validate after editing
```bash
openclaw doctor
```

> ⚠️ `openclaw doctor --fix` cannot repair type errors (e.g., boolean where array is expected). If validation fails, fix manually.

### 5. Log the change

Write what changed and why to `memory/YYYY-MM-DD.md`.

---

## Common Type Mistakes

See `references/field-types.md` for the canonical type reference.

Key rule: **`tools.elevated.allowFrom.<provider>` must be a string array, never a boolean.**

```json
// ❌ Wrong
"allowFrom": { "feishu": true }

// ✅ Correct
"allowFrom": { "feishu": ["user:ou_xxx"] }
```
