# openclaw.json Field Type Reference

Source: `/usr/lib/node_modules/openclaw/docs/tools/`

## tools.elevated

| Field | Type | Example |
|-------|------|---------|
| `tools.elevated.enabled` | boolean | `true` |
| `tools.elevated.allowFrom` | object | `{ "feishu": [...] }` |
| `tools.elevated.allowFrom.<provider>` | string[] | `["user:ou_xxx"]` |

### allowFrom entry formats
- `"user:ou_xxx"` — match by open_id (Feishu)
- `"username:xxx"` — match by username
- `"name:xxx"` — match by display name
- `"id:xxx"` / `"from:xxx"` / `"e164:xxx"` — explicit identity targeting
- Bare string — matches sender-scoped identity values only

Supported providers: `feishu`, `discord`, `whatsapp`, `telegram`, `signal`, `slack`, etc.

Discord fallback: if `tools.elevated.allowFrom.discord` is omitted, falls back to `channels.discord.allowFrom`.

## tools.exec

| Field | Type | Example |
|-------|------|---------|
| `tools.exec.host` | string enum | `"sandbox"` \| `"gateway"` \| `"node"` |
| `tools.exec.security` | string enum | `"deny"` \| `"allowlist"` \| `"full"` |
| `tools.exec.ask` | string enum | `"off"` \| `"on-miss"` \| `"always"` |
| `tools.exec.notifyOnExit` | boolean | `true` |
| `tools.exec.pathPrepend` | string[] | `["~/bin"]` |
| `tools.exec.safeBins` | string[] | `["jq", "grep"]` |
| `tools.exec.node` | string | `"my-node-id"` |

## tools.deny / tools.allow

| Field | Type | Example |
|-------|------|---------|
| `tools.deny` | string[] | `["exec", "browser"]` |
| `tools.allow` | string[] | `["exec"]` |

## Doctor & Validation

```bash
openclaw doctor          # check config validity
openclaw doctor --fix    # attempt auto-fix (cannot fix type errors)
openclaw config get <key>   # read a specific key
openclaw config set <key> <value>   # set a specific key
```
