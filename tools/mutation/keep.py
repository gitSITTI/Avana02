"""Mutation run for the prototype: Keeping the work: the project file, the browser copy, the checks on what is loaded, two tabs.

Usage: python3 tools/mutation/keep.py [part of a name ...]     (--list shows the names). See README.md in this folder."""
import sys
from common import main

P='parts/persist.js'; K='parts/c7.js'
muts = [
 ('the format is not checked', P, "if (file.format !== PERSIST_FORMAT) return bad(", "if (false) return bad("),
 ('the project is not checked', P, "|| fp.fingerprint !== pj.fingerprint)", "|| false)"),
 ('the record is not checked', P, "if (r !== 'ok') { out.problems.push(", "if (false) { out.problems.push("),
 ('event fields may be anything', P, "['type', 'actor', 'text', 'target', 'time', 'prev', 'hash', 'payload'].every((f) => typeof e[f] === 'string')", "true"),
 ('the record may be any length', P, "ok.events.length > 20000 ||", ""),
 ('the person is not checked', P, "if (ok.person && !PEOPLE.some((p) => p.k === ok.person)) {", "if (false) {"),
 ('other keys are kept', P, "if (PERSIST_KEYS.indexOf(k) < 0) {", "if (false) {"),
 ('names every object has count as clusters', P, "const known = (id) => persistHas(CL_BY, String(id).split(':')[0]) || persistHas(REQ_BY, String(id).split(':')[0]);", "const known = (id) => !!CL_BY[String(id).split(':')[0]] || !!REQ_BY[String(id).split(':')[0]];"),
 ('names every object has count as requirements', P, "if (!persistHas(REQ_BY, id) || !persistPlain(ok[k][id]))", "if (!REQ_BY[id] || !persistPlain(ok[k][id]))"),
 ('a decision may have any outcome', P, "PERSIST_DEC_OUT.indexOf(d.outcome) >= 0 &&", ""),
 ('a decision may cover anything', P, "persistReqIds(d.covers) && persistReqIds(d.kept)", "true"),
 ('a decision may lack its lists', P, "Array.isArray(d.revs) && d.revs.every(persistPlain) &&", ""),
 ('a single-requirement decision may have any outcome', P, "persistHas(RD_BY, d.outcome) &&", ""),
 ('a sign-off may be in any slot', P, "SLOT_KEYS.indexOf(s) >= 0 && persistPlain(g[s])", "persistPlain(g[s])"),
 ('a hand-off may be to anyone', P, "PEOPLE.some((p) => p.k === h.from) && PEOPLE.some((p) => p.k === h.to) &&", ""),
 ('entries of the wrong kind stay', P, "!persistKindIn(ok[k][id], PERSIST_VALUE[k])", "false"),
 ('a label may be for any pair', P, "if (persistHas(by, key) && persistPlain(L)", "if (persistPlain(L)"),
 ('a label may be any relation', P, "persistHas(GOLD_BY, L[w].v) &&", ""),
 ('the cut-off may be anything', P, "|| typeof g.cut !== 'number' || !(g.cut >= 0 && g.cut <= 1))", ")"),
 ('an unknown allocation is kept', P, "if (ok.scope && ok.scope !== 'all' && !ALLOCS.some((a) => a.k === ok.scope)) { delete ok.scope;", "if (false) { delete ok.scope;"),
 ('the chain ignores the link to the entry before', P, "if (e.prev !== prev || h32(e.prev + payload) !== e.hash)", "if (h32(e.prev + payload) !== e.hash)"),
 ('the chain ignores the fingerprint', P, "if (e.prev !== prev || h32(e.prev + payload) !== e.hash)", "if (e.prev !== prev)"),
 ('everything counts as work', P, "return S.events.length > 0 ||", "return true || S.events.length > 0 ||"),
 ('which screen is open is kept', P, "'rdec', 'rform', 'mapOver', 'aiOn', 'aiSheet'];", "'rdec', 'rform', 'mapOver', 'aiOn', 'aiSheet', 'view'];"),
 ('sign-offs are miscounted', P, "signoffs: Object.keys(S.sign || {}).reduce((a, k) => a + Object.keys(S.sign[k] || {}).length, 0)", "signoffs: Object.keys(S.sign || {}).length"),
 ('oversized saved work is kept', P, "if (raw.length > PERSIST_MAX) { s.removeItem(PERSIST_STORE); return", "if (false) { s.removeItem(PERSIST_STORE); return"),
 ('refused saved work stays in the store', P, "if (!r.ok) { s.removeItem(PERSIST_STORE); return", "if (!r.ok) { return"),
 ('unreadable saved work stays in the store', P, "} catch (x) { try { s.removeItem(PERSIST_STORE); } catch (y) { /* nothing more to do */ } return", "} catch (x) { return"),
 ('a blocked store is trusted', P, "s.setItem('reqin-probe', '1'); s.removeItem('reqin-probe'); ", ""),
 ('a full store says it saved', P, "} catch (x) { return 'full'; }", "} catch (x) { return 'saved'; }"),
 ('a restore marks everything as changed', K, "      st.openVer = Object.assign({}, st.liveVer);", "      st.openVer = {};"),
 ('a load marks everything as changed', K, "    merged.openVer = Object.assign({}, merged.liveVer);\n", ""),
 ('a load is not recorded', K, "    merged.events = this.mk(merged.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Loaded saved work from ' + p.name + ' (' + persistSaid(c, ['decisions', 'signoffs']) + ')', 'Project state');", ""),
 ('a good file is loaded without asking', K, "    this._pending = { state: r.state, name, saved: r.saved, counts: r.counts, notes: r.notes };\n    const c = r.counts;", "    this._pending = { state: r.state, name, saved: r.saved, counts: r.counts, notes: r.notes };\n    this.keepApply(this.S);\n    const c = r.counts;"),
 ('a file that cannot be drawn is loaded', K, "const probe = this.keepProbe(r.state);", "const probe = '';"),
 ('nothing is drawn to check a file', K, "const tries = ['home', 'review', 'explorer', 'results', 'vee', 'export', 'audit', 'gold', 'methods', 'policy', 'ai', 'overview'].map((view) => ({ view }))", "const tries = [].map((view) => ({ view }))"),
 ('an empty page writes itself', K, "if (this._keepHold || !persistHasWork(S)) return;", "if (this._keepHold) return;"),
 ('every change writes again', K, "    if (raw === this._keepRaw) return;\n", ""),
 ('a save is not debounced', K, "    clearTimeout(this._keepT);\n", ""),
 ('start over leaves the store', K, "    persistClear(); this._keepRaw = ''; this._pending = null;", "    this._keepRaw = ''; this._pending = null;"),
 ('start over keeps some work', K, "const reset = {}; PERSIST_KEYS.forEach((k) => { reset[k] = DEFAULTS[k]; });", "const reset = {}; PERSIST_KEYS.forEach((k) => { if (k !== 'rdec') reset[k] = DEFAULTS[k]; });"),
 ('start over does not ask', K, "kStart: () => this.setState({ keepAsk: 'start', keepMsg: null }),", "kStart: () => this.keepStartOver(),"),
 ('work saved before opening restores into the middle', K, "view: r.opened ? 'home' : 'open'", "view: 'home'"),
 ('start over is always available', K, "kStartDisabled: !work && !S.keepRestored", "kStartDisabled: false"),
 ('the scope text leaves out that it is not encrypted', K, "It stays in this browser and is not encrypted, so", "It stays in this browser, so"),
]

