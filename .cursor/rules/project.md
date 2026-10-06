# cms-data-mcp project rules

- Use `cms-data-mcp` for the project, root, distribution, documentation, and future
  GitHub repository. `cms_mcp` is the Python import name only.
- Read PROJECT_STATE.md before work. The main agent owns scope and architecture;
  specialists return bounded work and evidence. Do not invoke every specialist
  for a trivial change. Keep work within the current user request and milestone
  recorded in PROJECT_STATE.md.
- Use only public documentation, synthetic data, and permitted public data.
  Exclude PHI, PII, employer/proprietary data, and secrets everywhere, including
  caches, logs, fixtures, and exports. Public clinician identifiers and names are
  not exempt from the no-PII requirement. Do not download their raw records.
- Facts come from authoritative sources and deterministic code. Record evidence
  and uncertainty; never infer a release, field meaning, or county from a title,
  a search snippet, a city label, or an unverified ZIP mapping.
- Preserve row grain, string identifiers, coverage dates, source version,
  original retrieval time, transformations, validation outcomes, and scope.
  Partial extracts stay partial. A local hash is not publisher verification.
- Keep typed interfaces, explicit errors, bounded I/O, structured logging to
  stderr, and reproducible tests. Do not expose arbitrary SQL, Python, shell,
  network URLs, or output paths through MCP. Validate redirected sources too.
- Prefer one tested workflow and modules with real responsibility. Add packages,
  dependencies, and infrastructure only when the current task needs them.
- Read the relevant canonical skill in `skills/` before domain work. The thin
  `.cursor/skills/` adapters route to those documents; they are not extra policy.
- `/teacher` routes to the teacher role and preserves the active task. Teaching
  does not modify production code or architecture.
- Run relevant checks and report evidence. Setup checks are not product tests;
  planned examples are not demos. Update state and affected docs with the work.
- Do not modify unrelated files or inherit the enclosing vault's remote. Confirm
  this project's Git root before repository operations. Never commit credentials.
- Existing user authorization takes precedence over workflow preferences. Do
  not add redundant approval gates. Publication and messaging require their
  own authorization.
