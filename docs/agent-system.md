# cms-data-mcp agent system

The main agent owns requirements, decisions, integration, and project state.
Specialists receive a bounded task, relevant paths, expected output, and allowed
side effects. They return evidence and recommendations; they do not independently
redesign the project. Use independent review/verification for meaningful changes,
not a seven-agent ceremony for every edit.

| Role | Responsibility | Default write scope |
| --- | --- | --- |
| architect | Boundaries, interfaces, dependency tradeoffs | Read-only recommendations |
| explore | Repository and authoritative source research | Read-only |
| data-engineer | Ingestion, normalization, cache, analytics, quality | Assigned implementation files |
| mcp-engineer | SDK, tool schemas, errors, context efficiency | Assigned implementation files |
| reviewer | Prioritized independent critique | Read-only |
| verifier | Actual checks and completion evidence | Temporary test/build artifacts |
| teacher | Project-grounded explanation for Bowie | Read-only |

Definitions use `model: inherit`. The user's preferred main-model label is
`GPT SOL 6.1`; no unverified provider model identifier is hard-coded. Select the
intended available model in the host; these files do not change account settings.

## Commands, rules, and skills

Commands in `.cursor/commands/` define `/teacher`, `/plan`, `/review`, `/verify`,
and `/checkpoint`. A teacher request routes to the teacher subagent if supported,
passing the question and relevant files; otherwise the main agent follows that
role inline and says so. It returns to the active engineering task afterward.

Rules are always-applicable project constraints. The requested `project.md` is
the canonical text; `project.mdc` is the actual Cursor loader referencing it.
`AGENTS.md` routes other hosts to the same rules and state.

Skills are optional, focused domain guidance chosen for the task. Their canonical
content is under `skills/`. Native `.cursor/skills/<name>/SKILL.md` adapters have
descriptions and direct paths to that content so Cursor can discover them without
duplicating domain instructions or depending on symlink traversal. Five additional
explicit-only adapters route the requested slash commands on current Cursor.

Cursor's current documentation lists `.cursor/agents/` definitions, `.mdc` rules,
and `.cursor/skills/` or `.agents/skills/` discovery. Its command documentation
routes toward explicit-only skills. These adapters preserve the requested paths
while supplying the current discovery format. Reviewed 2026-10-01:
[subagents](https://cursor.com/docs/subagents),
[rules](https://cursor.com/docs/rules),
[skills](https://cursor.com/docs/skills), and
[command migration](https://cursor.com/help/customization/skills).

## Editor verification

Open the inner `cms-data-mcp` folder. In Cursor, inspect the project skills and
rules, then enter `/teacher why is provenance part of retrieval?`. Verify that
the response distinguishes the planned design from implemented code and that
project files remain unchanged. A command menu may contain built-in names such
as `/review`; select the project item or refer to its file explicitly if needed.

This scaffold's automated checks verify paths and frontmatter, not a live editor
session. Role instructions are a behavioral boundary; use host permissions as
the enforcement boundary. Other hosts can read AGENTS.md and load the canonical
role/skill files, but no native cross-host command installation is claimed.
