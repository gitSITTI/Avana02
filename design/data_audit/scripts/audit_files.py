"""The checks that read files rather than open a page: known (the person's own records against the screen), scan (the person's source) and diff (two copies of the data).

Standard library only, except `known`, which needs a saved visit of the page (audit_net.py). Everything here only reads. Nothing is written except into the session folder.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_common as C  # noqa: E402
import audit_values as V  # noqa: E402

sys.path.insert(0, str(C.REPO / "tools" / "gui_checks"))

ID_NAMES = ("uid", "id", "identifier", "req_id", "reqid", "requirement_id", "key", "number", "name")
TEXT_NAMES = ("text", "statement", "description", "requirement", "title", "summary", "name")
MAX_SHOWN = 12


# ------------------------------------------------------------------------------------------------ reading the person's data
def _read_text(p: Path) -> tuple:
    """(text, note). UTF-8 if the file is UTF-8; otherwise Windows-1252 (what a spreadsheet or DOORS export written on Windows usually is), and the note says so."""
    raw = p.read_bytes()
    try:
        return raw.decode("utf-8-sig"), None
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "%s is not UTF-8; it was read as Windows-1252. If accented letters look wrong in the findings, save it as UTF-8 and run again." % p.name


def _record_lists(doc, path="$", depth=0):
    """Every list of objects in a JSON document, with where it is, not looking inside the objects of a list."""
    if isinstance(doc, list):
        if doc and any(isinstance(x, dict) for x in doc):
            yield path, [x for x in doc if isinstance(x, dict)]
    elif isinstance(doc, dict) and depth < 5:
        for k, v in doc.items():
            yield from _record_lists(v, "%s.%s" % (path, k), depth + 1)


def load_records_noted(path) -> tuple:
    """(records, note): a list of records (dicts) from a JSON file (a list, or an object holding records at any depth: {"data": {"items": [...]}}), a JSON-lines file, or a CSV
    file. `note` is None, or a sentence about how the file had to be read."""
    p = Path(path)
    if not p.is_file():
        raise SystemExit("not a file: %s" % path)
    raw, note = _read_text(p)
    suf = p.suffix.lower()
    if suf in (".csv", ".tsv"):
        rows = list(csv.DictReader(io.StringIO(raw), delimiter="\t" if suf == ".tsv" else ","))
        return [dict(r) for r in rows], note
    if suf in (".jsonl", ".ndjson"):
        out = []
        for n, line in enumerate(raw.splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    raise SystemExit("%s line %d is not JSON" % (p.name, n))
        return [r for r in out if isinstance(r, dict)], note
    try:
        doc = json.loads(raw)
    except ValueError as e:
        raise SystemExit("%s is not JSON: %s" % (p.name, e))
    found = list(_record_lists(doc))
    if not found:
        raise SystemExit("%s: no list of records found (a list of objects, or an object holding one)" % p.name)
    if len(found) > 1:
        found.sort(key=lambda t: -len(t[1]))
        if len(found[0][1]) == len(found[1][1]):
            raise SystemExit("%s: more than one list of records (%s). Save the one you mean as its own file." % (p.name, ", ".join("%s has %d" % (w, len(r)) for w, r in found[:4])))
        note = (note + " " if note else "") + "%s holds %d lists of records; the longest (%s, %d records) was used." % (p.name, len(found), found[0][0], len(found[0][1]))
    return found[0][1], note


def load_records(path) -> list:
    return load_records_noted(path)[0]


def guess_id_field(records: list) -> str | None:
    keys = list(dict.fromkeys(k for r in records for k in r))
    lower = {k.lower(): k for k in keys}
    cands = [lower[n] for n in ID_NAMES if n in lower] + keys
    for k in cands:
        vals = [str(r.get(k, "")).strip() for r in records]
        if all(vals) and len(set(vals)) == len(vals):
            return k
    return None


def guess_text_field(records: list, id_field: str | None) -> str | None:
    keys = list(dict.fromkeys(k for r in records for k in r if k != id_field))
    lower = {k.lower(): k for k in keys}
    for n in TEXT_NAMES:
        if n in lower:
            return lower[n]
    best, score = None, 0.0
    for k in keys:
        vals = [r.get(k) for r in records if isinstance(r.get(k), str)]
        if vals and sum(len(x) for x in vals) / len(vals) > score:
            best, score = k, sum(len(x) for x in vals) / len(vals)
    return best


def _unusual(rec: dict) -> bool:
    for v in rec.values():
        if isinstance(v, str) and (re.search(r"[^\x00-\x7f]|[<>&\"']|\n|^\s|\s$", v)):
            return True
    return False


def pick_sample(records: list, text_field: str | None, n: int = 5) -> list:
    """[(why, index)]: the first, the last, a middle one, the longest text, one with unusual characters (markup, quotes, accents, line breaks); then evenly spaced ones up to n."""
    if not records:
        return []
    picks, used = [], set()

    def add(why, i):
        if i is not None and i not in used and len(picks) < n:
            used.add(i)
            picks.append((why, i))
    add("the first record", 0)
    add("the last record", len(records) - 1)
    add("a record from the middle", len(records) // 2)
    if text_field:
        add("the record with the longest text", max(range(len(records)), key=lambda i: len(str(records[i].get(text_field) or ""))))
    add("a record with unusual characters (markup, quotes, accents or line breaks)", next((i for i, r in enumerate(records) if _unusual(r)), None))
    step = max(1, len(records) // (n + 1))
    for i in range(step, len(records), step):
        add("a record picked at an even spacing", i)
    return picks


# ------------------------------------------------------------------------------------------------ known
def _group(target: dict, items: list, other_ids: set) -> list:
    """The things on the screen that sit with the target (the nearest enclosing part that holds no other record's ID)."""
    best = [target]
    for depth in range(1, min(len(target.get("anc", [])), 8)):
        anc = target["anc"][depth]
        grp = [it for it in items if anc in it.get("anc", [])]
        if any(V.norm(it["text"]) in other_ids for it in grp if it is not target):
            break
        best = grp
    return best


def _head_key(head: str, keys) -> str | None:
    h = re.sub(r"[^a-z0-9]", "", (head or "").lower())
    for k in keys:
        if h and re.sub(r"[^a-z0-9]", "", str(k).lower()) == h:
            return k
    return None


def _same(shown: str, value) -> bool:
    a, b = V.norm(shown), V.norm(value)
    return a == b or (len(b) >= 40 and V.statement_in(b, a)) or (len(a) >= 40 and V.statement_in(a, b))


def known(sess: Path, hat: str, rec_visit, data_path, id_field: str | None = None, text_field: str | None = None, n: int = 5) -> dict:
    """Check a handful of the person's own records against the recorded screen, and write a sheet for the person to tick."""
    records, note = load_records_noted(data_path)
    if not records:
        return C.result("known", hat, "Not run: no records in %s." % Path(data_path).name, [], not_checked=["no records to pick from"], verdict="not-run")
    idf = id_field or guess_id_field(records)
    if not idf:
        raise SystemExit("could not find a field that identifies each record (unique, never empty). Name it with --id-field.")
    txf = text_field or guess_text_field(records, idf)
    if not rec_visit.ok:
        return C.result("known", hat, "Not run: the page did not open: " + rec_visit.error, [], not_checked=["the screen was not read"], verdict="not-run")
    all_ids = {V.norm(r.get(idf)) for r in records}
    picks = pick_sample(records, txf, n)
    items = rec_visit.items
    F, sheet, found_n, wrong, absent_in = [], [], 0, 0, {}
    if note:
        F.append(C.finding("known.encoding", "info", "the person's data file", note, "", ""))
    seen_ids = Counter(V.norm(r.get(idf)) for r in records)
    dupes = [k for k, c in seen_ids.items() if c > 1]
    if dupes:
        F.append(C.finding("known.duplicate-ids", "medium", "the person's data file", "%d ID(s) in the field %r belong to more than one record, so the record found on the screen may not be the one picked." % (len(dupes), idf),
                           ", ".join(dupes[:5]), "Name a field that is unique with --id-field, or check the data."))
    for why, i in picks:
        r = records[i]
        rid = str(r.get(idf))
        others = all_ids - {V.norm(rid)}
        hit = next((it for it in items if V.norm(it["text"]) == V.norm(rid)), None)
        if hit is None:
            hit = next((it for it in items if V.norm(rid) in [a["value"] for a in V.atoms(it["text"]) if a["kind"] == "id"]), None)
        if hit is None:
            F.append(C.finding("known.missing.%s" % re.sub(r"\W+", "", rid)[:20], "low", "record %s (%s)" % (rid, why),
                               "The record's ID is not on the screen.", "", "It may be on another page or behind a search or a click: reach it with --setup, or say where it is. If it should be here, it is missing."))
            sheet.append((why, r, None, []))
            continue
        found_n += 1
        grp = _group(hit, items, others)
        sheet.append((why, r, hit, grp))
        gtext = " ".join(V.norm(g["text"]) for g in grp)
        # the field named by a column heading must show that field's value
        for g in grp:
            k = _head_key(g.get("head"), [x for x in r if x != idf])
            if k is not None and not _same(g["text"], r.get(k)) and not (isinstance(r.get(k), (int, float)) and V.canon_number(g["text"]) == V.canon_number(str(r.get(k)))):
                wrong += 1
                F.append(C.finding("known.field.%s.%s" % (re.sub(r"\W+", "", rid)[:20], re.sub(r"\W+", "", str(k))[:12]), "high", "record %s, the %r column" % (rid, g.get("head")),
                                   "The screen shows %r under %r; the data has %r for that field." % (C.short(g["text"], 80), g.get("head"), C.short(str(r.get(k)), 80)),
                                   "", "Read the cell from the field its heading names."))
        # the text
        if txf and r.get(txf):
            want = str(r.get(txf))
            if not any(_same(g["text"], want) for g in grp) and not V.statement_in(V.norm(want), gtext) and V.norm(want) not in gtext:
                other = next((g for g in grp if len(g["text"]) >= 30 and g is not hit), None)
                if other is not None:
                    wrong += 1
                    F.append(C.finding("known.text.%s" % re.sub(r"\W+", "", rid)[:20], "high", "record %s" % rid, "The text beside the ID is not the record's text.",
                                       "screen: %s | data: %s" % (C.short(other["text"], 90), C.short(want, 90)), "Check which record the text is read from."))
                else:
                    F.append(C.finding("known.text-absent.%s" % re.sub(r"\W+", "", rid)[:20], "medium", "record %s" % rid, "The record's text is not on the screen beside its ID.", C.short(want, 120),
                                       "It may be shown on a detail panel after a click; reach it with --setup. If it should be here, it is missing or cut."))
        # fields not shown with it
        for k, v in r.items():
            if k not in (idf, txf) and v not in (None, "") and V.norm(v) not in gtext and not isinstance(v, (dict, list)):
                absent_in.setdefault(k, []).append(rid)
    if absent_in:
        F.append(C.finding("known.absent", "info", "the records picked", "Fields of the data that are not on the screen beside the ID: %s." % "; ".join("%s (%d of %d records found)" % (k, len(v), found_n) for k, v in list(absent_in.items())[:8]),
                           "", "They may not be meant to be shown here, or be shown elsewhere. The sheet has a place to say which."))
    sheet_path = _write_sheet(sess, sheet, idf, txf, rec_visit)
    summary = "%d records picked from the data (%d rows read, ID field %r%s); %d found on the screen, %d with something different from the data. Sheet to tick: %s." % (
        len(picks), len(records), idf, ", text field %r" % txf if txf else "", found_n, wrong, sheet_path.name)
    return C.result("known", hat, summary, F, {"records_in_data": len(records), "picked": len(picks), "on_screen": found_n, "different": wrong},
                    list(C.skills()["known"]["cannot_find"]) + ["fields the data holds that the screen is not meant to show", "numbers shown under a heading that does not name the field"], [str(sheet_path)])


def _write_sheet(sess: Path, sheet: list, idf: str, txf, visit) -> Path:
    L = ["# Records to check by hand", "",
         "These were picked from your data. For each, look at the screen (%s) and tick what is true. The audit cannot tick for you." % visit.url, "",
         "This file holds your data. It stays in the session folder: do not put it in a repository.", ""]
    for n, (why, r, hit, grp) in enumerate(sheet, 1):
        L += ["## %d. %s: %s" % (n, r.get(idf), why), "", "In your data:", ""]
        L += ["- %s: %s" % (k, C.short(str(v), 200)) for k, v in r.items()]
        L += ["", "On the screen beside the ID:", ""]
        L += ["- " + (C.short(g["text"], 160) + ("  (column %s)" % g["head"] if g.get("head") else "")) for g in grp if g is not hit] if hit else ["- the ID was not found on this screen"]
        L += ["", "- [ ] the ID is the same", "- [ ] the text is the same, word for word", "- [ ] the other fields shown are the same as in the data", "- [ ] nothing from another record is mixed in", ""]
    p = Path(sess) / "known_values.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p


# ------------------------------------------------------------------------------------------------ scan
DATA_RULES = {"typed-in-requirement": "high", "typed-in-id": "high", "typed-in-record": "high", "typed-in-count": "high",
              "storage": "medium", "html-injection": "medium", "dynamic-code": "medium", "outside-data": "low"}


def scan(sess: Path, hat: str, source) -> dict:
    import hardcode_scan as H
    root = Path(source)
    if not root.is_dir():
        raise SystemExit("--source must be a folder of the app's source files: %s" % source)
    found = [f for f in H.scan(root) if f["rule"] in DATA_RULES]
    F, per = [], Counter()
    for f in found:
        per[f["rule"]] += 1
        if per[f["rule"]] <= 5:
            F.append(C.finding("scan.%s.%d" % (f["rule"], per[f["rule"]]), DATA_RULES[f["rule"]], "%s line %d" % (f["file"], f["line"]), f["why"][0].upper() + f["why"][1:] + " (%s)." % f["rule"],
                               C.short(f["text"], 120), "Read the value from the data instead, or take it out."))
    for rule, n in per.items():
        if n > 5:
            F.append(C.finding("scan.%s.more" % rule, "info", "the source", "%d more %s findings are not listed one by one." % (n - 5, rule), "", ""))
    files = len({f["file"] for f in found})
    read, unread, skipped = coverage(root, H)
    if skipped:
        F.append(C.finding("scan.skipped-folders", "info", "the source", "Folders the scan does not read: %s." % "; ".join("%s (%d files)" % (k, v) for k, v in sorted(skipped.items())), "",
                           "A built copy of the app (dist, build) is what runs; if sample data is in it, the scan did not look."))
    data_like = {k: v for k, v in unread.items() if k in (".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".yaml", ".yml", ".sql")}
    if data_like:
        F.append(C.finding("scan.unread-data", "medium", "the source", "Files that could hold sample data were not read: %s." % ", ".join("%d %s" % (v, k) for k, v in sorted(data_like.items())),
                           "", "The scan reads code and markup only. A fixture, a seed file or a mock the page loads is a place for made-up records: look at those files by hand."))
    other = {k: v for k, v in unread.items() if k not in data_like}
    if other:
        F.append(C.finding("scan.unread-code", "info", "the source", "Other files were not read: %s." % ", ".join("%d %s" % (v, k) for k, v in sorted(other.items())), "",
                           "A server, a script or a mock written in another language can hold typed-in data too."))
    summary = "%d finding(s) about data written into, or kept by, the source: %s. %d files read (code and markup). (Design rules such as literal colours are not part of this audit; run tools/gui_checks/hardcode_scan.py for them.)" % (
        len(found), ", ".join("%d %s" % (n, r) for r, n in per.items()) or "none", read)
    return C.result("scan", hat, summary, F, {"findings": len(found), "files": files, "files_read": read, **{r: n for r, n in per.items()}}, list(C.skills()["scan"]["cannot_find"]))


UNREAD_SUFFIXES = {".json", ".jsonl", ".ndjson", ".csv", ".tsv", ".yaml", ".yml", ".sql", ".py", ".rb", ".php", ".java", ".go", ".cs", ".xml"}
IGNORED_NAMES = {"package.json", "package-lock.json", "tsconfig.json", "tokens.json", "yarn.lock", "composer.json", "pyproject.toml"}


def coverage(root: Path, H) -> tuple:
    """(files read, {suffix: files not read that could hold data or logic}, {folder: files in a folder the scan skips}) so that a person can see what the scan looked at."""
    read, unread, skipped = 0, Counter(), Counter()
    readable = H.CODE | H.MARK | H.STYLE
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).parts
        in_skipped = [part for part in rel[:-1] if part in H.SKIP_DIRS and part not in (".git", "__pycache__", "fonts")]
        if in_skipped:
            skipped[in_skipped[0]] += 1
            continue
        if ".git" in rel[:-1] or "__pycache__" in rel[:-1] or any(part in H.SKIP_DIRS for part in rel[:-1]):
            continue
        if p.suffix.lower() in readable and p.name not in H.SKIP_FILES and not p.name.endswith(".min.js"):
            read += 1
        elif p.suffix.lower() in UNREAD_SUFFIXES and p.name not in IGNORED_NAMES:
            unread[p.suffix.lower()] += 1
    return read, dict(unread), dict(skipped)


# ------------------------------------------------------------------------------------------------ diff
def _index(records: list, key: str, label: str):
    idx, bad = {}, []
    for n, r in enumerate(records, 1):
        k = r.get(key)
        if k in (None, ""):
            bad.append((label, n, "no %r" % key))
            continue
        k = str(k)
        if k in idx:
            bad.append((label, n, "the key %r appears more than once" % k))
        idx[k] = r
    return idx, bad


def diff(sess: Path, hat: str, before, after, key: str, allowed_fields=None, expect_keys=None) -> dict:
    """Compare two copies of the same data record by record and field by field. Reads both files; changes neither."""
    A, na = load_records_noted(before)
    B, nb = load_records_noted(after)
    ia, bad_a = _index(A, key, "before")
    ib, bad_b = _index(B, key, "after")
    F = [C.finding("diff.encoding", "info", "the data files", n, "", "") for n in (na, nb) if n]
    for label, n, why in (bad_a + bad_b)[:MAX_SHOWN]:
        F.append(C.finding("diff.key.%s.%d" % (label, n), "high", "%s copy, record %d" % (label, n), "A record has %s." % why, "", "Fix the key field or name another with --key. The comparison below skips such records."))
    removed = [k for k in ia if k not in ib]
    added = [k for k in ib if k not in ia]
    changed = {}
    for k in ia:
        if k in ib:
            fields = {f for f in set(ia[k]) | set(ib[k]) if ia[k].get(f) != ib[k].get(f)}
            if fields:
                changed[k] = {f: (ia[k].get(f), ib[k].get(f)) for f in sorted(fields)}
    allowed = set(allowed_fields or [])
    expect = set(expect_keys or [])
    if removed:
        F.append(C.finding("diff.removed", "high", "the data", "%d record(s) are in the before copy and not in the after copy." % len(removed), ", ".join(removed[:MAX_SHOWN]),
                           "Confirm each was meant to go. A removed record cannot be recovered from the after copy."))
    if added:
        sev = "info" if expect and set(added) <= expect else "medium"
        F.append(C.finding("diff.added", sev, "the data", "%d record(s) are new in the after copy." % len(added), ", ".join(added[:MAX_SHOWN]), "Confirm each was meant to be created."))
    per_field = Counter(f for ch in changed.values() for f in ch)
    for f, n in per_field.most_common():
        out_of_scope = bool(allowed) and f not in allowed
        bulk = n >= 5 and n >= 0.2 * max(1, len(ia))
        if out_of_scope:
            F.append(C.finding("diff.outside.%s" % re.sub(r"\W+", "", str(f))[:16], "high", "field %r" % f, "The field %r changed in %d record(s), and it was not one of the fields meant to change (%s)." % (f, n, ", ".join(sorted(allowed))),
                               ", ".join(list(k for k, ch in changed.items() if f in ch)[:MAX_SHOWN]), "Undo it, or add the field to what was meant to change after a person has read it."))
        elif bulk:
            F.append(C.finding("diff.bulk.%s" % re.sub(r"\W+", "", str(f))[:16], "medium", "field %r" % f, "The field %r changed in %d of %d records at once." % (f, n, len(ia)), "", "A change in many records at once is often a mapping or format mistake: read a few."))
    if expect:
        stray = [k for k in list(changed) + removed + added if k not in expect]
        if stray:
            F.append(C.finding("diff.stray", "high", "the data", "%d record(s) changed that were not among those meant to change." % len(stray), ", ".join(stray[:MAX_SHOWN]), "Undo them, or say why they changed."))
    ws = [k for k, ch in changed.items() if all(isinstance(a, str) and isinstance(b, str) and V.norm(a) == V.norm(b) for a, b in ch.values())]
    if ws:
        F.append(C.finding("diff.whitespace", "low", "the data", "%d record(s) differ only in spacing or letter case." % len(ws), ", ".join(ws[:MAX_SHOWN]), "Check they were meant to change."))
    path = _write_diff(sess, ia, ib, changed, removed, added)
    summary = "%d records before, %d after: %d changed, %d removed, %d added. The full list is in %s. Nothing was written to any system; both files were only read." % (len(ia), len(ib), len(changed), len(removed), len(added), path.name)
    return C.result("diff", hat, summary, F, {"before": len(ia), "after": len(ib), "changed": len(changed), "removed": len(removed), "added": len(added), "outside_scope": sum(1 for f in per_field if allowed and f not in allowed)},
                    list(C.skills()["diff"]["cannot_find"]), [str(path)])


def _write_diff(sess: Path, ia: dict, ib: dict, changed: dict, removed: list, added: list) -> Path:
    L = ["# What changed", "", "Compared record by record. This file holds your data: keep it in the session folder.", ""]
    L += ["## Removed (%d)" % len(removed), ""] + ["- %s" % k for k in removed] + [""]
    L += ["## Added (%d)" % len(added), ""] + ["- %s" % k for k in added] + [""]
    L += ["## Changed (%d)" % len(changed), "", "| record | field | before | after |", "|---|---|---|---|"]
    for k, ch in changed.items():
        for f, (a, b) in ch.items():
            L.append("| %s | %s | %s | %s |" % (k, f, C.short(str(a), 80).replace("|", "\\|"), C.short(str(b), 80).replace("|", "\\|")))
    p = Path(sess) / "diff.md"
    p.write_text("\n".join(L) + "\n", encoding="utf-8")
    return p
