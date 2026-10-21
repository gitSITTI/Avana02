"""Mutation run for the comparison engine (reqin/src/reqin/compare): each written rule and each piece of machinery under it is broken in a copy, one at a time, and
reqin/tests/test_compare.py must fail. A rule that can be removed without a test noticing is a rule nobody has checked.

Usage: python3 tools/mutation/compare.py [part of a name ...]
       python3 tools/mutation/compare.py --list        the names
       python3 tools/mutation/compare.py --patterns    only check that every change still matches the code exactly once (fast; no tests are run)
Exit status 1 when a change goes unnoticed and is not listed in EQUIVALENT with the reason it is harmless.   See README.md in this folder."""
import atexit
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'reqin')
MUT = tempfile.mkdtemp(prefix='reqin-mutation-compare-')
atexit.register(shutil.rmtree, MUT, True)

C = 'src/reqin/compare/'
R, E, O, CL, L, Q, S, V = (C + f for f in ('rules.py', 'engine.py', 'output.py', 'cluster.py', 'ladder.py', 'quantities.py', 'slots.py', 'vocabulary.py'))

# (name, file, old text that must occur exactly once, new text)
MUTANTS = [
    # ---- rules: the slot rules ----------------------------------------------------------------------------------------------------------------------------------
    ('EQ-DIGEST: equal keys are not enough', R, 'if a.digest == b.digest:\n        return Relation("EQUIVALENT"', 'if False:\n        return Relation("EQUIVALENT"'),
    ('EQ-DIGEST: every pair in a family is equivalent', R, 'if a.digest == b.digest:\n        return Relation("EQUIVALENT"', 'if a.family == b.family:\n        return Relation("EQUIVALENT"'),
    ('MODAL-DIFF is never found', R, 'if a.modal_class != b.modal_class:', 'if False:'),
    ('NEG-CONFLICT is typed as a variant', R, 'Finding("CONFLICT", "NEG-CONFLICT", "polarity_conflict"', 'Finding("VARIANT", "NEG-CONFLICT", "polarity_conflict"'),
    ('NEG-COND: a negation with different conditions is a conflict', R, 'if conds_equal:\n            f.append(Finding("CONFLICT", "NEG-CONFLICT"', 'if True:\n            f.append(Finding("CONFLICT", "NEG-CONFLICT"'),
    ('COND-ABSENT: the unconditional one is the looser', R, 'if not a.conditions and b.conditions:\n            f.append(Finding("SUBSUMES_A", "COND-ABSENT"',
     'if not a.conditions and b.conditions:\n            f.append(Finding("SUBSUMES_B", "COND-ABSENT"'),
    ('COND-ABSENT is never found', R, 'if not a.conditions and b.conditions:', 'if False:'),
    ('COND-DIFF is never found', R, '        else:\n            f.append(Finding("VARIANT", "COND-DIFF"', '        elif False:\n            f.append(Finding("VARIANT", "COND-DIFF"'),
    ('COND-REGION is never found', R, 'if inside(ia, ib) and not inside(ib, ia):', 'if False:'),
    ('COND-REGION: the narrower trigger is the stricter', R, 'out.append(Finding("SUBSUMES_B", "COND-REGION"', 'out.append(Finding("SUBSUMES_A", "COND-REGION"'),
    ('numbers inside conditions are never compared', R, 'conds_equal = _cond_keys(a) == _cond_keys(b)\n    for role in ("main", "condition"):', 'conds_equal = False\n    for role in ("main", "condition"):'),
    ('numbers inside different conditions are compared', R, 'if role == "condition" and not conds_equal:\n            continue', 'if False:\n            continue'),
    # ---- rules: numbers -----------------------------------------------------------------------------------------------------------------------------------------
    ('Q-SUBSUMES: the looser value is the stricter', R, 'if inside(ix, iy):\n        return [Finding("SUBSUMES_A"', 'if inside(ix, iy):\n        return [Finding("SUBSUMES_B"'),
    ('inside() is the wrong way round', R, 'return _lo(x) >= _lo(y) and _hi(x) <= _hi(y)', 'return _lo(x) <= _lo(y) and _hi(x) >= _hi(y)'),
    ('an interval that touches at one point is empty', R, 'return lo[0] > hi[0] or (lo[0] == hi[0] and (lo[1] == 1 or hi[1] == -1))', 'return lo[0] >= hi[0]'),
    ('Q-CONFLICT is never found', R, 'if not intersects(ix, iy):', 'if False:'),
    ('Q-BOUNDS is never found', R, 'if (x_upper and y_lower) or (x_lower and y_upper):', 'if False:'),
    ('Q-UNSTATED is never found', R, 'if not x.comparator or not y.comparator:', 'if False:'),
    ('Q-RANGE: a range is read like a limit', R, 'if x.comparator == "range" or y.comparator == "range":', 'if False:'),
    ('Q-TOLERANCE: values that differ with a tolerance are compared as exact', R, 'if x.tolerance is not None or y.tolerance is not None:\n        return [Finding("VARIANT", "Q-TOLERANCE"',
     'if False:\n        return [Finding("VARIANT", "Q-TOLERANCE"'),
    ('Q-TOLERANCE-TIGHTER: the looser tolerance is the stricter', R, 'stricter = "A" if x.tolerance < y.tolerance else "B"', 'stricter = "A" if x.tolerance > y.tolerance else "B"'),
    ('Q-TOLERANCE-TIGHTER is never found', R, 'if x.tolerance is not None and y.tolerance is not None:\n        stricter', 'if False:\n        stricter'),
    ('Q-EXTRA: the extra number on A makes B stricter', R, 'Finding("SUBSUMES_A" if q.comparator else "VARIANT"', 'Finding("SUBSUMES_B" if q.comparator else "VARIANT"'),
    ('Q-EXTRA: the extra number on B makes A stricter', R, 'Finding("SUBSUMES_B" if q.comparator else "VARIANT"', 'Finding("SUBSUMES_A" if q.comparator else "VARIANT"'),
    ('Q-EXTRA-UNSTATED: a number with no bound counts as a constraint', R, 'Finding("SUBSUMES_A" if q.comparator else "VARIANT"', 'Finding("SUBSUMES_A"'),
    ('Q-MULTI: several numbers are matched by position', R, 'if len(la) == 1 and len(lb) == 1:\n                tol_only', 'if len(la) >= 1 and len(lb) >= 1:\n                tol_only'),
    ('Q-NEGATED: the direction of a bound under a negation is read', R, 'if a.negated or b.negated:', 'if False:'),
    # ---- rules: combining ---------------------------------------------------------------------------------------------------------------------------------------
    ('MIXED: opposite directions become a subsume', R, 'if sa and sb:\n        return ("VARIANT", "MIXED", None)', 'if sa and sb:\n        return ("SUBSUMES", "MIXED", "a")'),
    ('a complementary finding with others is still complementary', R, 'if len(findings) == len(comp) == 1 else', 'if True else'),
    ('a conflict beside a variant is only a variant', R, 'if conflicts:\n        return ("CONFLICT", conflicts[0].rule, None)', 'if conflicts and len(findings) == len(conflicts):\n        return ("CONFLICT", conflicts[0].rule, None)'),
    ('no finding is not written as UNEXPLAINED', R, 'return ("VARIANT", "UNEXPLAINED", None)', 'return ("VARIANT", "MIXED", None)'),
    ('needs_review is not set for a conflict', R, 'return self.type in ("VARIANT", "CONFLICT")', 'return self.type in ("VARIANT",)'),
    # ---- rules: the two near misses between wordings ---------------------------------------------------------------------------------------------------------
    ('SUBJ-DIFF is never found', R, 'if a.predicate_key == b.predicate_key and a.subject_key != b.subject_key:', 'if False:'),
    ('WORDS-DIFF is never found', R, 'if a.subject_key == b.subject_key and a.predicate_key != b.predicate_key:', 'if False:'),
    ('any overlap is enough for a near miss (classify)', R, 'if overlap < tau:\n        return None', 'if False:\n        return None'),
    ('the same words in another order are called different words', R, 'order = sorted(a.predicate_key) == sorted(b.predicate_key)', 'order = False'),
    ('different families are classified as one', R, 'if a.family == b.family:\n        return classify_group(a, b)', 'if True:\n        return classify_group(a, b)'),
    # ---- engine ---------------------------------------------------------------------------------------------------------------------------------------------------
    ('any overlap is enough for a near miss (engine)', E, 'if ov < st.tau_pair:\n            continue', 'if False:\n            continue'),
    ('a family of any size is compared pairwise', E, 'if len(us) > st.max_family:', 'if False:'),
    ('words in too many wordings are used to find pairs', E, 'if len(ix) > st.max_posting or len(ix) < 2:', 'if len(ix) < 2:'),
    ('a cluster is never checked', E, 'valid = cl.check_cluster(u, eq)', 'valid = True'),
    ('pairs are not put in order of seriousness', E, 'pair_rows.sort(key=lambda p: (TYPE_ORDER[p["type"]], -p["score"], p["pid"]))', 'pair_rows.sort(key=lambda p: p["pid"])'),
    ('the stricter side is not swapped with the sides', E, 'if direction:\n                direction = "b" if direction == "a" else "a"', 'if direction:\n                direction = direction'),
    ('the reasons are not swapped with the sides', E, 'why = [{"code": w["code"], "text": w["text"], "a_span": w["b_span"], "b_span": w["a_span"]} for w in why]', 'why = why'),
    ('a word-level pair names only one wording', E, 'if scope == "words":\n            ea, eb = _endpoint(families[a.family], clusters_of, scope)', 'if False:\n            ea, eb = _endpoint(families[a.family], clusters_of, scope)'),
    ('every cluster says its rung is exact', E, 'if all(m.exact == u[0].exact for m in u):', 'if True:'),
    ('the overlap of a cluster is always 1', E, 'min_overlap = min(len(repr_raw & r) / len(repr_raw | r) if (repr_raw | r) else 1.0 for r in raw)', 'min_overlap = 1.0'),
    ('a cluster lists no related pairs', E, '"related": [p["pid"] for p in rel_pairs[: st.max_related]], "related_total": len(rel_pairs),', '"related": [], "related_total": 0,'),
    ('empty requirements are compared', E, 'if u[0].empty:\n            continue', 'if False:\n            continue'),
    ('"no requirements" is not said', E, 'if n == 0:\n        notes.append', 'if False:\n        notes.append'),
    ('"one requirement" is not said', E, 'elif n == 1:', 'elif False:'),
    ('"nothing found" is not said', E, 'elif not clusters and not pair_rows:', 'elif False:'),
    ('the empty-text count is not said', E, 'if any(s.empty for s in slots):', 'if False:'),
    ('the no-modal count is not said', E, 'if any(s.no_modal for s in slots):', 'if False:'),
    ('the several-modals count is not said', E, 'if any(s.compound for s in slots):', 'if False:'),
    ('invented ids are not said', E, 'if any(r.get("uid_synthetic") for r in requirements):', 'if False:'),
    ('too-common words are not said', E, 'if too_common:\n        notes.append', 'if False:\n        notes.append'),
    ('the families not compared are not said', E, 'if skipped_families:\n        limits', 'if False:\n        limits'),
    # ---- clusters -------------------------------------------------------------------------------------------------------------------------------------------------
    ('merge_cliques joins on any edge (chaining)', CL, 'if y in groups and all(m in adj[k] for k in groups[x] for m in groups[y]):', 'if y in groups and any(m in adj[k] for k in groups[x] for m in groups[y]):'),
    ('check_cluster looks only at the first member', CL, 'return all(classify(a, b) == "EQUIVALENT" for i, a in enumerate(members) for b in members[i + 1:])', 'return all(classify(members[0], m) == "EQUIVALENT" for m in members[1:])'),
    ('representative: a named baseline does not count', CL, '(0 if str(f.get("baseline", "")).strip() else 1,', '(1,'),
    ('representative: an approved status does not count', CL, '0 if str(f.get("status", "")).strip().lower() in AUTHORITY else 1,', '1,'),
    ('representative: filled fields do not count', CL, '-sum(1 for k in SIX if str(f.get(k, "")).strip()),', '0,'),
    ('representative: an invented id counts as real', CL, '1 if r.get("uid_synthetic") else 0,', '0,'),
    ('representative: the highest id wins the tie', CL, 'ranked = sorted(members, key=key)', 'ranked = sorted(members, key=key, reverse=True)'),
    # ---- the ladder -----------------------------------------------------------------------------------------------------------------------------------------------
    ('every word weighs the same', L, 'return ({t: math.log(1 + n / c) for t, c in df.items()}, math.log(1 + n))', 'return ({t: 1.0 for t in df}, 1.0)'),
    ('overlap counts all words as shared', L, 'inter = sum(idf.get(t, default) for t in a & b)', 'inter = sum(idf.get(t, default) for t in a | b)'),
    ('the rung is always canonical when the words match', L, 'if f["masked_equal"]:\n        return "masked"', 'if False:\n        return "masked"'),
    # ---- quantities -----------------------------------------------------------------------------------------------------------------------------------------------
    ('"5 s or less" means at least', Q, '_POST_SYM = {"less": "<=",', '_POST_SYM = {"less": ">=",'),
    ('a minute is six seconds', Q, '"min": ("time", 60000.0)', '"min": ("time", 6000.0)'),
    ('a kilohertz is a hertz', Q, '"kHz": ("frequency", 1e3),', '"kHz": ("frequency", 1.0),'),
    ('a milliampere is an ampere', Q, '"mA": ("current", 1e-3)', '"mA": ("current", 1.0)'),
    ('a gram is a kilogram', Q, '"g": ("mass", 0.001), "gram"', '"g": ("mass", 1.0), "gram"'),
    ('a gigabyte is a thousand megabytes', Q, '"GB": ("gbytes", 1.0)', '"GB": ("mbytes", 1000.0)'),
    ('a capital L is not a litre', Q, '"L": ("volume", 1.0), ', ''),
    ('a litre is a millilitre', Q, '"l": ("volume", 1.0),', '"l": ("volume", 1e-3),'),
    ('a single capital letter that is not a listed symbol is a unit', Q, 'if f.isalpha() and len(f) == 1 and got not in UNITS_CS and not (got.islower()):', 'if False:'),
    ('"at least" is not a bound', Q, '">=": ["at least",', '">=": ["at once",'),
    ('ranges are not read', Q, '        if rng:\n            (n2e, n2v, n2w), u2 = rng', '        if False:\n            (n2e, n2v, n2w), u2 = rng'),
    ('a tolerance is not read', Q, '        mt = _TOL.match(text, end)\n        if mt:', '        mt = _TOL.match(text, end)\n        if False:'),
    ('the "in" before a bare number is left as a word', Q, 'elif u1 and not pm:', 'elif False:'),
    ('a leading plus-or-minus is not a bound', Q, '            start = pm.start()\n            cmp_ = "<="', '            start = pm.start()\n            cmp_ = ""'),
    ('a number word with no unit is a quantity', Q, '            if is_word:\n                continue', '            if False:\n                continue'),
    ('a reference number is a quantity', Q, 'if pw and (pw.lower() in _REF_WORDS or', 'if False and (pw.lower() in _REF_WORDS or'),
    ('"less than" includes its value', Q, 'if c == "<":\n            return (None, b, False, False)', 'if c == "<":\n            return (None, b, False, True)'),
    ('"more than" includes its value', Q, 'if c == ">":\n            return (b, None, False, False)', 'if c == ">":\n            return (b, None, True, False)'),
    # ---- slots ----------------------------------------------------------------------------------------------------------------------------------------------------
    ('a "not" after the modal is not a negation', S, 'if n and not _inside(n.start(1), qspans):', 'if False:'),
    ('a "not" inside a bound is a negation', S, 'if n and not _inside(n.start(1), qspans):', 'if n:'),
    ('a leading condition is not read', S, 'lead = _LEAD.match(t)', 'lead = None'),
    ('a leading condition with no comma is not read', S, 'dets = [d for d in _DET.finditer(t, lead.end(), mm.start()) if t[lead.end():d.start()].strip()]', 'dets = []'),
    ('a trailing condition is not read', S, 'tm = next((m for m in _TRAIL.finditer(t, pred_start) if not _inside(m.start(), qspans)), None)', 'tm = None'),
    ('numbers in a condition are main numbers', S, 'q.role = "condition" if any(a <= q.start and q.end <= b for _, a, b in conds) else "main"', 'q.role = "main"'),
    ('conditions joined by "and" are not sorted', S, 'if "and" in tokens and "or" not in tokens:', 'if False:'),
    ('conditions joined by "and" and "or" are sorted', S, 'if "and" in tokens and "or" not in tokens:', 'if "and" in tokens:'),
    ('the passive is not turned into the active', S, 'if modal and len(pred_raw) >= 4 and pred_raw[0] == "be" and "by" in pred_raw[2:]:', 'if False:'),
    ('an irregular participle is not turned into its verb', S, 'pred_raw = [_IRREGULAR_PARTICIPLES.get(part, part)] + subj_raw + pred_raw[2:j]', 'pred_raw = [part] + subj_raw + pred_raw[2:j]'),
    ('"be <anything> by" is a passive', S, 'if agent and (part.endswith("ed") or part in _IRREGULAR_PARTICIPLES):', 'if agent:'),
    ('several modals are not noticed', S, 'sl.compound = any(not _inside(m.start(), qspans) for m in _MODAL.finditer(t, pred_start))', 'sl.compound = False'),
    ('the trigger word is not part of a condition', S, '(trig_c,) + _condition_key(words(body), v)', '_condition_key(words(body), v)'),
    ('"whenever" is not "when"', S, '"whenever": "when",', '"whenever": "whenever",'),
    ('the key ignores the negation', S, 'sl.modal_class, sl.negated, list(sl.predicate_key)', 'sl.modal_class, list(sl.predicate_key)'),
    ('the key ignores the modal', S, 'sl.modal_class, sl.negated, list(sl.predicate_key)', 'sl.negated, list(sl.predicate_key)'),
    ('the key ignores the conditions', S, 'sorted(list(c.key) for c in sl.conditions),', '[],'),
    ('the key ignores the numbers', S, 'sorted(map(list, (q.canon() for q in sl.quantities)), key=json.dumps)', '[]'),
    ('the key ignores the subject', S, 'payload = json.dumps([list(sl.subject_key), sl.modal_class,', 'payload = json.dumps([[], sl.modal_class,'),
    ('the key ignores the predicate', S, 'sl.negated, list(sl.predicate_key), sorted(list(c.key)', 'sl.negated, [], sorted(list(c.key)'),
    # ---- vocabulary and stemming ---------------------------------------------------------------------------------------------------------------------------------
    ('plurals are not stripped', V, 'elif s.endswith("s") and not s.endswith(("ss", "us", "is")):', 'elif False:'),
    ('-ing and -ed are not stripped', V, 'for suf in ("ing", "ed"):', 'for suf in ():'),
    ('a doubled consonant is kept', V, 'if len(b) >= 2 and b[-1] == b[-2] and b[-1] not in "aeioulsz":', 'if False:'),
    ('-ied is not turned into -y', V, 'elif s.endswith("ied") and len(s) > 4:', 'elif False:'),
    ('-ies is not turned into -y', V, 'if s.endswith("ies") and len(s) > 4:', 'if False:'),
    ('a final -e is kept', V, 'if s.endswith("e") and len(s) >= 5:', 'if False:'),
    ('short words are stemmed', V, 'if len(w) < 4 or not w.isalpha():', 'if False:'),
    ('ignored words are compared', V, 'if token in self.ignore:\n            return None', 'if False:\n            return None'),
    ('abbreviations are not expanded', V, 't = self.abbreviations.get(token, token)', 't = token'),
    ('synonyms are not applied', V, 'return self.synonym_of.get(s, s)', 'return s'),
    ('fixed phrases are not applied', V, 'if tuple(tokens[i:i + len(src)]) == src:', 'if False:'),
    ('the vocabulary checksum ignores the synonyms', V, '"synonyms": v.get("synonyms", []), ', ''),
    ('the vocabulary checksum ignores the ignore list', V, '"ignore": sorted(v.get("ignore", []))}', '"ignore": []}'),
    ('a bad vocabulary is accepted', V, '    if bad:\n        raise ValueError("; ".join(bad))', '    if False:\n        raise ValueError("; ".join(bad))'),
    # ---- the output folder and its checker ----------------------------------------------------------------------------------------------------------------------
    ('the checker ignores the checksums', O, 'if hashlib.sha256(data).hexdigest() != meta.get("sha256") or len(data) != meta.get("bytes"):', 'if False:'),
    ('the checker accepts a cluster that is not valid', O, 'if c.get("valid") is not True:', 'if False:'),
    ('the checker accepts a cluster of one', O, 'if len(mem) < 2:', 'if False:'),
    ('the checker accepts a representative that is not a member', O, 'if c.get("representative") not in mem:', 'if False:'),
    ('the checker accepts a cluster that is not a draft', O, 'if c.get("status") != "draft" or c.get("provenance") != "mechanical":', 'if False:'),
    ('the checker accepts an equivalent pair', O, 'if p.get("type") not in TYPES or p.get("type") == "EQUIVALENT":', 'if p.get("type") not in TYPES:'),
    ('the checker accepts a direction on a non-subsume', O, 'if (p.get("direction") in ("a", "b")) != (p.get("type") == "SUBSUMES") or p.get("direction") not in (None, "a", "b"):', 'if False:'),
    ('the checker accepts an unknown basis', O, 'if p.get("basis") not in BASES:', 'if False:'),
    ('the checker accepts a rule that decides another type', O, 'elif RULES[p["rule"]][0] != p.get("type") and p.get("rule") != "MIXED":', 'elif False:'),
    ('the checker accepts the wrong needs_review', O, 'if p.get("needs_review") is not (p.get("type") in ("VARIANT", "CONFLICT")):', 'if False:'),
    ('the checker accepts a score of 7', O, 'or not 0 <= p["score"] <= 1:', 'or False:'),
    ('the checker accepts an unknown rung', O, 'if p.get("rung") not in RUNGS:', 'if False:'),
    ('the checker accepts a requirement on both sides', O, 'if not ma or not mb or set(ma) & set(mb):', 'if not ma or not mb:'),
    ('the checker accepts an unknown cluster', O, 'if cid not in cids:', 'if False:'),
    ('the checker accepts an unknown requirement in a pair', O, '                if m not in mids_seen:\n                    problems.append(f"{w}: {m} has no line in slots.jsonl")', '                if False:\n                    problems.append(f"{w}: {m} has no line in slots.jsonl")'),
    ('the checker accepts any span', O, 'return x is None or (isinstance(x, list) and len(x) == 2', 'return True or (isinstance(x, list) and len(x) == 2'),
    ('the checker does not compare the counts', O, 'if counts.get("clusters") != len(clusters) or counts.get("requirements") != len(slots):', 'if False:'),
    ('the checker does not compare the pair counts', O, 'if counts["pairs"][t] != sum(1 for p in pairs if isinstance(p, dict) and p.get("type") == t):', 'if False:'),
    ('the checker does not match the dataset', O, 'if sha not in [x.get("manifest_sha256") for x in recorded if isinstance(x, dict)]:', 'if False:'),
    ('the checker does not match the requirements', O, 'if req and set(req) != mids_seen:', 'if False:'),
    ('a dataset that has changed is not noticed', O, '            if dprob:\n                problems.append(f"{d} no longer follows the contract', '            if False:\n                problems.append(f"{d} no longer follows the contract'),
    ('writing replaces unrelated files', O, '        if stray:\n            raise CompareError(f"{out} already holds other files', '        if False:\n            raise CompareError(f"{out} already holds other files'),
    ('a dataset that fails its contract is compared', O, '        if problems:\n            raise CompareError(f"{d} does not follow the contract', '        if False:\n            raise CompareError(f"{d} does not follow the contract'),
    ('two imports with the same internal key are compared', O, '            if r["mid"] in seen:', '            if False:'),
]

