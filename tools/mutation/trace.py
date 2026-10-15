"""Mutation run for the prototype: The trace map: what a decision moves outside the requirement list.

Usage: python3 tools/mutation/trace.py [part of a name ...]     (--list shows the names). See README.md in this folder."""
import sys
from common import main

T='parts/trace.js'; C3='parts/c3.js'; C5='parts/c5.js'; C6='parts/c6.js'; L3='parts/logic3.js'; SG='parts/single.js'
muts = [
 ('items move to the first wording, not the kept one', T, "const to = d.newWording ? 'NEW:' + c.id : kept;", "const to = d.newWording ? 'NEW:' + c.id : ms[0].id;"),
 ('superseded wordings are not listed', T, "if (kind !== 'merged' && kind !== 'superseded') return;\n      out.push", "if (kind !== 'merged') return;\n      out.push"),
 ('a child that is itself leaving is listed', T, "(TR_CHILD[r.id] || []).filter((c) => !gone[c]).map", "(TR_CHILD[r.id] || []).map"),
 ('a parent is bare when any child leaves', T, "if ((TR_CHILD[p] || []).every((k) => gone[k])) T.links.push", "if ((TR_CHILD[p] || []).some((k) => gone[k])) T.links.push"),
 ('approved only keeps everything', T, "if (only === 'approved') rem = rem.filter((r) => r.status === 'approved');", ""),
 ('new wording moves its items', T, "action: 'reread', src: x.r.id", "action: 'move', src: x.r.id"),
 ('no requirement is baselined', T, "const trBase = (id) => TR_BL[id] || null;", "const trBase = (id) => null;"),
 ('any text is a change request', T, "const TR_CR_RE = /^CR-\\d{3,6}$/;", "const TR_CR_RE = /.*/;"),
 ('a cell that starts with = is not marked', T, "if (/^[=+\\-@\\t\\r]/.test(t)) t = \"'\" + t;", ""),
 ('a covering requirement that leaves is not followed', T, "rem.forEach((r) => { r.to = settle(r.to); });", ""),
 ('items with nowhere to go are counted as moved', T, "action: r.to ? 'move' : 'choose' }, base));", "action: 'move' }, base));"),
 ('the stricter wording is not put under the general one', T, "else if (c.rel === 'SUBSUMES' && VREQ[m.id].lvl > VREQ[first.id].lvl) TR_PARENT[m.id] = first.id;", ""),
 ('new wording is not named as the target', T, "const to = d.newWording ? 'NEW:' + c.id : kept;", "const to = d.newWording ? '' : kept;"),
 ('the file does not say it is sample data', T, "    sample_data: true,", "    sample_data: false,"),
 ('supersede keeps nobody (the V)', L3, "kid = d.survivor || (d.newWording ? '' : ((ms.find((m) => d.by[m.id].kind === 'keep') || {}).id || '')), keep", "kid = d.survivor, keep"),
 ('a pending decision is called approved', T, "status: x.st === 'approved' ? 'approved' : 'pending', cr: c.baselined", "status: 'approved', cr: c.baselined"),
 ('two items share an ID', T, "(1000 + i * 4 + k)", "(1000 + i * 2 + k)"),
 ('a parent is picked from the same level', T, "pool[r.alloc + '|' + (l - 1)] || pool['*|' + (l - 1)]", "pool[r.alloc + '|' + l] || pool['*|' + l]"),
 ('the download is not logged', C6, "      events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Downloaded '", "      eventsX: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Downloaded '"),
 ('the package does not list the trace map', C3, "'change-record.rst', 'alias-map.csv', 'trace-map.json']", "'change-record.rst']"),
 ('a change request is kept for an unbaselined requirement', C5, "cr: trBase(r.id) && (f.kind === 'reword' || RD_REMOVES(f.kind)) ? trCrNorm(f.cr) : '',", "cr: trCrNorm(f.cr),"),
 ('a baselined drop needs no change request', SG, "if (bl && (kind === 'reword' || RD_REMOVES(kind)) && !TR_CR_RE.test(trCrNorm(f.cr)))", "if (false)"),
 ('the panel never sees a bare parent', T, "out.bare = !!p && (TR_CHILD[p] || []).every((k) => k === r.id);", "out.bare = false;"),
 ('a method change is never noticed', T, "const methodChange = !!(tv && v.vm && tv.vm && v.vm !== tv.vm);", "const methodChange = false;"),
 ('a level change is never noticed', T, "levelChange: !!(tv && tv.lvl !== v.lvl), methodChange, action", "levelChange: false, methodChange, action"),
 ('the kept child is moved under itself', T, "const now = c === r.to ? TR_PARENT[r.id] || '' : r.to;", "const now = r.to;"),
 ('baselines are listed for every removal', T, "const bases = b ? [Object.assign", "const bases = true ? [Object.assign"),
 ('the CSV leaves out the header', T, "return [d.head.join(',')].concat(", "return [].concat("),
 ('quotes are not doubled in the CSV', T, "t.replace(/\"/g, '\"\"')", "t"),
 ('every parent is a child of the first requirement', T, "else if (trH(m.id, 'sp', 100) < 70) TR_PARENT[m.id] = TR_PARENT[first.id];", "else if (true) TR_PARENT[m.id] = TR_PARENT[first.id];"),
]

EQUIVALENT = {}

if __name__ == '__main__':
    sys.exit(main(muts, EQUIVALENT))
