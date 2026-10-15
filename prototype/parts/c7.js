  /* ----- keeping the work: autosave to this browser, save to a file, load from a file, start over (the rules and the checks are in persist.js) ----- */
  constructor(props) {
    super(props);
    const r = persistRead(), st = Object.assign({}, this.state || {});
    st.keepStatus = r.status;
    if (r.state) {
      Object.assign(st, r.state, { view: r.opened ? 'home' : 'open', keepRestored: { at: r.saved, counts: r.counts }, keepAt: r.saved });
      st.openVer = Object.assign({}, st.liveVer);   // what was open when it was saved is what is current now, so nothing reads as changed behind the person's back
      st.keepStatus = 'saved';
    } else if (r.refused) st.keepMsg = { bad: true, text: 'The work saved in this browser could not be used and was removed: ' + r.refused, notes: [] };
    this.state = st;
  }
  setState(o, cb) { super.setState(o, cb); this.keepSoon(); }
  /* two tabs of one browser share one store: when the other tab writes, this one stops saving until the person says whose work stands */
  componentDidMount() {
    if (typeof window === 'undefined' || !window.addEventListener) return;
    this._onStore = (e) => { if (e.key !== null && e.key !== PERSIST_STORE) return; try { if (e.storageArea && e.storageArea !== window.localStorage) return; } catch (x) { return; } this.keepOther(); };
    window.addEventListener('storage', this._onStore);
    // the last change before a tab is closed or hidden is written at once, not after the pause
    this._onHide = () => { clearTimeout(this._keepT); this.keepNow(); };
    this._onVis = () => { try { if (document.visibilityState === 'hidden') this._onHide(); } catch (x) { /* no document */ } };
    window.addEventListener('pagehide', this._onHide);
    try { document.addEventListener('visibilitychange', this._onVis); } catch (x) { /* no document */ }
  }
  componentWillUnmount() {
    if (typeof window !== 'undefined') {
      if (this._onStore) window.removeEventListener('storage', this._onStore);
      if (this._onHide) window.removeEventListener('pagehide', this._onHide);
      try { if (this._onVis) document.removeEventListener('visibilitychange', this._onVis); } catch (x) { /* no document */ }
    }
    clearTimeout(this._keepT);
  }
  keepOther() { clearTimeout(this._keepT); this._keepHold = true; super.setState({ keepStatus: 'other' }); }
  keepTakeOther() {
    const r = persistRead();
    if (!r.state) { this._keepHold = false; this._keepRaw = ''; super.setState({ keepStatus: r.status, keepMsg: { bad: false, text: 'The other tab has no saved work now, so this tab keeps its own.', notes: [] } }); this.keepSoon(); return; }
    const merged = {}; PERSIST_KEYS.forEach((k) => { merged[k] = DEFAULTS[k]; });
    Object.assign(merged, r.state); merged.openVer = Object.assign({}, merged.liveVer);
    this._keepHold = false; this._keepRaw = ''; this._pending = null;
    this.setState(Object.assign(merged, { view: 'home', verified: '', tamper: false, chatOpen: false, keepAsk: '', keepSummary: [], keepStatus: 'saved', keepAt: r.saved, keepRestored: null, keepMsg: { bad: false, text: 'Now showing the work the other tab saved. The changes made in this tab since then were dropped.', notes: [] } }));
  }
  keepKeepMine() { this._keepHold = false; this._keepRaw = ''; this.keepNow(); this.setState({ keepMsg: { bad: false, text: 'This tab’s work was saved over what the other tab had.', notes: [] } }); }
  keepSoon() {
    if (typeof window === 'undefined' || typeof setTimeout === 'undefined' || this._dry) return;
    clearTimeout(this._keepT);
    this._keepT = setTimeout(() => this.keepNow(), 350);
  }
  keepNow() {
    const S = this.S;
    if (this._keepHold || !persistHasWork(S)) return;
    let raw = '';
    try { raw = JSON.stringify(persistPick(S)) + '|' + (S.view === 'open' || S.view === 'import' ? 'o' : 'w'); } catch (x) { return; }
    if (raw === this._keepRaw) return;
    this._keepRaw = raw;
    const status = persistWrite(S, S.view !== 'open' && S.view !== 'import');
    super.setState({ keepStatus: status, keepAt: status === 'saved' ? new Date().toISOString() : S.keepAt });
  }
  keepEvent(S, text, target) { const P = this.person(S); return this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), text, target || 'Project state'); }
  keepSave(S) {
    const f = persistFile(S), c = f.counts;
    trSave('reqin-project-state.json', JSON.stringify(f, null, 2), 'application/json');
    this.setState({ keepMsg: { bad: false, text: 'Saved reqin-project-state.json: ' + persistSaid(c, ['decisions', 'signoffs', 'events']) + '.', notes: [] }, events: this.keepEvent(S, 'Saved the project state to a file (' + persistSaid(c, ['decisions', 'signoffs']) + ')') });
  }
  keepPick(S, e) {
    const f = e && e.target && e.target.files && e.target.files[0];
    if (!f) return;
    const done = (text) => this.keepRead(text, f.name);
    if (f.size > PERSIST_MAX) { this.setState({ keepMsg: { bad: true, text: f.name + ' is larger than ' + PERSIST_MAX / 1048576 + ' MB, which is more than this app writes. It was not loaded.', notes: [] }, keepAsk: '' }); return; }
    try { const rd = new FileReader(); rd.onload = () => done(String(rd.result)); rd.onerror = () => done(''); rd.readAsText(f); } catch (x) { done(''); }
    try { e.target.value = ''; } catch (x) { /* the next pick of the same file still works in most browsers */ }
  }
  /* parse, check, then try to draw every screen with it; only then ask the person to replace their work */
  keepRead(text, name) {
    let obj = null;
    try { obj = JSON.parse(text); } catch (x) { this.setState({ keepMsg: { bad: true, text: name + ' is not a saved project: it is not valid JSON.', notes: [] }, keepAsk: '' }); return; }
    const r = persistCheck(obj);
    if (!r.ok) { this.setState({ keepMsg: { bad: true, text: name + ' was not loaded. ' + r.problems[0], notes: r.problems.slice(1) }, keepAsk: '' }); return; }
    const probe = this.keepProbe(r.state);
    if (probe) { this.setState({ keepMsg: { bad: true, text: name + ' was not loaded. ' + probe, notes: [] }, keepAsk: '' }); return; }
    this._pending = { state: r.state, name, saved: r.saved, counts: r.counts, notes: r.notes };
    const c = r.counts;
    this.setState({ keepAsk: 'load', keepMsg: null, keepSummary: [name + (r.saved ? ', saved ' + r.saved.replace('T', ' ').slice(0, 16) : ''), persistSaid(c, ['decisions', 'signoffs', 'handoffs', 'labels', 'events']), this.aiSaid(r.state)].concat(r.notes) });
  }
  /* the AI switch and data sheet a saved project would put in place, said in one line before anything is replaced */
  aiSaid(st) {
    const sh = st.aiSheet || DEFAULTS.aiSheet, on = st.aiOn === undefined ? DEFAULTS.aiOn : st.aiOn;
    return 'AI use: ' + (on ? 'on' : 'switched off') + '; ' + sh.model + ' ' + AI_WHERE_NAME[sh.where].toLowerCase() + ', approves ' + AI_LEVEL_SHORT[sh.approved] + '; ' + (aiReviewed(sh) ? 'sheet reviewed by ' + sh.reviewed_by : 'sheet not reviewed');
  }
  keepProbe(loaded) {
    const base = {}; PERSIST_KEYS.forEach((k) => { base[k] = DEFAULTS[k]; });
    // every screen once, then the review screen for each cluster the file says something about and the requirement screen for each requirement it decided
    const cids = new Set(), rids = Object.keys(loaded.rdec || {});
    PERSIST_BY_CLUSTER.forEach((k) => Object.keys(loaded[k] || {}).forEach((id) => { const c = String(id).split(':')[0]; if (persistHas(CL_BY, c)) cids.add(c); }));
    const spread = (list) => (list.length <= PERSIST_PROBE ? list : Array.from({ length: PERSIST_PROBE }, (x, i) => list[Math.round(i * (list.length - 1) / (PERSIST_PROBE - 1))]));   // an even spread, first and last included: a full draw of 250 clusters would take seconds
    const tries = ['home', 'review', 'explorer', 'results', 'vee', 'export', 'audit', 'gold', 'methods', 'policy', 'ai', 'overview'].map((view) => ({ view }))
      .concat(spread([...cids]).map((id) => ({ view: 'review', selected: id, qTab: 'all' }))).concat(spread(rids).map((id) => ({ view: 'explorer', xPick: id })));
    for (const extra of tries) {
      try { const t = new this.constructor(this.props); t._dry = true; t.state = Object.assign({}, t.state, base, loaded, extra); t.renderVals(); }
      catch (x) { return 'Its contents do not fit this project (the ' + extra.view + ' screen' + (extra.selected ? ' for ' + extra.selected : extra.xPick ? ' for ' + extra.xPick : '') + ' could not be drawn: ' + String(x && x.message).slice(0, 80) + ').'; }
    }
    return '';
  }
  keepApply(S) {
    const p = this._pending; if (!p) return;
    const merged = {}; PERSIST_KEYS.forEach((k) => { merged[k] = DEFAULTS[k]; });
    Object.assign(merged, p.state);
    merged.openVer = Object.assign({}, merged.liveVer);
    const c = p.counts, P = PEOPLE.find((x) => x.k === merged.person) || PEOPLE[0];
    merged.events = this.mk(merged.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Loaded saved work from ' + p.name + ' (' + persistSaid(c, ['decisions', 'signoffs']) + ')', 'Project state');
    this._pending = null; this._keepRaw = '';
    this.setState(Object.assign(merged, { view: 'home', verified: '', tamper: false, chatOpen: false, keepAsk: '', keepSummary: [], keepRestored: null, keepMsg: { bad: false, text: 'Loaded ' + p.name + '. Your earlier work in this browser was replaced.', notes: p.notes } }));
  }
  keepStartOver() {
    const reset = {}; PERSIST_KEYS.forEach((k) => { reset[k] = DEFAULTS[k]; });
    persistClear(); this._keepRaw = ''; this._pending = null;
    this.setState(Object.assign(reset, { view: 'open', verified: '', tamper: false, chatOpen: false, keepAsk: '', keepSummary: [], keepAt: '', keepRestored: null, keepMsg: { bad: false, text: 'Started over. The work kept in this browser was removed.', notes: [] } }));
  }
  valsKeep(S) {
    const work = persistHasWork(S), off = S.keepStatus === 'off', full = S.keepStatus === 'full', other = S.keepStatus === 'other', c = persistCounts(S);
    const at = S.keepAt ? S.keepAt.replace('T', ' ').slice(11, 19) : '';
    const line = other ? 'Another tab of this browser saved or removed work for this project. This tab has stopped saving so it cannot write over that. Choose whose work stands.'
      : off ? 'This browser is not letting the page keep anything (a private window, or storage is blocked). Save a file before you close the tab.'
      : full ? 'Your work is too large to keep in this browser. Save a file.'
      : work ? 'Kept automatically' + (at ? ' at ' + at : '') + ': ' + persistSaid(c, ['decisions', 'signoffs', 'handoffs', 'labels']) + '.'
      : 'Decide a cluster or a requirement and it is kept here by itself.';
    const msg = S.keepMsg;
    return {
      kHead: other ? 'Another tab changed this project' : off ? 'Your work is not being kept' : full ? 'Your work is too large to keep here' : 'Your work', kLine: line,
      kOther: other, kTake: () => this.keepTakeOther(), kMine: () => this.keepKeepMine(),
      kRestored: !!S.keepRestored, kRestoredText: S.keepRestored ? 'Picked up where you left off. This was saved ' + (S.keepRestored.at ? S.keepRestored.at.replace('T', ' ').slice(0, 16) : 'earlier') + ' in this browser.' : '',
      kWarn: off || full || other, kWarnText: other ? 'This tab is not saving.' : 'Nothing is being kept for you right now.', kScope: 'It stays in this browser and is not encrypted, so a colleague on another computer does not see it. On a shared computer, start over when you finish. Sharing between people needs the server, which this prototype is not connected to.',
      kSave: () => this.keepSave(S), kLoad: () => { try { document.getElementById('keep-file').click(); } catch (x) { /* no DOM */ } }, kFile: (e) => this.keepPick(S, e),
      kStart: () => this.setState({ keepAsk: 'start', keepMsg: null }),
      kAskStart: S.keepAsk === 'start', kAskLoad: S.keepAsk === 'load', kSummary: (S.keepSummary || []).map((t) => ({ t })),
      kDoStart: () => this.keepStartOver(), kDoLoad: () => this.keepApply(S), kCancel: () => { this._pending = null; this.setState({ keepAsk: '', keepSummary: [] }); },
      kHasMsg: !!msg, kMsgText: msg ? msg.text : '', kMsgBad: !!(msg && msg.bad), kMsgNotes: msg ? (msg.notes || []).map((t) => ({ t })) : [], kMsgStyle: 'font-size:13px;display:flex;flex-direction:column;gap:2px;border-radius:6px;padding:8px 12px;' + (msg && msg.bad ? 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;' : 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;'),
      kStartDisabled: !work && !S.keepRestored
    };
  }
