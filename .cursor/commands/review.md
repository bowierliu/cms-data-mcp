# Review cms-data-mcp work

Resolve the requested diff or files inside this project. Delegate to the reviewer
defined in `.cursor/agents/reviewer.md` when available, passing the task contract
and exact review scope. If delegation is unavailable, follow that role inline
and report the fallback. Review does not authorize edits.

Return findings as BLOCKER, IMPORTANT, IMPROVEMENT, or OPTIONAL, with location,
trigger, impact, and evidence. Report unverified areas. If there is no diff,
review the named files; never silently review the enclosing vault repository.
