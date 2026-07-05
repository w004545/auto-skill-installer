---
name: auto-skill-installer
description: Runtime capability self-discovery. When the AI agent detects a task that falls outside its installed skill set, it autonomously searches local + GitHub registries and installs the best-matching skill on the fly. Does NOT require user to trigger manually — agent acts proactively.
---

# Auto Skill Installer

This skill enables the AI agent to **autonomously expand its own capabilities at runtime** by detecting skill gaps and installing matching skills via MCP tools.

> **You do NOT need the user to invoke this skill manually.** If you detect a capability gap, act proactively.

---

## Auto-Discovery Protocol

When you (the AI agent) receive a user request, silently evaluate:

### 1. Trigger Conditions — suspect a gap when

- The user asks about a platform, tool, or domain you recognize as broad but have no specific skill for (e.g., "analyze this Figma file" → you lack a Figma skill)
- The user says "is there a skill that can..." or "find me a tool for..."
- A task would be significantly safer, faster, or more accurate with a specialized skill
- A prior attempt at a task produced a shallow or generic result that a skill would improve
- The user mentions a service, API, or workflow you've never been trained on

### 2. Evaluate — what's installed?

```python
# Call the MCP tool:
list_installed_skills()
# If nothing matches the task domain → proceed to search
```

If you find an already-installed skill that matches, **use it directly** and skip installation.

### 3. Search — formulate capability terms

Extract 2-3 concise capability phrases from the user's request:

| User says | Search terms |
|-----------|-------------|
| "help me analyze this Figma design" | `figma design analysis`, `figma plugin` |
| "write a PR review" | `github pull request review`, `code review` |
| "research this topic deeply" | `deep research`, `web research` |
| "create an infographic" | `infographic`, `data visualization card` |

```python
# Call the MCP tool:
search_skills(need="<capability phrase>", limit=5)
```

### 4. Install — when confident

If the top result:
- Has **score ≥ 15** → strong match, install automatically
- Has **score ≥ 10** AND is clearly better than alternatives → install
- Is close to multiple alternatives → report to user with candidates

```python
# Call the MCP tool:
ensure_skill(need="<capability phrase>", force=False)
# Use force=True when one candidate is clearly dominant
```

### 5. Verify & continue

After installation:
- Check that the skill directory exists
- **Mention to the user** what was installed and why ("I noticed this task needs X, so I auto-installed the Y skill")
- Proceed with the task using the newly installed skill

---

## Command Reference (MCP Tools)

These tools are available automatically when the MCP server is running:

| Tool | When to use |
|------|-------------|
| `search_skills(need, limit)` | Search for skills matching a capability gap |
| `ensure_skill(need, force)` | Search + install the best match in one step |
| `list_installed_skills()` | Check what's already available |
| `list_sources()` | See configured registries |
| `add_source(name, repo, path, ref)` | Add a custom GitHub skill source |
| `remove_source(name)` | Remove a user-added source |

## Search Strategy

- **Start concrete**: prefer `github review comments` over `github`
- **If first search is noisy**, try 2-3 sharper keywords
- **Prefer skills** whose `description` explicitly matches the task
- **If several candidates are close**, the top-ranked one by score is usually correct
- **If the top match is already installed**, it means you already have the capability — use it

## Decision Rules

- Install automatically when one candidate is clearly better (score gap ≥ 4)
- Report to user when multiple candidates are close and tradeoffs differ
- Treat user-configured sources as higher priority than broad registries
- After installation, the new skill is available immediately (no restart needed in Proma)

## Safety

- The installer only copies directories that contain `SKILL.md`
- It will not overwrite an existing skill directory
- Network failures for one source don't block other sources
- Archive extraction is sandboxed against path traversal
