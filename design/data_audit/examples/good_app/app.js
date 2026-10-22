// A made-up screen that shows only what it was given and says where that came from. It is the reference the audit's tests run against.
const KEY = "lamp-cache";
const WORDS = {
  loading: "Loading",
  live: "Live from the server",
  cached: "Saved copy, the server could not be reached",
  empty: "The server returned no requirements",
  error: "Could not load requirements, try again"
};

function show(state, rows, asof) {
  document.body.setAttribute("data-state", {live: "ready", cached: "ready", empty: "empty", error: "error", loading: "loading"}[state]);
  const mark = document.getElementById("mark");
  mark.setAttribute("data-source-state", state);
  if (asof) mark.setAttribute("data-as-of", asof); else mark.removeAttribute("data-as-of");
  document.getElementById("label").textContent = WORDS[state] + (state === "cached" && asof ? " (copy from " + asof.slice(0, 10) + ")" : "");
  document.getElementById("count").textContent = String(rows.length);
  document.getElementById("message").textContent = state === "empty" || state === "error" ? WORDS[state] + "." : "";
  const tbody = document.querySelector("#rows tbody");
  tbody.textContent = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    for (const v of [r.uid, r.text, r.owner, r.status]) {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function load() {
  show("loading", []);
  try {
    const r = await fetch("/api/requirements");
    if (!r.ok) throw new Error("status " + r.status);
    const rows = await r.json();
    if (rows.length) localStorage.setItem(KEY, JSON.stringify({at: new Date().toISOString(), rows}));
    show(rows.length ? "live" : "empty", rows, new Date().toISOString());
  } catch (e) {
    let kept = null;
    try { kept = JSON.parse(localStorage.getItem(KEY)); } catch (_) {}
    if (kept && kept.rows) show("cached", kept.rows, kept.at); else show("error", []);
  }
}
load();