# a change no test notices, and why that is harmless
EQUIVALENT = {
    'any overlap is enough for a near miss (engine)': 'the same threshold is applied again inside classify(), which a test checks on its own: removing either one leaves the other in force',
}


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT)
    shutil.copytree(SRC + '/src', MUT + '/src', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(SRC + '/tests', MUT + '/tests', ignore=shutil.ignore_patterns('__pycache__', 'fixtures_approved'))


def run():
    r = subprocess.run('PYTHONPATH=src python3 -m pytest tests/test_compare.py -q -x -p no:cacheprovider 2>&1 | tail -5', cwd=MUT, shell=True, capture_output=True, text=True, timeout=900)
    return r.stdout


def main(args):
    if args == ['--list']:
        for m in MUTANTS:
            print(m[0])
        return 0
    if args == ['--patterns']:
        bad = []
        for name, f, old, _new in MUTANTS:
            n = open(os.path.join(SRC, f), encoding='utf-8').read().count(old)
            if n != 1:
                bad.append(name)
                print('PATTERN %s: %s (%d matches)' % ('MISSING' if n == 0 else 'NOT UNIQUE', name, n))
        print('%d of %d changes match the code exactly once' % (len(MUTANTS) - len(bad), len(MUTANTS)))
        return 1 if bad else 0
    survivors = []
    for name, f, old, new in MUTANTS:
        if args and not any(a in name for a in args):
            continue
        reset()
        p = os.path.join(MUT, f)
        s = open(p, encoding='utf-8').read()
        if s.count(old) != 1:
            print('%-70s PATTERN %s' % (name, 'MISSING' if s.count(old) == 0 else 'NOT UNIQUE'), flush=True)
            survivors.append(name)
            continue
        open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
        out = run()
        if ' failed' in out or ' error' in out or 'Error' in out:
            line = next((l for l in out.splitlines() if l.startswith(('FAILED', 'ERROR'))), out.strip().splitlines()[-1] if out.strip() else '')
            print('%-70s CAUGHT: %s' % (name, line[:90]), flush=True)
        elif name in EQUIVALENT:
            print('%-70s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
        else:
            print('%-70s NOT CAUGHT' % name, flush=True)
            survivors.append(name)
    print('\n%s' % ('every change was noticed' if not survivors else '%d went unnoticed: %s' % (len(survivors), '; '.join(survivors))))
    return 1 if survivors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
