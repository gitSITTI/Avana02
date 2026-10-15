  /* ----- label pairs: the gold set (rules in gold.js) ----- */
  goldPatch(S, patch, extra) { this.setState(Object.assign({ gold: Object.assign({}, S.gold, patch) }, extra || {})); }
  goldFocus(id) { setTimeout(() => { try { const e = document.getElementById(id); if (e) e.focus(); } catch (x) { /* no DOM */ } }, 60); }
  goldFirst(name) { return String(name || '').split(' ')[0]; }
  goldNameOf(k) { const p = PEOPLE.find((x) => x.k === k); return p ? this.goldFirst(p.name) : k; }
  goldCurrent(S) {
    const plan = goldPlan(), g = S.gold, queue = goldQueue(S, S.person);
    const redo = g.redo && plan.by[g.redo] ? plan.by[g.redo] : null;
    return { it: redo || queue[0] || null, redo, queue };
  }
  goldPick(S, v) {
    if (!this.canAct(S)) return;
    const g = S.gold, who = S.person, cur = this.goldCurrent(S), it = cur.it;
    if (!it) return;
    const entry = { v, note: (g.note || '').trim(), t: TODAY };
    const labels = Object.assign({}, g.labels, { [it.key]: Object.assign({}, g.labels[it.key] || {}, { [who]: entry }) });
    const adj = Object.assign({}, g.adj); delete adj[it.key];          // a label that changes after a pair was settled sends it back to be checked
    this.goldPatch(S, { labels, adj, last: Object.assign({}, g.last, { [who]: it.key }), note: '', redo: '', status: 'Saved “' + GOLD_BY[v].name + '” for ' + it.a.id + ' and ' + it.b.id + '. The next pair is shown.' });
    this.goldFocus('gl-pair-h');
  }
  goldSkip(S) {
    const g = S.gold, who = S.person, it = this.goldCurrent(S).it;
    if (!it || !this.canAct(S)) return;
    const mine = (g.skip[who] || []).filter((k) => k !== it.key).concat([it.key]);
    this.goldPatch(S, { skip: Object.assign({}, g.skip, { [who]: mine }), redo: '', status: 'Skipped. It will come back after the others.' });
    this.goldFocus('gl-pair-h');
  }
  goldUndo(S) {
    const g = S.gold, who = S.person, key = g.last[who];
    if (!key || !this.canAct(S)) return;
    const L = Object.assign({}, g.labels[key] || {}); delete L[who];
    const labels = Object.assign({}, g.labels); if (Object.keys(L).length) labels[key] = L; else delete labels[key];
    this.goldPatch(S, { labels, last: Object.assign({}, g.last, { [who]: '' }), redo: '', status: 'Removed your last label. That pair is back in your queue.' });
    this.goldFocus('gl-pair-h');
  }
  goldKey(S, e) {
    if (!this.canAct(S) || !e || !e.key || e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target && e.target.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;     // keys typed in the note box are not shortcuts
    const q = '123456'.indexOf(e.key);
    if (q >= 0 && q < GOLD_REL.length) { e.preventDefault(); this.goldPick(S, GOLD_REL[q].k); }
  }
  goldSettle(S, key, v) {
    const P = this.person(S);
    if (P.role !== 'lead' || !this.canAct(S)) return;
    const it = goldPlan().by[key], g = S.gold;
    this.goldPatch(S, { adj: Object.assign({}, g.adj, { [key]: { v, by: P.name, note: '' } }) },
      { events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Lead'), 'Settled a labelling disagreement on ' + key.replace('|', ' and ') + ' as “' + GOLD_BY[v].name + '”', it && it.a.cid ? it.a.cid : 'Gold set') });
  }
  goldLoadSample(S) {
    const lab = goldSampleLabels(), g = S.gold, labels = Object.assign({}, g.labels);
    let n = 0;
    Object.keys(lab).forEach((k) => { labels[k] = Object.assign({}, labels[k] || {}, lab[k]); n += Object.keys(lab[k]).length; });
    const P = this.person(S);
    this.goldPatch(S, { labels, status: 'Loaded ' + n + ' sample labels.' }, { events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Loaded ' + n + ' sample labels into the gold set (demonstration only)', 'Gold set') });
  }
  goldRemoveSample(S) {
    const g = S.gold, labels = {};
    Object.keys(g.labels).forEach((k) => {
      const keep = {}; Object.keys(g.labels[k]).forEach((w) => { if (!g.labels[k][w].sample) keep[w] = g.labels[k][w]; });
      if (Object.keys(keep).length) labels[k] = keep;
    });
    const adj = {}; Object.keys(g.adj).forEach((k) => { if (labels[k]) adj[k] = g.adj[k]; });
    this.goldPatch(S, { labels, adj, status: 'Removed the sample labels.' });
  }
  goldClearMine(S) {
    const g = S.gold, who = S.person, labels = {};
    Object.keys(g.labels).forEach((k) => {
      const keep = Object.assign({}, g.labels[k]); delete keep[who];
      if (Object.keys(keep).length) labels[k] = keep;
    });
    this.goldPatch(S, { labels, last: Object.assign({}, g.last, { [who]: '' }), skip: Object.assign({}, g.skip, { [who]: [] }), redo: '', status: 'Removed your labels.' });
  }
  goldDownload(S) {
    const f = goldFile(S), P = this.person(S);
    try {
      const b = new Blob([JSON.stringify(f, null, 2)], { type: 'application/json' }), a = document.createElement('a');
      a.href = URL.createObjectURL(b); a.download = 'gold-set.json'; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    } catch (x) { /* no DOM */ }
    this.goldPatch(S, { status: 'Prepared gold-set.json with ' + f.pairs.length + ' pairs.' }, { events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Exported the gold set (' + f.pairs.length + ' labelled pairs)', 'Gold set') });
  }
  valsGold(S) {
    const g = S.gold, who = S.person, P = this.person(S), act = this.canAct(S);
    const plan = goldPlan(), pop = goldPop(), U = goldUsable(S), cur = this.goldCurrent(S), it = cur.it;
    const mine = plan.items.filter((x) => goldLabelsOf(S, x.key)[who]);
    const mineN = mine.length, offered = mineN + cur.queue.length;
    const nf = (n) => n.toLocaleString('en-US');
    const plural = (n, w) => nf(n) + ' ' + w + (n === 1 ? '' : 's');
    const mark = g.labels && goldLabelsOf(S, it ? it.key : '')[who];
    const seg = (s) => (s.same ? 'color:#4F5B66;' : s.ghost ? 'padding:0 6px;border-radius:6px;border:1px dashed #7A8793;color:#5A6672;text-decoration:line-through;font-size:14px;' : CH_STYLE[s.kind] + 'padding:1px 7px;border-radius:6px;font-weight:600;');
    const bSegs = !it ? [] : g.diff ? compareRows(it.a.text, [it.b.text])[0].segs.map((s) => ({ t: s.t, style: seg(s) })) : [{ t: it.b.text, style: '' }];
    const opts = GOLD_REL.map((r, q) => {
      const on = !!mark && mark.v === r.k;
      return {
        name: r.name, help: r.help, key: String(q + 1), off: !act || !it, pick: () => this.goldPick(S, r.k),
        style: 'display:flex;gap:12px;align-items:flex-start;text-align:left;width:100%;min-height:52px;padding:8px 12px;border-radius:8px;cursor:' + (act ? 'pointer' : 'not-allowed') + ';border:1px ' + (r.k === 'unsure' ? 'dashed' : 'solid') + ' ' + (on ? 'var(--accent)' : '#7A8793') + ';background:' + (on ? 'color-mix(in srgb,var(--accent) 10%,#fff)' : '#FFFFFF') + ';color:var(--ink);font-family:inherit;font-size:14px;',
        keyStyle: 'flex:none;width:24px;height:24px;border-radius:6px;border:1px solid #7A8793;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:12px;background:#F4F6F8;margin-top:1px'
      };
    });
    const nSample = U.sample, total = Object.keys(S.gold.labels).reduce((s, k) => s + Object.keys(S.gold.labels[k]).length, 0);
    const sample = goldSampleLabels(), sampleN = Object.keys(sample).reduce((s, k) => s + Object.keys(sample[k]).length, 0);
    const ag = goldAgreement(S);
    const kword = (k) => (k === null ? '' : k < 0.4 ? 'weak' : k < 0.6 ? 'moderate' : k < 0.8 ? 'good' : 'very good');
    const agreeLine = !ag ? 'No pair has been labelled by two people yet. One pair in five is offered to a second person, and nobody sees another person’s label.'
      : this.goldNameOf(ag.a) + ' and ' + this.goldNameOf(ag.b) + ' both labelled ' + plural(ag.n, 'pair') + ' and agree on ' + ag.agree + ' (' + Math.round(ag.pct * 100) + ' percent). Agreement beyond chance (kappa) is ' + (ag.kappa === null ? 'not defined here' : ag.kappa.toFixed(2) + ', which is ' + kword(ag.kappa)) + '.' + (ag.kappa !== null && ag.kappa < 0.6 ? ' Below about 0.6 the descriptions of the labels need tightening before these labels are relied on.' : '');
    const disputes = goldDisputes(S).map((x) => {
      const L = goldLabelsOf(S, x.key), who2 = Object.keys(L).sort();
      const vals = who2.map((w) => L[w].v).filter((v, i, a) => v !== 'unsure' && a.indexOf(v) === i);
      return {
        pair: x.a.id + ' · ' + x.b.id, said: who2.map((w) => this.goldNameOf(w) + ': ' + GOLD_BY[L[w].v].name).join(' · '), canSettle: P.role === 'lead' && act,
        opts: vals.map((v) => ({ label: 'Settle as “' + GOLD_BY[v].name + '”', pick: () => this.goldSettle(S, x.key, v) }))
      };
    });
    const recent = mine.slice().reverse().slice(0, 5).map((x) => {
      const l = goldLabelsOf(S, x.key)[who];
      return { pair: x.a.id + ' · ' + x.b.id, label: GOLD_BY[l.v].name, aria: 'Change your label for ' + x.a.id + ' and ' + x.b.id, change: () => { this.goldPatch(S, { redo: x.key, status: '' }); this.goldFocus('gl-pair-h'); } };
    });
    const groups = GOLD_GROUPS.map((h) => ({
      name: GOLD_GROUP_NAME[h], N: nf(pop.N[h]), size: String(plan.size[h]), n: String(U.by[h].n), k: String(U.by[h].k),
      sub: { A: 'The app’s own suggestions.', B1: 'Text match or keyword overlap of ' + GOLD_BAND.toFixed(1) + ' or more: the near misses.', B2: 'The rest of the pairs inside one allocation.', C: 'The app never compares these.' }[h]
    }));
    const file = goldFile(S), json = JSON.stringify(file, null, 2).split('\n');
    const noPairMsg = !offered ? ['Nothing to label yet', 'No pairs are offered.'] : ['You have labelled every pair offered to you', 'Thank you. ' + plural(mineN, 'pair') + ' labelled by you. The pairs that two people labelled show up as agreement or as disagreements to settle.'];
    return {
      gSampleOn: nSample > 0, gSampleLine: nSample + ' of the ' + total + ' labels are made up for the demonstration. Remove them before you rely on any number.',
      gReadOnly: !act, gReadOnlyLine: P.role === 'observer' ? 'Observers can read the labels and the numbers but cannot label.' : 'You are previewing another lens, so labelling is switched off. Switch back to your own lens to label.',
      gHasPair: !!it, gNoPair: !it, gDoneTitle: noPairMsg[0], gDoneText: noPairMsg[1],
      gPairTitle: cur.redo ? 'Change your label for this pair' : 'Pair ' + (mineN + 1) + ' of ' + offered, gWho: act ? 'Labelling as ' + P.name : 'Not labelling',
      gA: it ? { id: it.a.id, alloc: it.a.alloc, text: it.a.text } : { id: '', alloc: '', text: '' },
      gB: it ? { id: it.b.id, alloc: it.b.alloc, segs: bSegs } : { id: '', alloc: '', segs: [] },
      gDiff: !!g.diff, gToggleDiff: () => this.goldPatch(S, { diff: !g.diff }),
      gOpts: opts, gNote: g.note || '', gOnNote: (e) => this.goldPatch(S, { note: e.target.value }),
      gSkip: () => this.goldSkip(S), gNoAct: !act || !it, gUndo: () => this.goldUndo(S), gNoUndo: !act || !g.last[who], gStatus: g.status || '',
      gOnKey: (e) => this.goldKey(S, e),
      gToMetrics: () => this.setState({ view: 'methods' }),
      gGroups: groups, gHowLine: 'The sample is ' + plan.items.length + ' pairs from ' + nf(pop.total) + ' in the project. Every group is a simple random sample, so stopping at any point still gives a fair sample of it.',
      gOffered: offered, gMineN: mineN, gBar: 'height:10px;background:#2A6FD6;border-radius:0 5px 5px 0;width:' + (offered ? Math.round((mineN / offered) * 100) : 0) + '%',
      gMineLine: 'You have labelled ' + plural(mineN, 'pair') + '. ' + plural(cur.queue.length, 'pair') + ' ' + (cur.queue.length === 1 ? 'is' : 'are') + ' still offered to you.',
      gAllLine: 'All labellers together: ' + plural(U.labelled, 'pair') + ' labelled, ' + nf(U.usable) + ' counted in the numbers, ' + nf(U.unsure) + ' left out as “Cannot tell” or unresolved, ' + plural(U.fineDisputed, 'disagreement') + ' to settle.',
      gAgreeLine: agreeLine, gHasDisputes: disputes.length > 0, gDisputeN: disputes.length, gDisputes: disputes,
      gSettleWho: P.role === 'lead' && act ? 'You settle these as the lead. Your choice is recorded with your name and joins the event chain.' : 'The lead (Morgan Hale) settles these. Until then a pair is left out of the numbers that need one answer.',
      gNoRecent: recent.length === 0, gRecent: recent,
      gFileLine: file.pairs.length ? plural(file.pairs.length, 'labelled pair') + ' with the text of both requirements, the label, who gave it and how the pair was drawn.' : 'Nothing to put in the file yet. Label a pair first.',
      gNoFile: file.pairs.length === 0, gDownload: () => this.goldDownload(S), gFilePreview: json.slice(0, 22).join('\n') + (json.length > 22 ? '\n …' : ''),
      gSampleN: sampleN, gLoadSample: () => this.goldLoadSample(S), gRemoveSample: () => this.goldRemoveSample(S), gClearMine: () => this.goldClearMine(S),
      gNoSample: nSample === 0, gNoMine: mineN === 0
    };
  }
  /* the table at the top of Methods and metrics: what the labels say, measured */
  valsGoldPanel(S) {
    const g = S.gold, U = goldUsable(S), M = goldMeasure(S), outside = goldOutside(S), nm = goldNaming(S);
    const f2 = (x) => x.toFixed(2), nf = (n) => n.toLocaleString('en-US'), pc = (x) => Math.round(x * 100) + '%';
    const posOf = (x) => 'left:calc(' + (Math.max(0, Math.min(1, x)) * 100).toFixed(1) + '% - 4px);';
    const rng = (lo, hi) => 'left:' + (lo * 100).toFixed(1) + '%;width:' + Math.max(1, (hi - lo) * 100).toFixed(1) + '%;';
    const need = (est) => est.missing.map((q) => GOLD_GROUP_NAME[est.cells[q].h] + ', ' + (est.cells[q].f ? 'pairs this method flags' : 'pairs it does not flag')).join('; ');
    const rows = M.rows.map((r) => {
      const e = r.est, haveP = e.p !== null, haveR = e.r !== null;
      return {
        name: r.name, sub: r.sub, flagged: nf(e.flagged),
        hasP: haveP, p: haveP ? f2(e.p) : '—', pRange: haveP ? f2(e.pLo) + ' to ' + f2(e.pHi) : '', pLine: haveP ? rng(e.pLo, e.pHi) : '', pDot: haveP ? posOf(e.p) : '',
        hasR: haveR, r: haveR ? f2(e.r) : '—', rRange: haveR ? f2(e.rLo) + ' to ' + f2(e.rHi) : '', rLine: haveR ? rng(e.rLo, e.rHi) : '', rDot: haveR ? posOf(e.r) : '',
        aria: r.name + ': ' + (haveP ? 'precision ' + f2(e.p) + ', range ' + f2(e.pLo) + ' to ' + f2(e.pHi) : 'precision not measured yet') + '; ' + (haveR ? 'recall ' + f2(e.r) + ', range ' + f2(e.rLo) + ' to ' + f2(e.rHi) : 'recall not measured yet') + '.',
        needs: e.missing.length > 0, needText: 'Not enough labels yet. Label pairs in: ' + need(e) + '.',
        wide: haveR && (e.rHi - e.rLo > 0.3 || (haveP && e.pHi - e.pLo > 0.3)), wideText: 'The range is wide. More labels in the near-miss and cluster groups will narrow it.'
      };
    });
    const pill = (on) => 'min-height:40px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#7A8793') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';color:#121820;';
    const cuts = GOLD_CUTS.map((c) => ({ label: c.toFixed(1), pressed: M.cut === c ? 'true' : 'false', style: pill(M.cut === c) + 'min-width:52px;', pick: () => this.goldPatch(S, { cut: c }) }));
    const outRows = outside.map((o) => ({
      name: o.name, N: nf(o.N), n: String(o.n), k: String(o.k),
      line: o.n ? o.k + ' of ' + o.n + ' labelled pairs were related, so up to ' + pc(o.hi) + ' of these pairs could be (a 95 percent range). ' + (o.hi > 0.05 ? 'Label more of them to narrow it.' : '') : 'No pair from this group has been labelled yet.'
    }));
    const nSample = U.sample;
    return {
      gmEmpty: U.usable === 0, gmHas: U.usable > 0,
      gmHead: U.usable === 0 ? 'No pair has been labelled yet, so nothing here is measured.' : 'Measured from ' + nf(U.usable) + ' labelled pairs.' + (nSample ? ' ' + nf(nSample) + ' of the labels behind them were made up for the demonstration.' : ''),
      gmSample: nSample > 0, gmRows: rows, gmCuts: cuts, gmCutLabel: M.cut.toFixed(1), gmOutside: outRows,
      gmNaming: nm.n > 0, gmNamingLine: 'Where the app suggested a cluster and people call the pair related, the AI named the relation the way people did for ' + nm.k + ' of ' + nm.n + ' pairs (' + pc(nm.p) + ', range ' + pc(nm.lo) + ' to ' + pc(nm.hi) + '). The AI verdicts in this sample are made up too.' + (nm.held ? ' ' + nm.held + (nm.held === 1 ? ' pair is' : ' pairs are') + ' left out because the AI was not used on its group.' : ''),
      gmToLabel: () => this.setState({ view: 'gold' })
    };
  }
