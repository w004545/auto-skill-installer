#!/usr/bin/env python3
"""MCP server for auto-skill-installer.

Exposes skill search, install, and management as MCP tools so that AI agents
can autonomously discover and install missing capabilities at runtime.

Usage:
    python mcp_server.py

Register in Proma's mcp.json:
    "auto-skill-installer": {
      "command": "python",
      "args": ["path/to/mcp_server.py"],
      "description": "Search and install AI agent skills at runtime"
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure sibling imports work when run as script or via MCP stdio
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from fastmcp import FastMCP

from skill_registry import (
    RegistryError,
    SourceSpec,
    install_candidate,
    load_sources,
    local_candidates,
    save_user_sources,
    search,
    skills_root,
)

# ── MCP Server ──────────────────────────────────────────────────────────

mcp = FastMCP("auto-skill-installer")


# ── Tools ───────────────────────────────────────────────────────────────


@mcp.tool(
    name="search_skills",
    description=(
        "Search for agent skills matching a capability need. "
        "Searches BOTH locally installed skills AND remote GitHub registries. "
        "Returns ranked candidates with scores, descriptions, and install status."
    ),
)
def search_skills_tool(need: str, limit: int = 8) -> str:
    """Search for matching skills by capability description."""
    candidates, warnings = search(need, limit=limit)
    return json.dumps(
        {
            "need": need,
            "warnings": warnings,
            "found": len(candidates) > 0,
            "candidates": [c.to_dict() for c in candidates],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool(
    name="ensure_skill",
    description=(
        "Ensure a skill matching the given need is installed. "
        "Searches all sources (local + remote) and installs the best matching "
        "skill if not already present. Use force=True when you are confident "
        "the top match is correct despite multiple close candidates."
    ),
)
def ensure_skill_tool(need: str, force: bool = False) -> str:
    """Search and install the best matching skill."""
    candidates, warnings = search(need, limit=5)
    if not candidates:
        return json.dumps(
            {
                "success": False,
                "need": need,
                "warnings": warnings,
                "error": "No matching skills found in any source.",
            },
            indent=2,
            ensure_ascii=False,
        )

    best = candidates[0]
    runner_up_gap = best.score - candidates[1].score if len(candidates) > 1 else best.score
    close = not force and len(candidates) > 1 and runner_up_gap < 4

    if close:
        return json.dumps(
            {
                "success": False,
                "need": need,
                "close_matches": True,
                "message": "Multiple close matches — use ensure_skill with force=True or narrow the need.",
                "candidates": [c.to_dict() for c in candidates[:3]],
            },
            indent=2,
            ensure_ascii=False,
        )

    if best.installed:
        return json.dumps(
            {
                "success": True,
                "need": need,
                "installed": True,
                "message": f"Already installed: {best.name}",
                "candidate": best.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )

    try:
        dest = install_candidate(best)
        return json.dumps(
            {
                "success": True,
                "need": need,
                "installed": False,
                "message": f"Installed {best.name} -> {dest}",
                "destination": str(dest),
                "candidate": best.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )
    except RegistryError as exc:
        return json.dumps(
            {
                "success": False,
                "need": need,
                "error": str(exc),
                "candidate": best.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool(
    name="list_installed_skills",
    description="List all agent skills currently installed in local skills directories.",
)
def list_installed_skills_tool() -> str:
    """List all locally installed skills."""
    candidates = local_candidates()
    return json.dumps(
        {
            "count": len(candidates),
            "skills_root": str(skills_root()),
            "skills": [
                c.to_dict()
                for c in sorted(candidates, key=lambda x: x.name.lower())
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool(
    name="list_sources",
    description="List all configured skill registry sources (built-in + user-added).",
)
def list_sources_tool() -> str:
    """List all configured registry sources."""
    sources = load_sources()
    return json.dumps(
        {
            "count": len(sources),
            "sources": [
                {
                    "name": s.name,
                    "repo": s.repo,
                    "path": s.path,
                    "ref": s.ref,
                    "tags": list(s.tags),
                }
                for s in sources
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool(
    name="add_source",
    description="Add a custom GitHub skill registry source for future searches and installations.",
)
def add_source_tool(name: str, repo: str, path: str, ref: str = "main") -> str:
    """Add a custom skill registry source."""
    sources = load_sources()
    custom = [s for s in sources if not s.name.startswith("openai-")]
    custom.append(
        SourceSpec(name=name, repo=repo, path=path.strip("/"), ref=ref)
    )
    saved_path = save_user_sources(custom)
    return json.dumps(
        {
            "success": True,
            "message": f"Added source '{name}' ({repo}/{path}#{ref})",
            "saved_to": str(saved_path),
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.tool(
    name="remove_source",
    description="Remove a user-added skill registry source by name. Built-in sources cannot be removed.",
)
def remove_source_tool(name: str) -> str:
    """Remove a user-added source by name."""
    sources = load_sources()
    remaining = [s for s in sources if s.name != name]
    if len(remaining) == len(sources):
        return json.dumps(
            {
                "success": False,
                "error": f"Source '{name}' not found.",
                "available": [s.name for s in sources],
            },
            indent=2,
            ensure_ascii=False,
        )

    built_in = [s for s in sources if s.name.startswith("openai-")]
    custom = [s for s in remaining if not s.name.startswith("openai-")]
    save_user_sources(built_in + custom)
    return json.dumps(
        {
            "success": True,
            "message": f"Removed source '{name}'.",
        },
        indent=2,
        ensure_ascii=False,
    )


# ── Entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
