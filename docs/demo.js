"use strict";

(async () => {
  // The public replay never probes localhost. Only this companion's own origin accepts runs.
  if (window.location.protocol !== "http:" || window.location.hostname !== "127.0.0.1") return;
  try {
    const health = await fetch("/api/status", {cache: "no-store"});
    if (!health.ok || (await health.json()).service !== "cms-data-mcp-companion") return;
  } catch {
    return;
  }
  const el = id => document.getElementById(id);
  el("setup").hidden = true;
  el("controls").hidden = false;
  const request = (route, value) => fetch(route, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(value), cache: "no-store"
  });
  el("run").addEventListener("click", async () => {
    el("run").disabled = el("stop").disabled = true;
    el("status").textContent = "Running the model and MCP tools…";
    el("result").hidden = true;
    try {
      const response = await request("/api/investigate", {scenario: el("question").value});
      const data = await response.json();
      if (!response.ok) {
        el("status").textContent = data.error || "The investigation stopped.";
        return;
      }
      el("explanation").textContent = data.explanation;
      el("tool-path").textContent = data.evidence.tools.join(" → ");
      el("detail").textContent = JSON.stringify(data.evidence, null, 2);
      el("status").textContent = "Investigation complete. Review the evidence below.";
      el("result").hidden = false;
    } catch {
      el("status").textContent = "Connection interrupted. Check the budget ledger before running again.";
    } finally {
      el("run").disabled = el("stop").disabled = false;
    }
  });
  el("stop").addEventListener("click", async () => {
    el("run").disabled = el("stop").disabled = true;
    try {
      const response = await request("/api/stop", {});
      if (!response.ok) throw new Error();
      el("status").textContent = "Local server stopped. Use the launcher to open it again.";
    } catch {
      el("status").textContent = "The local server could not be reached.";
    }
  });
})();
