# Auto Skill Installer / AI 技能自动安装器

**Enable AI agents to autonomously discover and install missing skills at runtime.**

This is a **fork** of [lingbol088-spec/auto-skill-installer](https://github.com/lingbol088-spec/auto-skill-installer) with two key additions:

1. **MCP Server** — Exposes skill search/install as standard MCP tools so any MCP-compatible agent can call them
2. **Auto-Trigger Protocol** — Agents proactively detect capability gaps and install matching skills without user prompting

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    AI Agent                           │
│  (Proma, Codex, Claude Code, etc.)                    │
│                                                       │
│  Detects gap → calls MCP tools → skill installed ✓    │
└──────────────────────┬───────────────────────────────┘
                       │ MCP stdio
┌──────────────────────▼───────────────────────────────┐
│              MCP Server (mcp_server.py)                │
│                                                       │
│  search_skills │ ensure_skill │ list_installed        │
│  add_source    │ remove_source│ list_sources           │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│         Core Engine (skill_registry.py)               │
│                                                       │
│  Local scan → GitHub API → score → install → verify   │
└──────────────────────────────────────────────────────┘
```

---

## What It Does

- **Searches local skills** before hitting the network (avoids re-download)
- **Reads configured GitHub registries**, ranks matches by token scoring
- **Installs** only when the candidate directory contains `SKILL.md`
- **Supports multiple agent platforms**: Proma, Codex, and any MCP-compatible runtime
- **Auto-triggers** when the agent detects a capability gap at runtime

---

## MCP Server

The MCP server exposes 6 tools for AI agent consumption:

| Tool | Description |
|------|-------------|
| `search_skills(need, limit)` | Search local + remote for matching skills |
| `ensure_skill(need, force)` | Search and install the best match |
| `list_installed_skills()` | List all locally installed skills |
| `list_sources()` | List configured registries |
| `add_source(name, repo, path, ref)` | Add a custom registry |
| `remove_source(name)` | Remove a user-added source |

### Start the server

```bash
python scripts/mcp_server.py
```

All tools return structured JSON. No restart needed after installation.

---

## Auto-Trigger Protocol

The included `SKILL.md` instructs the agent to:

1. **Detect** — when a task needs capabilities outside installed skills
2. **Search** — call `search_skills()` with extracted capability terms
3. **Install** — call `ensure_skill()` when match confidence is high
4. **Continue** — use the new skill and inform the user

No explicit user invocation required — the agent acts proactively.

---

## Quick Start

### For Proma

1. **Install dependencies** (if not already present):

```bash
pip install fastmcp>=3.0.0
```

2. **Register the MCP server** — add to your Proma workspace `mcp.json`:

```json
{
  "servers": {
    "auto-skill-installer": {
      "command": "python",
      "args": ["path/to/skills/auto-skill-installer/scripts/mcp_server.py"],
      "description": "Search and install AI agent skills at runtime"
    }
  }
}
```

3. **Copy the skill** into your agent's skills directory:

```bash
cp -r skills/auto-skill-installer ~/.proma/agent-workspaces/default/skills/
```

4. Restart your agent. The MCP tools are now available.

### CLI (standalone)

```bash
python scripts/auto_install.py search --need "figma design generation"
python scripts/auto_install.py ensure --need "github pull request review" --force
python scripts/auto_install.py add-source --name my-team --repo your-org/agent-skills --path skills
```

---

## Platform Support

| Platform | Auto-detect | Default install path |
|----------|-------------|---------------------|
| **Proma** (auto) | `PROMASKILLS_HOME` env, or `~/.proma/agent-workspaces/*/skills` | Proma workspace skills dir |
| **Codex** | `CODEX_HOME` env, or `~/.codex/skills` | `$CODEX_HOME/skills` |
| **Custom** | Set `PROMASKILLS_HOME` or `CODEX_HOME` | As specified |

---

## Layout

```
auto-skill-installer/
├── README.md
├── LICENSE
├── requirements.txt                  # Python deps (fastmcp)
├── example-proma-mcp-config.json     # Example MCP config for Proma
└── skills/auto-skill-installer/
    ├── SKILL.md                      ← Auto-Trigger protocol
    ├── scripts/
    │   ├── auto_install.py           # CLI entry point
    │   ├── skill_registry.py         # Core engine
    │   └── mcp_server.py             # ★ NEW: MCP server
    ├── assets/
    │   └── registry-sources.json     # Default registries
    ├── agents/
    │   └── openai.yaml
    └── references/
        └── source-format.md
```

---

## Registry Sources

Pre-configured default: `openai/skills` curated set.

Add your own:

```bash
# CLI
python scripts/auto_install.py add-source --name my-org --repo your-org/agent-skills --path skills

# Or via MCP tool
mcp call add_source --arguments '{"name":"my-org","repo":"your-org/agent-skills","path":"skills"}'
```

---

## License

MIT
