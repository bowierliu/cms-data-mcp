# Teach a cms-data-mcp concept

Treat the text following `/teacher` as Bowie's question. Preserve the current
engineering task and its checkpoint. Read `.cursor/agents/teacher.md` and the
relevant project file; delegate the question and those references to the teacher
subagent using the host's available task/delegation tool.

Pass only the question, relevant context, current phase, and file references.
Request an explanation, not changes. Return the teacher's answer in a direct,
project-grounded form. If no delegation tool is available, apply the teacher
instructions inline and clearly identify that fallback. Do not claim a subagent
was launched when it was not. If the question is absent, ask for the concept or
file to explain. Then resume any already-authorized engineering work.

Example: `/teacher why does a cache hit keep its original retrieval timestamp?`