muts += [
 ('another tab writing is ignored', K, "e.storageArea !== window.localStorage) return; } catch (x) { return; } this.keepOther(); };", "e.storageArea !== window.localStorage) return; } catch (x) { return; } };"),
 ('a held tab still writes', K, "if (this._keepHold || !persistHasWork(S)) return;", "if (!persistHasWork(S)) return;"),
 ('taking the other tab leaves the hold on', K, "    this._keepHold = false; this._keepRaw = ''; this._pending = null;\n    this.setState(Object.assign(merged, { view: 'home', verified: '', tamper: false, chatOpen: false, keepAsk: '', keepSummary: [], keepStatus: 'saved'", "    this._keepRaw = ''; this._pending = null;\n    this.setState(Object.assign(merged, { view: 'home', verified: '', tamper: false, chatOpen: false, keepAsk: '', keepSummary: [], keepStatus: 'saved'"),
 ('keeping this tab does not write it', K, "this._keepHold = false; this._keepRaw = ''; this.keepNow(); this.setState({ keepMsg: { bad: false, text: 'This tab", "this._keepHold = false; this._keepRaw = ''; this.setState({ keepMsg: { bad: false, text: 'This tab"),
 ('closing the tab does not write', K, "this._onHide = () => { clearTimeout(this._keepT); this.keepNow(); };", "this._onHide = () => {};"),
 ('any storage key counts as the other tab', K, "if (e.key !== null && e.key !== PERSIST_STORE) return;", ""),
 ('a closed tab keeps listening', K, "if (this._onStore) window.removeEventListener('storage', this._onStore);", ""),
 ('a closed tab keeps its hide listener', K, "if (this._onHide) window.removeEventListener('pagehide', this._onHide);", ""),
]

EQUIVALENT = {
    'a save is not debounced': 'during a burst of changes the page writes more often (each pause no longer waits for the last change); every write holds the whole current state and a write of an unchanged state is skipped, so what is kept is the same. It could cost time on a very large project; nothing times the autosave on its own',
}

if __name__ == '__main__':
    sys.exit(main(muts, EQUIVALENT))
