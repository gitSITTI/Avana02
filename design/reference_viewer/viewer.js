/* Reference viewer for one or more canonical datasets (contract reqin-dataset, version 1). See ../../reqin/GUI_CONTRACT.md.
 *
 * Rules this file keeps, and that tools/gui_checks/hardcode_scan.py checks in any app:
 *   - It reads only what the user gives it: dataset files from a file input, or from ?dataset=FOLDER. No sample data, no server, no storage.
 *   - Every value from a dataset reaches the page through textContent. There is no innerHTML, so markup inside a requirement is shown as text.
 *   - A dataset that fails its own checks (missing file, changed checksum, wrong counts, malformed record) is refused whole. Nothing is shown from it.
 *   - Counts, chips, columns and panels come from the data. A field no record has gets no column. A source with no links gets no trace panel.
 *   - The list is windowed: only the rows in view are in the page, so 50,000 records stay responsive.
 * The data-testid values are the contract with the probe: docs/GUI_TEST_HOOKS.md.
 */
"use strict";
(function () {
  var FILES = { requirements: "requirements.jsonl", links: "links.jsonl", rejected: "rejected.jsonl", report: "report.json", manifest: "dataset.json" };
  var STANDARD = ["status", "verification", "owner", "allocation", "baseline", "rationale"];
  var LABELS = { status: "Status", verification: "Verification", owner: "Owner", allocation: "Allocation", baseline: "Baseline", rationale: "Rationale" };
  var MAX_COLUMNS = 2, OVERSCAN = 6, LIST_CAP = 200;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text, testid) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    if (testid) e.setAttribute("data-testid", testid);
    return e;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function show(node, on) { node.hidden = !on; }
  function plain(v) { return typeof v === "string" ? v : JSON.stringify(v); }

  var S = null;           // the loaded workspace; null until a dataset has been accepted
  var rowH = 96;          // measured, not assumed: it follows the stylesheet at every width
  var verified = {};      // "marked verified" lives in this page only; a reload clears it

  /* ---------------------------------------------------------------- reading */
  async function sha256(buf) {
    if (!(window.crypto && window.crypto.subtle)) return null;
    var d = await window.crypto.subtle.digest("SHA-256", buf);
    return Array.prototype.map.call(new Uint8Array(d), function (b) { return b.toString(16).padStart(2, "0"); }).join("");
  }
  function decode(buf) { return new TextDecoder("utf-8", { fatal: true }).decode(buf); }

  async function readGroup(group, notices) {
    var problems = [], out = { label: group.label, requirements: [], links: [], rejected: [], report: null, manifest: null };
    var bytes = {};
    var names = Object.keys(FILES);
    for (var i = 0; i < names.length; i++) {
      var key = names[i];
      try { bytes[key] = await group.get(FILES[key]); } catch (e) { bytes[key] = null; }
      if (!bytes[key]) problems.push(FILES[key] + " is missing" + (key === "manifest" ? ": the folder is not a dataset, or it was cut short before it finished" : ""));
    }
    if (bytes.manifest) {
      try {
        out.manifest = JSON.parse(decode(bytes.manifest));
        if (!out.manifest || out.manifest.contract !== "reqin-dataset") problems.push("dataset.json is not a reqin-dataset manifest");
        else if (out.manifest.version !== 1) problems.push("dataset.json is contract version " + out.manifest.version + " and this viewer reads version 1");
      } catch (e) { problems.push("dataset.json is not valid JSON"); out.manifest = null; }
    }
    ["requirements", "links", "rejected"].forEach(function (k) {
      if (!bytes[k]) return;
      try {
        var text = decode(bytes[k]), lines = text.split("\n");
        for (var n = 0; n < lines.length; n++) {
          if (!lines[n].trim()) continue;
          try { out[k].push(JSON.parse(lines[n])); } catch (e) { problems.push(FILES[k] + " line " + (n + 1) + " is not valid JSON"); break; }
        }
      } catch (e) { problems.push(FILES[k] + " is not valid UTF-8 text"); }
    });
    if (bytes.report) {
      try { out.report = JSON.parse(decode(bytes.report)); } catch (e) { problems.push("report.json is not valid JSON"); }
    }
    var man = out.manifest;
    if (man && man.files && typeof man.files === "object") {
      var skipped = false, byFile = {};
      Object.keys(FILES).forEach(function (k) { byFile[FILES[k]] = k; });
      for (var f in man.files) {
        var key2 = byFile[f];
        if (!key2 || !bytes[key2]) continue;
        var got = await sha256(bytes[key2]);
        if (got === null) { skipped = true; continue; }
        if (!man.files[f] || got !== man.files[f].sha256) problems.push(f + " changed or was cut short after it was written: its checksum no longer matches dataset.json");
      }
      if (skipped) notices.push(group.label + ": checksums were not checked, because this page was not opened from a secure address (https, localhost or a local file). Counts and structure were checked.");
    }
    if (man && man.counts) {
      ["requirements", "links", "rejected"].forEach(function (k) {
        if (man.counts[k] !== out[k].length) problems.push("dataset.json says " + man.counts[k] + " " + k + " but " + FILES[k] + " has " + out[k].length);
      });
    }
    var bad = 0;
    out.requirements.forEach(function (r, i) {
      var ok = r && typeof r.mid === "string" && typeof r.uid === "string" && typeof r.text === "string" && r.fields && typeof r.fields === "object" &&
        r.extra && typeof r.extra === "object" && r.ref && typeof r.ref === "object" && r.conf && typeof r.conf === "object" && typeof r.fidelity === "string";
      if (!ok && bad++ < 3) problems.push("requirements.jsonl record " + (i + 1) + " is missing a required part (mid, uid, text, fields, extra, ref, conf or fidelity)");
    });
    out.links.forEach(function (l, i) {
      if (!(l && typeof l.kind === "string") && bad++ < 6) problems.push("links.jsonl record " + (i + 1) + " has no kind");
    });
    if (out.report && typeof out.report !== "object") problems.push("report.json is not an object");
    return { data: out, problems: problems };
  }

  function groupsFromFiles(fileList) {
    var byDir = {};
    Array.prototype.forEach.call(fileList, function (f) {
      var rel = f.webkitRelativePath || f.name, i = rel.lastIndexOf("/"), dir = i < 0 ? "" : rel.slice(0, i), base = i < 0 ? rel : rel.slice(i + 1);
      if (Object.keys(FILES).some(function (k) { return FILES[k] === base; })) { (byDir[dir] = byDir[dir] || {})[base] = f; }
    });
    return Object.keys(byDir).sort().map(function (dir) {
      return { label: dir || "the chosen files", get: async function (name) { var f = byDir[dir][name]; return f ? await f.arrayBuffer() : null; } };
    });
  }
  function groupsFromUrls(bases) {
    return bases.map(function (base) {
      var b = base.replace(/\/+$/, "");
      return { label: b, get: async function (name) { var r = await fetch(b + "/" + name); return r.ok ? await r.arrayBuffer() : null; } };
    });
  }

  /* ---------------------------------------------------------------- loading */
  async function load(groups) {
    document.body.setAttribute("data-state", "loading");
    show($("loading"), true); show($("ready"), false); show($("error"), false);
    S = null; verified = {};
    $("loading").textContent = "Reading the dataset\u2026";
    if (!groups.length) return fail(["No dataset files were found. A dataset is a folder holding dataset.json, requirements.jsonl, links.jsonl, rejected.jsonl and report.json."]);
    var notices = [], problems = [], sets = [];
    for (var i = 0; i < groups.length; i++) {
      var r = await readGroup(groups[i], notices);
      r.problems.forEach(function (p) { problems.push((groups.length > 1 ? groups[i].label + ": " : "") + p); });
      sets.push(r.data);
    }
    if (problems.length) return fail(problems);
    build(sets, notices);
  }

  function fail(problems) {
    S = null;
    show($("loading"), false); show($("ready"), false); show($("error"), true);
    var ul = $("problems"); clear(ul);
    problems.slice(0, 20).forEach(function (p) { ul.appendChild(el("li", "", p, "dataset-problem")); });
    if (problems.length > 20) ul.appendChild(el("li", "", "and " + (problems.length - 20) + " more"));
    document.body.setAttribute("data-state", "error");
  }

  function build(sets, notices) {
    var many = sets.length > 1, recs = [], byKey = {}, linksByKey = {}, links = [], rejected = [], warnings = [], filtered = {}, read = 0;
    sets.forEach(function (d, di) {
      var rep = d.report || {};
      var fo = rep.filtered_out || {}, fsum = 0;
      Object.keys(fo).forEach(function (k) { filtered[k] = (filtered[k] || 0) + fo[k]; fsum += fo[k]; });
      read += typeof rep.raw_records === "number" ? rep.raw_records : d.requirements.length + d.rejected.length + fsum;
      (rep.warnings || []).forEach(function (w) { warnings.push((many ? "[" + d.label + "] " : "") + w); });
      d.requirements.forEach(function (r) { var o = { r: r, ds: di, key: di + "|" + r.mid, text: null }; recs.push(o); byKey[o.key] = o; });
      d.links.forEach(function (l) {
        var o = { l: l, ds: di };
        links.push(o);
        [l.source_mid, l.target_mid].forEach(function (m) { if (m) (linksByKey[di + "|" + m] = linksByKey[di + "|" + m] || []).push(o); });
      });
      d.rejected.forEach(function (x) { rejected.push(x); });
    });
    // depth by following parent_mid; a cycle or a missing parent ends the walk
    var maxDepth = 1, hierarchy = false;
    recs.forEach(function (o) {
      var depth = 1, cur = o, seen = {};
      while (cur.r.parent_mid && byKey[cur.ds + "|" + cur.r.parent_mid] && !seen[cur.key]) { seen[cur.key] = 1; cur = byKey[cur.ds + "|" + cur.r.parent_mid]; depth++; }
      o.depth = depth; if (depth > 1 || o.r.parent_mid) hierarchy = true; if (depth > maxDepth) maxDepth = depth;
    });
    var present = {};
    recs.forEach(function (o) { Object.keys(o.r.fields).forEach(function (k) { present[k] = true; }); });
    var fieldsPresent = STANDARD.filter(function (k) { return present[k]; }).concat(Object.keys(present).filter(function (k) { return STANDARD.indexOf(k) < 0; }).sort());
    var columns = fieldsPresent.filter(function (k) { return STANDARD.indexOf(k) >= 0; }).slice(0, MAX_COLUMNS);
    S = { sets: sets, many: many, recs: recs, byKey: byKey, links: links, linksByKey: linksByKey, rejected: rejected, warnings: warnings, notices: notices, filtered: filtered, read: read,
          hierarchy: hierarchy, maxDepth: maxDepth, fieldsPresent: fieldsPresent, columns: columns, items: recs, selected: -1, filterText: "" };
    paint();
  }

  /* ---------------------------------------------------------------- painting */
  function paint() {
    show($("loading"), false); show($("error"), false); show($("ready"), true);
    $("where").textContent = S.sets.map(function (d) { return d.label; }).join(", ");
    var kept = S.recs.length, rej = S.rejected.length, filt = 0;
    Object.keys(S.filtered).forEach(function (k) { filt += S.filtered[k]; });
    $("c-read").textContent = S.read; $("c-kept").textContent = kept; $("c-rejected").textContent = rej; $("c-filtered").textContent = filt;
    var mm = $("mismatch");
    if (S.read !== kept + rej + filt) { mm.textContent = "These counts do not add up: " + S.read + " read is not " + kept + " kept + " + rej + " rejected + " + filt + " filtered out. Treat the source as incomplete until the importer explains it."; show(mm, true); } else show(mm, false);
    var why = $("filtered-why"); clear(why);
    Object.keys(S.filtered).forEach(function (k) { why.appendChild(el("li", "", k + ": " + S.filtered[k], "filtered-reason")); });
    var w = $("warnings"); clear(w); S.warnings.forEach(function (t) { w.appendChild(el("li", "", t, "warning")); });
    var n = $("notices"); clear(n); S.notices.forEach(function (t) { n.appendChild(el("li", "", t, "viewer-notice")); });
    var uris = {}, fids = {};
    S.recs.forEach(function (o) { uris[o.r.ref && o.r.ref.uri] = (uris[o.r.ref && o.r.ref.uri] || 0) + 1; fids[o.r.fidelity] = (fids[o.r.fidelity] || 0) + 1; });
    var src = $("sources"); clear(src);
    Object.keys(uris).sort().forEach(function (u) { var c = el("span", "chip", u, "source-chip"); c.setAttribute("data-count", uris[u]); src.appendChild(c); });
    var fd = $("fidelities"); clear(fd);
    Object.keys(fids).sort().forEach(function (f) { var c = el("span", "chip cue", f, "fidelity-chip"); c.setAttribute("data-count", fids[f]); fd.appendChild(c); });
    var facts = $("facts"); clear(facts);
    var synth = S.recs.filter(function (o) { return o.r.uid_synthetic; }).length;
    var cnt = {}; S.recs.forEach(function (o) { cnt[o.r.uid] = (cnt[o.r.uid] || 0) + 1; });
    var dup = Object.keys(cnt).filter(function (u) { return cnt[u] > 1; }).length;
    var outside = S.links.filter(function (o) { return o.l.source_mid === null || o.l.target_mid === null || o.l.source_mid === undefined || o.l.target_mid === undefined; }).length;
    var low = 0; S.recs.forEach(function (o) { Object.keys(o.r.conf).forEach(function (k) { if (o.r.conf[k] === "Medium" || o.r.conf[k] === "Low") low++; }); });
    function fact(t, k, v) { var li = el("li", "", t, "fact"); li.setAttribute("data-fact", k); li.setAttribute("data-value", v); facts.appendChild(li); }
    if (synth) fact(synth + " of " + kept + " requirements have an ID the importer invented, because the source gave none.", "synthetic-ids", synth);
    if (dup) fact(dup + " IDs appear on more than one requirement.", "duplicate-ids", dup);
    if (low) fact(low + " field values were read with medium or low confidence.", "low-confidence", low);
    if (outside) fact(outside + " links point to something outside this import. They are kept by ID.", "outside-links", outside);
    show($("verify"), !!fids.extracted);

    var isEmpty = kept === 0;
    show($("empty"), isEmpty); show($("body"), !isEmpty);
    var tn = $("tree-note");
    if (S.hierarchy) { tn.textContent = "Hierarchy: up to " + S.maxDepth + " levels. Indentation shows depth; rows stay in source order."; tn.setAttribute("data-depth", S.maxDepth); show(tn, true); } else show(tn, false);
    $("row-total").textContent = kept;
    paintHead(); paintLinks(); paintRejected();
    $("filter").value = "";
    resetDetail();
    document.body.setAttribute("data-state", isEmpty ? "empty" : "ready");
    if (!isEmpty) { measure(); renderWindow(); }
  }

  function paintHead() {
    var head = $("head"); clear(head);
    var l = $("list");
    l.style.setProperty("--cols", S.columns.length);
    head.style.setProperty("--cols", S.columns.length);
    head.appendChild(el("span", "", "ID")); head.appendChild(el("span", "", "Requirement"));
    S.columns.forEach(function (k) { var c = el("span", "", LABELS[k] || k, "col-head"); c.setAttribute("data-field", k); head.appendChild(c); });
  }

  function paintLinks() {
    var none = S.links.length === 0;
    show($("no-links"), none); show($("trace"), !none);
    var kinds = $("kinds"); clear(kinds); var ul = $("link-list"); clear(ul);
    if (none) return;
    var count = {}; S.links.forEach(function (o) { count[o.l.kind] = (count[o.l.kind] || 0) + 1; });
    Object.keys(count).sort().forEach(function (k) {
      var li = el("li", "chip", "", "link-kind"); li.setAttribute("data-kind", k); li.setAttribute("data-count", count[k]);
      li.appendChild(el("span", "kind", k)); li.appendChild(document.createTextNode(" ")); li.appendChild(el("span", "n", count[k])); kinds.appendChild(li);
    });
    S.links.slice(0, LIST_CAP).forEach(function (o) { ul.appendChild(linkItem(o, null)); });
    if (S.links.length > LIST_CAP) ul.appendChild(el("li", "rq-caption", "Showing the first " + LIST_CAP + " of " + S.links.length + " links. Choose a requirement to see its own.", "links-more"));
  }

  function uidOf(o, end) {
    var mid = o.l[end + "_mid"], uid = o.l[end + "_uid"];
    var rec = mid ? S.byKey[o.ds + "|" + mid] : null;
    return { uid: uid || (rec ? rec.r.uid : null), inside: !!rec };
  }
  function linkItem(o, self) {
    var a = uidOf(o, "source"), b = uidOf(o, "target");
    var li = el("li", "", "", "link");
    li.setAttribute("data-kind", o.l.kind); li.setAttribute("data-source-uid", a.uid === null ? "" : a.uid); li.setAttribute("data-target-uid", b.uid === null ? "" : b.uid);
    var left = self && self === o.l.source_mid ? "this requirement" : (a.uid === null ? "(unknown)" : a.uid);
    var right = self && self === o.l.target_mid ? "this requirement" : (b.uid === null ? "(unknown)" : b.uid);
    li.appendChild(el("span", "", left + " → " + o.l.kind + " → " + right));
    if (!a.inside || !b.inside) { li.appendChild(document.createTextNode(" ")); li.appendChild(el("span", "chip invented", "not in this import", "link-outside")); }
    return li;
  }

  function paintRejected() {
    var box = $("rejected"), ul = $("rejected-list"); clear(ul);
    show(box, S.rejected.length > 0);
    S.rejected.slice(0, LIST_CAP).forEach(function (x) {
      var li = el("li", "", "", "rejected-item");
      li.appendChild(el("strong", "", x.reason, "rejected-reason"));
      var parts = Object.keys(x.fields || {}).map(function (k) { return k + ": " + plain(x.fields[k]); });
      if (x.ref && x.ref.locator) parts.push("at " + x.ref.locator);
      li.appendChild(el("div", "rq-caption", parts.join(" | ")));
      ul.appendChild(li);
    });
    if (S.rejected.length > LIST_CAP) ul.appendChild(el("li", "rq-caption", "Showing the first " + LIST_CAP + " of " + S.rejected.length + " rejected records.", "rejected-more"));
  }

  /* ---------------------------------------------------------------- the windowed list */
  function measure() {
    var win = $("window"), probe = buildRow(S.items.length ? S.items[0] : S.recs[0], -1);
    probe.style.visibility = "hidden"; win.appendChild(probe);
    var h = probe.getBoundingClientRect().height; win.removeChild(probe);
    if (h > 20) rowH = h;
  }

  function buildRow(o, index) {
    var r = o.r, row = el("div", "row", "", "row");
    row.setAttribute("role", "option"); row.id = "row-" + index; row.setAttribute("aria-selected", index === S.selected ? "true" : "false");
    row.setAttribute("data-uid", r.uid); row.setAttribute("data-mid", r.mid); row.setAttribute("data-index", index); row.setAttribute("data-depth", o.depth); row.setAttribute("data-fidelity", r.fidelity);
    row.style.setProperty("--depth", o.depth - 1);
    var uid = el("div", "uid");
    uid.appendChild(el("span", "rq-id", r.uid, "row-uid"));
    if (r.uid_synthetic) { uid.appendChild(document.createTextNode(" ")); uid.appendChild(el("span", "chip invented", "invented ID", "synthetic-badge")); }
    row.appendChild(uid);
    var main = el("div", "main");
    main.appendChild(el("div", "stmt", r.text, "row-text"));
    var meta = el("div", "meta");
    meta.appendChild(el("span", "chip cue", r.fidelity, "row-fidelity"));
    meta.appendChild(el("span", "chip", r.ref && r.ref.uri ? r.ref.uri : "unknown source", "row-source"));
    if (r.fidelity === "extracted") meta.appendChild(el("span", verified[o.key] ? "chip verified" : "chip low", verified[o.key] ? "verified" : "verify", "verify-badge"));
    main.appendChild(meta); row.appendChild(main);
    S.columns.forEach(function (k) {
      var has = Object.prototype.hasOwnProperty.call(r.fields, k);
      var c = el("div", "cell" + (has ? "" : " missing"), has ? plain(r.fields[k]) : "Not provided", "row-cell");
      c.setAttribute("data-field", k); row.appendChild(c);
    });
    return row;
  }

  function renderWindow() {
    if (!S || !S.recs.length) return;
    var sc = $("list"), win = $("window"), sp = $("spacer");
    var first = Math.max(0, Math.floor(sc.scrollTop / rowH) - OVERSCAN);
    var last = Math.min(S.items.length, Math.ceil((sc.scrollTop + sc.clientHeight) / rowH) + OVERSCAN);
    sp.style.height = (S.items.length * rowH) + "px";
    win.style.top = (first * rowH) + "px";
    clear(win);
    for (var i = first; i < last; i++) win.appendChild(buildRow(S.items[i], i));
    if (S.selected >= 0) sc.setAttribute("aria-activedescendant", "row-" + S.selected);
  }

  function applyFilter(text) {
    S.filterText = text; var t = text.trim().toLowerCase();
    S.items = !t ? S.recs : S.recs.filter(function (o) {
      if (o.low === undefined) o.low = (o.r.uid + "\n" + o.r.text).toLowerCase();
      return o.low.indexOf(t) >= 0;
    });
    S.selected = -1; $("list").scrollTop = 0; $("row-total").textContent = S.items.length; resetDetail(); renderWindow();
  }

  function select(i, scroll) {
    if (!S.items.length) return;
    i = Math.max(0, Math.min(S.items.length - 1, i)); S.selected = i;
    var sc = $("list");
    if (scroll) { var top = i * rowH; if (top < sc.scrollTop) sc.scrollTop = top; else if (top + rowH > sc.scrollTop + sc.clientHeight) sc.scrollTop = top + rowH - sc.clientHeight; }
    renderWindow(); paintDetail(S.items[i]);
  }

  /* ---------------------------------------------------------------- the detail panel */
  function resetDetail() { show($("detail-empty"), true); show($("detail-body"), false); clear($("detail-body")); }

  function paintDetail(o) {
    var r = o.r, box = $("detail-body"); clear(box);
    show($("detail-empty"), false); show(box, true);
    var h = el("h3", "rq-id", "", "detail-uid"); h.appendChild(document.createTextNode(r.uid));
    if (r.uid_synthetic) { h.appendChild(document.createTextNode(" ")); h.appendChild(el("span", "chip invented", "invented ID: the source gave none", "detail-synthetic")); }
    box.appendChild(h);
    box.appendChild(el("p", "full rq-statement", r.text, "detail-text"));
    var actions = el("div", "actions");
    var src = el("button", "rq-button", "Show in source", "show-source"); src.type = "button"; src.setAttribute("aria-expanded", "false");
    actions.appendChild(src);
    var vbtn = null;
    if (r.fidelity === "extracted") { vbtn = el("button", "rq-button", verified[o.key] ? "Marked verified" : "Mark as verified", "mark-verified"); vbtn.type = "button"; vbtn.setAttribute("aria-pressed", verified[o.key] ? "true" : "false"); actions.appendChild(vbtn); }
    box.appendChild(actions);
    var loc = el("dl", "", "", "source-location"); loc.hidden = true;
    var ref = r.ref || {};
    [["Source", ref.uri], ["Adapter", ref.adapter], ["Container", ref.container], ["Locator", ref.locator], ["Revision", ref.revision]].forEach(function (p) {
      if (p[1] === undefined || p[1] === null) return; loc.appendChild(el("dt", "", p[0])); loc.appendChild(el("dd", "", p[1]));
    });
    var m = /^p(\d+):blk(\d+)$/.exec(ref.locator || "");
    if (m) { loc.appendChild(el("dt", "", "Position")); loc.appendChild(el("dd", "", "page " + m[1] + ", block " + m[2], "source-position")); }
    box.appendChild(loc);
    src.addEventListener("click", function () { var open = loc.hidden; loc.hidden = !open; src.setAttribute("aria-expanded", open ? "true" : "false"); });
    if (vbtn) {
      var note = el("p", "rq-caption", verified[o.key] ? "Marked verified by you in this page. A reload clears it." : "Not yet verified against the source.", "verified-state");
      box.appendChild(note);
      vbtn.addEventListener("click", function () { verified[o.key] = !verified[o.key]; renderWindow(); paintDetail(o); $("detail-body").querySelector("[data-testid=mark-verified]").focus(); });
    }
    box.appendChild(el("div", "sub", "Fields"));
    var dl = el("dl", "", "", "fields");
    S.fieldsPresent.filter(function (k) { return STANDARD.indexOf(k) >= 0; }).forEach(function (k) {
      var has = Object.prototype.hasOwnProperty.call(r.fields, k);
      dl.appendChild(el("dt", "", LABELS[k]));
      var dd = el("dd", has ? "" : "missing", has ? plain(r.fields[k]) : "Not provided by this source", "field-value"); dd.setAttribute("data-field", k);
      var c = r.conf[k]; if (has && (c === "Medium" || c === "Low")) { dd.appendChild(document.createTextNode(" ")); dd.appendChild(el("span", c === "Low" ? "chip low" : "chip cue", "read with " + c.toLowerCase() + " confidence", "confidence-cue")); }
      dl.appendChild(dd);
    });
    box.appendChild(dl);
    var other = Object.keys(r.fields).filter(function (k) { return STANDARD.indexOf(k) < 0; }).map(function (k) { return [k, r.fields[k]]; })
      .concat(Object.keys(r.extra).map(function (k) { return [k, r.extra[k]]; }));
    if (other.length) {
      box.appendChild(el("div", "sub", "Other fields"));
      var od = el("dl", "", "", "other-fields");
      other.forEach(function (p) { var dt = el("dt", "", p[0], "other-field-name"); od.appendChild(dt); od.appendChild(el("dd", "", plain(p[1]), "other-field-value")); });
      box.appendChild(od);
    }
    var mine = S.linksByKey[o.key] || [];
    if (mine.length) {
      box.appendChild(el("div", "sub", "Links of this requirement"));
      var ul = el("ul", "plain links", "", "detail-links");
      mine.slice(0, LIST_CAP).forEach(function (lo) { ul.appendChild(linkItem(lo, r.mid)); });
      box.appendChild(ul);
    }
  }

  /* ---------------------------------------------------------------- wiring */
  function wire() {
    var list = $("list");
    list.addEventListener("scroll", function () { renderWindow(); });
    list.addEventListener("click", function (e) {
      var row = e.target.closest ? e.target.closest(".row") : null;
      if (row) select(parseInt(row.getAttribute("data-index"), 10), false);
    });
    list.addEventListener("keydown", function (e) {
      if (!S || !S.items.length) return;
      var page = Math.max(1, Math.floor(list.clientHeight / rowH) - 1), cur = S.selected < 0 ? 0 : S.selected, to = null;
      if (e.key === "ArrowDown") to = S.selected < 0 ? 0 : cur + 1; else if (e.key === "ArrowUp") to = cur - 1; else if (e.key === "Home") to = 0; else if (e.key === "End") to = S.items.length - 1;
      else if (e.key === "PageDown") to = cur + page; else if (e.key === "PageUp") to = cur - page;
      if (to !== null) { e.preventDefault(); select(to, true); }
    });
    $("filter").addEventListener("input", function (e) { if (S) applyFilter(e.target.value); });
    $("files").addEventListener("change", function (e) { load(groupsFromFiles(e.target.files)); });
    $("folder").addEventListener("change", function (e) { load(groupsFromFiles(e.target.files)); });
    var timer = null;
    window.addEventListener("resize", function () { clearTimeout(timer); timer = setTimeout(function () { if (S && S.recs.length) { measure(); renderWindow(); } }, 60); });
  }

  wire();
  var params = new URLSearchParams(location.search), wanted = params.getAll("dataset");
  if (wanted.length) load(groupsFromUrls(wanted));
  else document.body.setAttribute("data-state", "idle");
})();
