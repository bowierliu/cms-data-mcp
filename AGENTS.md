# Working in cms-data-mcp

Read `PROJECT_STATE.md`, `.cursor/rules/project.md`, and the relevant design
document before making changes. The main agent owns architecture and scope.
Use PROJECT_STATE.md for the current milestone and authorized next task. Do not
turn examples or future contracts into claimed features, or expand a bounded
source investigation into full implementation.

Domain skill entrypoints are `skills/<name>/SKILL.md`. Consult the relevant skill
for source discovery, source validation, healthcare modeling, tool design, data
validation, MCP testing, or provenance. Read the whole selected skill before use.

Specialist instructions are in `.cursor/agents/`. Use a specialist only for a
concrete task that benefits from its expertise or independent verification. Give
it bounded inputs, expected output, and permitted files. The parent integrates
results and resolves competing recommendations. Existing user authorization
continues to apply; do not insert redundant approval steps.

For `/teacher`, read `.cursor/commands/teacher.md` and route the question to
`.cursor/agents/teacher.md` through the available delegation tool. If the host
cannot load a custom role, supply that file's instructions to the subagent; if
delegation is unavailable, follow the teacher role inline and say so. Preserve
the active engineering task. Other commands are in `.cursor/commands/`.

Run the relevant verification commands documented in README.md. Report actual
results, failures, and untested scope. Do not run a live CMS test by default.
Never use the enclosing vault's data, credentials, Git remote, or unrelated files
as project inputs. Run Git operations only at this project's verified root.
