/* Pure view model and file contract first; the browser below only draws their output. */
"use strict";
(function () {
  const FORMAT = "reqin-review/1", PAGE_SIZE = 25;
  const OUTCOMES = ["agree", "disagree", "needs_review"];
  function itemsOf(data) {
    const by = new Map(data.requirements.map(r => [r.mid, r]));
    const members = mids => mids.map(mid => {
      if (!by.has(mid)) throw new Error("Comparison names a requirement outside this dataset.");
      return by.get(mid);
    });
    return data.clusters.map(c => ({ id: c.cid, kind: "EQUIVALENT", rule: c.rung, reasons: c.why || [], records: members(c.members.map(m => m.mid)) }))
      .concat(data.pairs.map(p => ({ id: p.pid, kind: p.type, rule: p.rule, reasons: p.why || [], records: members([...new Set(p.a.mids.concat(p.b.mids))]) })));
  }
  function exportDraft(data, binding, decisions) {
    return { format: FORMAT, status: "draft", binding, decisions,
      requirements: data.requirements, comparison: { summary: data.summary, clusters: data.clusters, pairs: data.pairs } };
  }
  function restore(file, data, binding) {
    if (!file || file.format !== FORMAT || file.status !== "draft" || file.binding !== binding) throw new Error("This review belongs to another comparison or is not a draft review file.");
    if (!file.decisions || typeof file.decisions !== "object" || Array.isArray(file.decisions)) throw new Error("The review notes are malformed.");
    const known = new Set(itemsOf(data).map(i => i.id)), clean = {};
    for (const [id, d] of Object.entries(file.decisions)) {
      if (!known.has(id) || !d || Object.keys(d).some(k => !["outcome", "reason"].includes(k)) || !OUTCOMES.includes(d.outcome) || typeof d.reason !== "string" || d.reason.length > 4000 || (d.outcome !== "needs_review" && !d.reason.trim())) throw new Error("A review note has an unknown comparison, outcome, or missing reason.");
      clean[id] = { outcome: d.outcome, reason: d.reason };
    }
    return clean;
  }
  function coverageOf(data) {
    return Object.entries(data.summary.limits || {}).map(([name, value]) => name.replaceAll("_", " ") + ": " + value).concat(data.summary.notes || []);
  }
  if (typeof module !== "undefined") module.exports = { itemsOf, exportDraft, restore, coverageOf };
  if (typeof document === "undefined") return;

  const script = document.currentScript, binding = script.dataset.binding;
  const $ = id => document.getElementById(id);
  const panel = $("review-panel"), status = $("review-status");
  let data, items = [], decisions = {}, page = 0, usable = true;
  function el(tag, text, cls) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function changedDataset() { usable = false; panel.hidden = true; }
  $("files").addEventListener("change", changedDataset);
  $("folder").addEventListener("change", changedDataset);
  function progress() {
    $("review-progress").textContent = Object.keys(decisions).length + " of " + items.length + " comparisons have review notes. All remain drafts.";
  }
  function render() {
    const kind = $("review-kind").value;
    const selected = items.filter(i => !kind || i.kind === kind);
    const host = $("review-items"); host.replaceChildren();
    for (const item of selected.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)) {
      const card = el("article", undefined, "review-item"); card.dataset.reviewId = item.id;
      card.append(el("h3", item.kind + " · " + item.id), el("p", "Rule: " + item.rule, "review-meta"));
      for (const r of item.records) card.append(el("p", r.uid + " · " + r.mid, "review-meta"), el("p", r.text, "review-wording"));
      for (const why of item.reasons) card.append(el("p", typeof why === "string" ? why : why.text || why.code || JSON.stringify(why), "review-meta"));
      const fields = el("div", undefined, "review-fields"), label = el("label", "Your assessment"), select = el("select");
      select.className = "rq-input";
      for (const [v, t] of [["", "Choose an assessment"], ["agree", "Agree with the mechanical classification"], ["disagree", "Disagree with the mechanical classification"], ["needs_review", "Needs further review"]]) { const o = el("option", t); o.value = v; select.append(o); }
      const reasonLabel = el("label", "Reason (required for agree or disagree)"), reason = el("textarea"); reason.className = "rq-input"; reason.maxLength = 4000;
      select.value = (decisions[item.id] || {}).outcome || ""; reason.value = (decisions[item.id] || {}).reason || "";
      const update = () => {
        if (!select.value) delete decisions[item.id];
        else decisions[item.id] = { outcome: select.value, reason: reason.value };
        reason.setCustomValidity(select.value && select.value !== "needs_review" && !reason.value.trim() ? "Give a reason for this assessment." : "");
        progress();
      };
      select.addEventListener("change", update); reason.addEventListener("input", update);
      label.append(select); reasonLabel.append(reason); fields.append(label, reasonLabel); card.append(fields); host.append(card);
    }
    if (!selected.length) host.append(el("p", "No comparisons in this category. Check the coverage limits above."));
    $("review-prev").disabled = page === 0;
    $("review-next").disabled = (page + 1) * PAGE_SIZE >= selected.length;
    progress();
  }
  $("review-kind").addEventListener("change", () => { page = 0; render(); });
  $("review-prev").addEventListener("click", () => { page--; render(); $("review-heading").scrollIntoView(); });
  $("review-next").addEventListener("click", () => { page++; render(); $("review-heading").scrollIntoView(); });
  $("review-save").addEventListener("click", () => {
    try {
      restore(exportDraft(data, binding, decisions), data, binding);
      const url = URL.createObjectURL(new Blob([JSON.stringify(exportDraft(data, binding, decisions), null, 2)], { type: "application/json" }));
      const a = el("a"); a.href = url; a.download = "requirements-draft-review.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      status.textContent = "Draft review downloaded. Original requirements are included with their internal IDs.";
    } catch (e) { status.textContent = e.message; }
  });
  $("review-load").addEventListener("change", async e => {
    try {
      const file = e.target.files[0]; if (!file) return;
      if (file.size > 20000000) throw new Error("Review file exceeds the size limit.");
      const next = restore(JSON.parse(await file.text()), data, binding);
      if (Object.keys(decisions).length && !window.confirm("Replace the review notes currently in this page? Download them first if needed.")) return;
      decisions = next; render(); status.textContent = "Draft review notes restored. Source text comes from the checked workspace.";
    } catch (e) { status.textContent = "Review refused: " + e.message; }
    e.target.value = "";
  });
  (async () => {
    try {
      const response = await fetch("review-input.json"); if (!response.ok) throw new Error("Comparison input is missing.");
      const raw = await response.arrayBuffer();
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", raw)), b => b.toString(16).padStart(2, "0")).join("");
      if (hash !== binding) throw new Error("Comparison input changed after validation; rebuild the workspace.");
      data = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
      if (data.format !== "reqin-review-input/1") throw new Error("Unknown review input format.");
      const qs = new URLSearchParams(location.search), chosen = qs.getAll("dataset");
      if (!usable) return;
      if (chosen.length && JSON.stringify(chosen) !== JSON.stringify(data.datasets)) return;
      if (!chosen.length) {
        data.datasets.forEach(d => qs.append("dataset", d));
        $("review-open").href = location.pathname + "?" + qs.toString();
        $("review-open").hidden = false;
        status.textContent = "Open the source datasets bound to this comparison, or choose another dataset above to inspect it.";
        panel.hidden = false; return;
      }
      for (let i = 0; i < data.datasets.length; i++) {
        const manifest = await fetch(data.datasets[i] + "/dataset.json");
        if (!manifest.ok) throw new Error("A source dataset is missing.");
        const bytes = await manifest.arrayBuffer();
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2, "0")).join("");
        if (digest !== data.summary.datasets[i].manifest_sha256) throw new Error("A source dataset no longer matches this comparison.");
      }
      await new Promise((resolve, reject) => {
        let observer, timer;
        const check = () => {
          const state = document.body.dataset.state;
          if (!["ready", "empty", "error"].includes(state)) return;
          if (observer) observer.disconnect(); clearTimeout(timer);
          if (state === "error") reject(new Error("The source dataset failed validation. Comparison review is disabled."));
          else resolve();
        };
        observer = new MutationObserver(check); observer.observe(document.body, { attributes: true, attributeFilter: ["data-state"] });
        timer = setTimeout(() => { observer.disconnect(); reject(new Error("Source validation did not finish. Reload after checking the dataset.")); }, 30000);
        check();
      });
      items = itemsOf(data); if (!usable) return;
      const counts = $("review-counts");
      for (const [name, value] of [["Requirements", data.requirements.length], ["Equivalent clusters", data.clusters.length], ["Other pairs", data.pairs.length]]) { const div = el("div"); div.append(el("dt", name), el("dd", String(value))); counts.append(div); }
      const limits = coverageOf(data); for (const line of limits.length ? limits : ["No candidate-search omissions were reported."]) $("review-limits").append(el("li", line));
      const all = el("option", "All comparisons"); all.value = ""; $("review-kind").append(all);
      for (const kind of [...new Set(items.map(i => i.kind))].sort()) { const o = el("option", kind); o.value = kind; $("review-kind").append(o); }
      status.textContent = "Checked mechanical output. No AI model was called."; panel.hidden = false; $("review-work").hidden = false; render();
    } catch (e) { status.textContent = "Comparison refused: " + e.message; panel.hidden = false; $("review-save").disabled = true; $("review-load").disabled = true; }
  })();
})();
