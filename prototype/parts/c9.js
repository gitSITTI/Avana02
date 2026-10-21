  /* ----- the shared project: sign in to the reference server, send changes, take in other people's (the rules and the checks are in connect.js) ----- */
  connOrigin() { try { return /^https?:$/.test(window.location.protocol) ? window.location.origin : ''; } catch (x) { return ''; } }
  connSignedIn(S) { return !!this._conn && ['live', 'offline', 'denied', 'rolledback'].indexOf((S.conn || {}).status) >= 0; }
  connClock() { return new Date().toTimeString().slice(0, 8); }
  connUi(patch) { const S = this.S; super.setState({ conn: Object.assign({}, DEFAULTS.conn, S.conn, patch) }); }
  connFail(text) { this.connUi({ status: 'off', msg: text, bad: true }); }
  /* the people of the project replace the page's sample people for as long as the person is signed in */
  connValidPeople(list, me) {
    if (!Array.isArray(list) || !list.length || list.length > 200) return 'The server did not list the people of this project.';
    const ok = list.every((p) => p && typeof p.key === 'string' && /^[a-z][a-z0-9_-]{0,31}$/.test(p.key) && typeof p.name === 'string' && p.name.trim() && p.name.length <= 80 && ROLE_NAME[p.role] !== undefined && (p.lens === '' || LENSES.some((l) => l.k === p.lens)) && (p.role === 'observer') === (p.lens === ''));
    if (!ok) return 'The server’s list of people is not in a shape this page reads.';
    const mine = list.find((p) => p.key === me.key);
    if (!mine || mine.role !== me.role || mine.lens !== me.lens) return 'The server’s list of people does not agree with who your token is for.';
    return '';
  }
  async connSignIn() {
    const S = this.S, token = String(S.connToken || '').trim();
    if (this._connBusy || this._conn) return;
    const origin = this.connOrigin();
    if (!token) { this.connFail('Paste the token you were given, then sign in.'); return; }
    if (!origin) { this.connFail('This page was not opened from a server, so there is nothing to sign in to. Open it from the address the person who runs the server gave you; it ends in /app/.'); return; }
    this._connBusy = true;
    this.connUi({ status: 'signing', msg: 'Signing in…', bad: false });
    try {
      const api = connApi((u, o) => fetch(u, o), origin, token);
      const me = await api.me();
      if (me.status === 0) { this.connFail('Could not reach the server at ' + origin + '. Check that it is running and that this page was opened from it.'); return; }
      if (me.status === 401) { this.connFail('That token is not recognised. Check that it was copied whole, or ask for a new one.'); return; }
      if (me.status !== 200 || !me.body || typeof me.body.key !== 'string' || typeof me.body.project !== 'string') { this.connFail('That address did not answer like a reqin server (it said ' + me.status + '). Open this page from the server’s own /app/ address.'); return; }
      const pp = await api.people(me.body.project);
      const bad = pp.status === 200 && pp.body ? this.connValidPeople(pp.body.people, me.body) : 'Could not read the people of the project (' + pp.status + ').';
      if (bad) { this.connFail(bad); return; }
      const before = {}; CONN_STATE_KEYS.concat(CONN_DRAFT_KEYS).forEach((k) => { before[k] = S[k]; });
      const peopleBefore = PEOPLE.slice();
      const ctx = connNew(api, me.body.project, me.body, this.connHooks());
      ctx.people = pp.body.people;
      let r;
      try { r = await connLoad(ctx); } catch (x) { PEOPLE.length = 0; peopleBefore.forEach((p) => PEOPLE.push(p)); throw x; }
      if (!r.ok) { this.connFail(r.problem); return; }
      this._conn = ctx; this._connBefore = before; this._peopleBefore = peopleBefore; this._connBy = {};
      clearTimeout(this._keepT); this._keepHold = true;      // while connected this browser keeps no copy: the server has the one
      super.setState({ connToken: '', conn: Object.assign({}, DEFAULTS.conn, { status: 'live', project: me.body.project, me: me.body.key, at: this.connClock(), pending: 0, msg: 'Signed in as ' + me.body.name + '.', bad: false, left: r.bad.length,
        notices: r.bad.slice(0, 5).map((b) => ({ kind: 'ignored', at: this.connClock(), text: connName(b.id) + ' on the server was left out because ' + b.why + '.' })) }) });
      this.connSchedule();
    } catch (x) {
      this.connFail('Signing in did not work: ' + String(x && x.message).slice(0, 120));
    } finally { this._connBusy = false; }
  }
  connSignOut(msg) {
    const ctx = this._conn; if (!ctx) return;
    clearTimeout(this._connT); clearTimeout(this._connF);
    this._conn = null; this._keepHold = false; this._keepRaw = '';
    PEOPLE.length = 0; this._peopleBefore.forEach((p) => PEOPLE.push(p));
    const back = Object.assign({}, this._connBefore);
    this._connBefore = null;
    super.setState(Object.assign(back, { preview: '', conn: Object.assign({}, DEFAULTS.conn, { msg: msg || 'Signed out. This page is showing the work kept in this browser again.', bad: false }) }));
    this.keepSoon();
  }
  connHooks() {
    const self = this;
    return {
      getS: () => self.S,
      swapPeople: (list) => { PEOPLE.length = 0; list.forEach((p) => PEOPLE.push({ k: p.key, name: p.name, lens: p.lens, role: p.role })); },
      replace: (patch, me) => super.setState(Object.assign({}, patch, { person: me.key, preview: '', events: self.connAiEvents(Object.assign({}, self.S, patch), patch) })),
      apply: (changes) => {
        const S = self.S, patch = connApply(S, changes), me = self._conn ? self._conn.me.key : '';
        const lv = {};
        changes.forEach((c) => { if (!c.by || c.by === me) return; const pl = connPlace(c.id); const cid = pl && pl.path[0]; if (pl && pl.k && CL_BY[cid]) { lv[cid] = (S.liveVer[cid] || 0) + 1; self._connBy[cid] = connWho(c.by); } });
        if (Object.keys(lv).length) patch.liveVer = Object.assign({}, S.liveVer, lv);
        const ai = changes.find((c) => c.id === 'proj/ai');
        if (ai) patch.events = self.connAiEvents(Object.assign({}, S, patch), patch, ai.by);
        super.setState(patch);
      },
      notice: (n) => { const S = self.S; super.setState({ conn: Object.assign({}, DEFAULTS.conn, S.conn, { notices: [Object.assign({ at: self.connClock() }, n)].concat((S.conn || {}).notices || []).slice(0, 20) }) }); },
      status: (s, pending) => { const S = self.S; if (!self._conn) return; self.connUi({ status: s, pending: pending || 0, at: s === 'live' ? self.connClock() : (S.conn || {}).at, msg: s === 'denied' ? 'The server no longer accepts your token. Sign in again with a current one.' : s === 'rolledback' ? 'The server’s record is shorter than, or different from, the one this page saw a moment ago. Nothing more is sent or read. Tell the person who runs the server.' : (S.conn || {}).msg, bad: s === 'denied' || s === 'rolledback' }); },
      activity: (evs) => { const S = self.S; const add = evs.filter((e) => e.type === 'doc').map((e) => ({ seq: e.seq, who: connWho(e.actor), text: e.text, at: String(e.at).replace('T', ' ').slice(11, 19) })).reverse(); super.setState({ conn: Object.assign({}, DEFAULTS.conn, S.conn, { activity: add.concat((S.conn || {}).activity || []).slice(0, 8) }) }); }
    };
  }
  /* the page's own record of AI use has to say what the switch and the sheet say, or a saved file would be refused: after a change that came from the server, say so in it */
  connAiEvents(S, patch, by) {
    if (patch.aiOn === undefined && patch.aiSheet === undefined) return S.events;
    let ev = S.events;
    const want = aiFromEvents(ev), on = patch.aiOn === undefined ? S.aiOn : patch.aiOn, sh = patch.aiSheet || S.aiSheet, actor = by ? connWho(by) + ' · shared project' : 'Shared project';
    if (want.on !== on) ev = this.mk(ev, 'human', actor, 'AI use switched ' + (on ? 'on' : 'off') + ' for the whole project (as the shared project has it)', 'AI use');
    if (want.fp !== aiSheetFp(sh)) ev = this.mk(ev, 'human', actor, 'AI data sheet set to what the shared project has [sheet ' + aiSheetFp(sh) + ']', 'AI use');
    return ev;
  }
  connSchedule() {
    clearTimeout(this._connT);
    const ctx = this._conn; if (!ctx || typeof setTimeout === 'undefined') return;
    const ms = (typeof window !== 'undefined' && window.__reqinPollMs) || CONN_POLL_MS;
    this._connT = setTimeout(() => this.connTick(ctx), ms);
  }
  async connTick(ctx) {
    if (this._conn !== ctx) return;
    let stop = false;
    try {
      stop = ['denied', 'rolledback'].indexOf((this.S.conn || {}).status) >= 0;
      if (!stop) await connFlush(ctx);
      if (this._conn !== ctx) return;
      stop = ['denied', 'rolledback'].indexOf((this.S.conn || {}).status) >= 0;
      if (!stop) await connPoll(ctx);
    } catch (x) { if (this._conn === ctx) this.connUi({ status: 'offline' }); }
    if (this._conn === ctx && ['denied', 'rolledback'].indexOf((this.S.conn || {}).status) < 0) this.connSchedule();
  }
  /* a change was made here: send it in a moment, once the person has stopped typing */
  connSoon() {
    const ctx = this._conn;
    if (!ctx || this._dry || typeof setTimeout === 'undefined') return;
    clearTimeout(this._connF);
    this._connF = setTimeout(() => { if (this._conn === ctx) connFlush(ctx).catch(() => { if (this._conn === ctx) this.connUi({ status: 'offline' }); }); }, 120);
  }
  connWake() { const ctx = this._conn; if (ctx && this._connT) { clearTimeout(this._connT); this._connT = setTimeout(() => this.connTick(ctx), 50); } }
  async connCheckNow() {
    const ctx = this._conn; if (!ctx || this._connChecking) return;
    this._connChecking = true;
    this.connUi({ record: { busy: true, ok: false, text: 'Asking the server to recompute its record…' } });
    try {
      const r = await connCheckRecord(ctx);
      if (this._conn === ctx) this.connUi({ record: { busy: false, ok: r.ok, text: r.text } });
    } catch (x) { if (this._conn === ctx) this.connUi({ record: { busy: false, ok: false, text: 'The check did not finish: ' + String(x && x.message).slice(0, 100) } }); }
    finally { this._connChecking = false; }
  }
  valsConn(S) {
    const c = Object.assign({}, DEFAULTS.conn, S.conn), signed = this.connSignedIn(S), origin = this.connOrigin();
    const stName = { live: 'Live', offline: 'Offline', denied: 'Signed out by the server', rolledback: 'Stopped' }[c.status] || '';
    const P = this.person(S), pend = c.pending || 0;
    const line = c.status === 'live' ? 'Everyone who signs in to ' + c.project + ' sees the same decisions, sign-offs, hand-offs and labels. Last checked ' + (c.at || 'just now') + (pend ? '; ' + pend + (pend === 1 ? ' change is' : ' changes are') + ' being sent.' : '; nothing is waiting to be sent.')
      : c.status === 'offline' ? 'The server cannot be reached. ' + (pend ? pend + (pend === 1 ? ' change is' : ' changes are') + ' waiting here and will be sent when it can.' : 'Nothing is waiting.') + ' What you see is what the server last said.'
      : c.status === 'denied' ? 'The server no longer accepts your token. Nothing more is sent or read.'
      : c.status === 'rolledback' ? 'The record on the server looks shorter or different than a moment ago. Nothing more is sent or read.' : '';
    const kindWord = { conflict: 'Not made: someone got there first', refused: 'Not made: the server’s rules', cleared: 'Cleared', ignored: 'Left out' };
    return {
      cnSigned: signed, cnAlone: !signed && c.status !== 'signing', cnSigning: c.status === 'signing', cnCanTry: !!origin && c.status !== 'signing',
      cnHead: signed ? 'Shared with your team: ' + c.project : 'Work with your team on a shared server',
      cnLine: line, cnStatus: stName, cnStatusStyle: 'font-size:12px;font-weight:600;padding:2px 10px;border-radius:999px;white-space:nowrap;' + (c.status === 'live' ? 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;' : 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;'),
      cnWhoCardOn: signed && S.view !== 'open', cnWho: signed ? P.name + ' · ' + (P.lens ? SLOT_NAME[P.lens] + ' lens' : 'no lens') + ' · ' + ROLE_NAME[P.role] : '',
      cnIntro: 'This page is working on its own: what you decide is kept in this browser and nobody else sees it. If your team runs the reference server, paste the token you were given and everyone works on one copy. A token is a password for one person: it decides your lens and what you may change. It is kept in this page only until you close it.',
      cnOrigin: origin ? 'Server: ' + origin : 'This page was not opened from a server, so it cannot sign in. Open it from the address the person who runs the server gave you; it ends in /app/.',
      cnToken: S.connToken || '', cnTokenChange: (e) => this.setState({ connToken: e.target.value }),
      cnTokenKey: (e) => { if (e.key === 'Enter') { e.preventDefault(); this.connSignIn(); } },
      cnSignIn: () => this.connSignIn(), cnSignOut: () => this.connSignOut(), cnCheck: () => this.connCheckNow(),
      cnMsg: c.msg, cnHasMsg: !!c.msg, cnMsgStyle: 'font-size:13px;border-radius:6px;padding:8px 12px;font-weight:600;' + (c.bad ? 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;' : 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;'),
      cnNotices: (c.notices || []).map((n, i) => ({ head: kindWord[n.kind] || 'Note', text: n.text, at: n.at || '', hasDetail: !!n.mine, mine: 'You: ' + (n.mine || ''), theirs: 'Now: ' + (n.theirs || ''), dismiss: () => { const cur = (this.S.conn || {}).notices || []; this.connUi({ notices: cur.filter((x, j) => j !== i) }); },
        style: 'border-radius:8px;padding:10px 14px;display:flex;flex-direction:column;gap:4px;font-size:13px;' + (n.kind === 'cleared' || n.kind === 'ignored' ? 'background:#FFF7E6;border:1px solid #A15C00;' : 'background:#FDE3E0;border:1px solid #A6261E;') })),
      cnNotesInCard: (c.notices || []).length > 0 && S.view === 'open', cnNotesInShell: (c.notices || []).length > 0 && S.view !== 'open',
      cnActivity: (c.activity || []).map((a) => ({ at: a.at, who: a.who, text: a.text })), cnHasActivity: (c.activity || []).length > 0,
      cnRecordOn: !!c.record, cnRecordText: c.record ? c.record.text : '', cnRecordOk: !!(c.record && c.record.ok), cnRecordBusy: !!(c.record && c.record.busy),
      cnRecordStyle: 'font-size:13px;border-radius:6px;padding:8px 12px;font-weight:600;' + (c.record && c.record.ok ? 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;' : c.record && c.record.busy ? 'background:#F1F6FF;color:#10337F;border:1px solid var(--accent);' : 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;'),
      cnCheckDisabled: !signed || !!(c.record && c.record.busy),
      cnShort: signed ? (c.status === 'live' ? 'Shared · live' : c.status === 'offline' ? 'Shared · offline' + (pend ? ', ' + pend + ' waiting' : '') : 'Shared · stopped') : 'Not shared · this browser only',
      cnShortStyle: 'font-size:12px;font-weight:600;padding:2px 10px;border-radius:999px;white-space:nowrap;' + (!signed ? 'background:#EEF2F6;color:#3C4852;' : c.status === 'live' ? 'background:#E1F2E7;color:#14502B;' : 'background:#FDE3E0;color:#7A1510;'),
      cnHint: signed ? 'Your login decides your lens.' : 'Your login decides your lens. Not signed in to a server, you can switch person to see each view.',
      cnDemo: !signed
    };
  }
