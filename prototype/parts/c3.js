  /* ----- all requirements: map, table, one requirement ----- */
  reqState(S, r) {
    const own = rdStatus(S, r);   // a requirement decided on its own is shown by how far that decision has got
    if (own) return own === 'approved' ? 'approved' : 'review';
    if (!r.cid) return 'alone';
    const st = statusOf(S, CL_BY[r.cid]);
    return st === 'approved' ? 'approved' : st === 'review' || st === 'decided' ? 'review' : attention(st) ? 'attn' : 'open';
  }
  /* a click on the map or the list picks the requirement to look at; while a person is choosing the second one it puts that one beside the first */
  xPickReq(S, id) {
    if (S.rpick && S.xPick && id !== S.xPick) this.setState({ rcmp: id, rpick: false });
    else this.setState({ xPick: id });
  }
  valsExplorer(S) {
    const U = universe(S), P = this.person(S);
    const SQ = 'width:10px;height:10px;border-radius:2px;display:inline-block;box-sizing:border-box;flex:none;';
    const STY = {
      alone: ['Alone · nothing similar found', SQ + 'border:2px solid #7B8792;background:transparent', '#7B8792'],
      open: ['In a cluster · needs a decision', SQ + 'background:#4F8FE6', '#4F8FE6'],
      review: ['Decided · collecting sign-offs', SQ + 'background:#1C5CAB', '#1C5CAB'],
      approved: ['Approved', SQ + 'background:#1B6B3A', '#1B6B3A'],
      attn: ['Needs attention · stale, disagreement or too big', SQ + 'background:repeating-linear-gradient(45deg,#C47A00 0 3px,#FFE3B8 3px 5px)', '#C47A00']
    };
    const stateOf = {}; U.reqs.forEach((r) => { stateOf[r.id] = this.reqState(S, r); });
    const meSet = new Set(); this.allInfos(S).forEach((x) => { if (x.me) x.c.members.forEach((m) => meSet.add(m.id)); });
    const chipStyle = (on) => 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#7A8793') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';';
    const isGap = (r) => { const v = VREQ[r.id]; return !(v.vm && v.vi > 0); };
    const matches = (r) => (S.xFilter === 'all' ? true : S.xFilter === 'mine' ? meSet.has(r.id) : stateOf[r.id] === S.xFilter) && (!S.xAlloc || r.alloc === S.xAlloc) && (!S.xLvl || VREQ[r.id].lvl === S.xLvl) && (!S.xGap || isGap(r));
    const counts = { all: U.reqs.length, alone: 0, open: 0, review: 0, approved: 0, attn: 0 };
    U.reqs.forEach((r) => { counts[stateOf[r.id]]++; });
    const fdefs = [['all', 'All'], ['mine', 'For me'], ['open', 'Needs a decision'], ['review', 'In review'], ['approved', 'Approved'], ['attn', 'Needs attention'], ['alone', 'Alone']];
    const chips = fdefs.map(([k, label]) => ({ label, count: k === 'mine' ? meSet.size : counts[k], pressed: S.xFilter === k ? 'true' : 'false', pick: () => this.setState({ xFilter: k, xPage: 0 }), style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (S.xFilter === k ? 600 : 500) + ';border:1px solid ' + (S.xFilter === k ? 'var(--accent)' : '#7A8793') + ';background:' + (S.xFilter === k ? '#E8F0FD' : '#FFFFFF') + ';' }));
    const groups = ALLOCS.filter((a) => S.scope === 'all' || a.k === S.scope).map((a) => {
      const rs = U.reqs.filter((r) => r.alloc === a.k);
      return {
        name: a.k, count: rs.length, on: S.xAlloc === a.k, pressed: S.xAlloc === a.k ? 'true' : 'false', pick: () => this.setState({ xAlloc: S.xAlloc === a.k ? '' : a.k, xPage: 0 }),
        cells: rs.map((r) => { const s = stateOf[r.id], hit = matches(r); return { title: r.id + ' · ' + STY[s][0], pick: () => this.xPickReq(S, r.id), style: STY[s][1].replace('display:inline-block', 'display:block') + ';cursor:pointer;flex:none;opacity:' + (hit ? 1 : 0.15) + (S.xPick === r.id ? ';outline:2px solid #12171C;outline-offset:2px' : '') }; })
      };
    });
    const legend = ['alone', 'open', 'review', 'approved', 'attn'].map((k) => ({ label: STY[k][0], shape: STY[k][1], n: counts[k] }));
    const alloc = ALLOCS.filter((a) => S.scope === 'all' || a.k === S.scope).map((a) => {
      const rs = U.reqs.filter((r) => r.alloc === a.k), n = (k) => rs.filter((r) => stateOf[r.id] === k).length;
      return { name: a.k, total: rs.length, alone: n('alone'), open: n('open'), review: n('review'), approved: n('approved'), attn: n('attn'), clusters: U.cl.filter((c) => c.alloc === a.k).length, pick: () => this.setState({ xAlloc: S.xAlloc === a.k ? '' : a.k, xPage: 0 }), rowStyle: 'display:grid;grid-template-columns:minmax(0,1.4fr) repeat(7,minmax(0,.7fr));gap:8px;padding:8px 16px;border-bottom:1px solid #E3E7EA;align-items:center;' + (S.xAlloc === a.k ? 'background:#F1F6FF;' : '') };
    });
    const list = U.reqs.filter(matches);
    const PAGE = 8, pages = Math.max(1, Math.ceil(list.length / PAGE)), page = Math.min(S.xPage, pages - 1);
    const rows = list.slice(page * PAGE, page * PAGE + PAGE).map((r) => ({ id: r.id, alloc: r.alloc, state: STY[stateOf[r.id]][0], shape: STY[stateOf[r.id]][1], cluster: r.cid || 'none', text: r.text, pick: () => this.xPickReq(S, r.id), on: S.xPick === r.id, style: 'text-align:left;display:grid;gap:10px;align-items:center;min-height:44px;padding:6px 12px;border-radius:6px;cursor:pointer;border:' + (S.xPick === r.id ? '2px solid var(--accent)' : '1px solid #D5DADE') + ';background:#FFFFFF;' }));
    const pk = S.xPick && REQ_BY[S.xPick] ? REQ_BY[S.xPick] : null;
    const pc = pk && pk.cid ? CL_BY[pk.cid] : null;
    return {
      xChips: chips, groups, legend, allocRows: alloc,
      xRows: rows, xInfo: list.length ? 'Showing ' + (page * PAGE + 1) + ' to ' + (page * PAGE + rows.length) + ' of ' + list.length.toLocaleString('en-US') : 'Nothing matches',
      xPageText: 'Page ' + (page + 1) + ' of ' + pages, xPrevDisabled: page === 0, xNextDisabled: page >= pages - 1,
      xPrev: () => this.setState({ xPage: Math.max(0, page - 1) }), xNext: () => this.setState({ xPage: Math.min(pages - 1, page + 1) }),
      xHasAlloc: !!S.xAlloc, xAllocName: S.xAlloc, xClearAlloc: () => this.setState({ xAlloc: '', xPage: 0 }),
      xLvlChips: [[0, 'All levels']].concat(VLEVELS.map((l) => [l.k, 'Level ' + l.k + ' · ' + l.short])).map(([k, label]) => ({ label, pressed: (S.xLvl || 0) === k ? 'true' : 'false', pick: () => this.setState({ xLvl: k, xPage: 0 }), style: chipStyle((S.xLvl || 0) === k) })),
      xGapPressed: S.xGap ? 'true' : 'false', xGapPick: () => this.setState({ xGap: !S.xGap, xPage: 0 }), xGapLabel: 'Verification gaps only', xGapStyle: chipStyle(!!S.xGap),
      xShowPick: !!pk, sp: this.valsSingle(S, pk),
      xp: pk ? {
        id: pk.id, vLine: (() => { const v = VREQ[pk.id], l = VLEVELS[v.lvl - 1]; return 'Level ' + v.lvl + ' · ' + l.short + '. Checked by ' + (v.vm ? v.vm.toLowerCase() : 'no method yet') + ' at ' + l.ver.toLowerCase() + ', ' + (v.vi ? v.vi + (v.vi === 1 ? ' verification item' : ' verification items') + ' linked' : 'no verification item linked') + '.'; })(), alloc: pk.alloc, owner: pk.owner, tok: paintOnly(pk.text), stateLabel: STY[stateOf[pk.id]][0], shape: STY[stateOf[pk.id]][1],
        inCluster: !!pc, clusterLine: pc ? pc.id + ' · ' + pc.title + ' · ' + STATUS_LABEL[statusOf(S, pc)] : 'Not in any cluster. Four methods compared it with every other requirement in its allocation and found nothing close.',
        open: pc ? () => this.setState({ view: 'review', selected: pc.id, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [pc.id]: S.liveVer[pc.id] || 0 }) }) : () => {},
        history: reqHistory(S, pk.id)
      } : { id: '', alloc: '', owner: '', tok: [], stateLabel: '', shape: '', inCluster: false, clusterLine: '', open: () => {}, history: [], vLine: '' }
    };
  }
  /* ----- the engineering V: levels on the left, what checks them on the right, and what your decisions do to the right leg ----- */
  valsVee(S, V) {
    V = V || veeOf(S, this.allInfos(S));
    const nf = (n) => n.toLocaleString('en-US'), pct = (a, b) => (b ? Math.round((a / b) * 100) : 100) + '%';
    const plural = (n, one, many) => nf(n) + ' ' + (n === 1 ? one : many || one + 's');
    const bar = (share, color) => 'height:10px;background:' + (color || '#2A6FD6') + ';border-radius:0 5px 5px 0;width:' + Math.max(share > 0 ? 2 : 0, Math.round(share * 100)) + '%';
    const maxM = (l) => Math.max(1, l.methods.Test, l.methods.Analysis, l.methods.Inspection, l.methods.Demonstration, l.methods.none);
    const rows = V.levels.map((l, i) => {
      const facts = [];
      if (l.open) facts.push(plural(l.open, 'cluster') + ' still to decide');
      if (l.dropped) facts.push(plural(l.dropped, 'requirement') + ' dropped or not a requirement');
      if (l.repoint) facts.push(plural(l.repoint, 'verification item') + ' to re‑point');
      if (l.recheck) facts.push(plural(l.recheck, 'verification item') + ' to read again against new wording');
      if (l.gaps) facts.push(plural(l.gaps, 'requirement') + ' without a method or an item');
      const state = l.state;
      const label = state === 'ok' ? 'In step' : state === 'attn' ? 'Needs attention' : 'Still being consolidated';
      const methods = VMETHODS.concat(['none']).map((k) => ({
        name: k === 'none' ? 'No method' : k, n: nf(l.methods[k]), isNone: k === 'none',
        bar: k === 'none' ? 'height:10px;border-radius:0 5px 5px 0;background:repeating-linear-gradient(45deg,#B35A00 0 3px,#FFD9A8 3px 5px);width:' + Math.max(l.methods[k] ? 2 : 0, Math.round((l.methods[k] / maxM(l)) * 100)) + '%' : bar(l.methods[k] / maxM(l))
      }));
      return {
        k: l.k, lname: l.name, ver: l.ver, how: l.how,
        aria: 'Level ' + l.k + '. ' + l.name + ' and ' + l.ver + '. ' + label + '.',
        lStyle: '--ind:' + i * 34 + 'px', rStyle: '--ind:' + i * 34 + 'px', gapStyle: '--ind:' + (i + 1) * 34 + 'px',
        reqs: nf(l.reqs), afterTxt: l.gone ? nf(l.after) + ' after your decisions (' + nf(Math.abs(l.gone)) + (l.gone > 0 ? ' fewer)' : ' more)') : 'None removed at this level so far',
        decBar: bar(l.decShare), decTxt: nf(l.decided) + ' of ' + nf(l.clusters) + ' clusters decided',
        hasOpen: l.open > 0, openTxt: 'Review the ' + nf(l.open) + ' open',
        review: () => this.setState({ view: 'review', qTab: 'all', qLvl: String(l.k), qStatus: 'undecided', qAlloc: '', qLane: '', qSearch: '', qPage: 0 }),
        reviewAria: 'Review the ' + l.open + ' open clusters at level ' + l.k + ', ' + l.name,
        crossTxt: l.cross ? plural(l.cross, 'cluster') + ' here hold a requirement and its parent. They can be linked, not merged.' : '',
        hasCross: l.cross > 0,
        methods, tracedTxt: nf(l.traced) + ' of ' + nf(l.reqs) + ' have a method and a verification item (' + pct(l.traced, l.reqs) + ')',
        traceBar: bar(l.traceShare, '#1B6B3A'), itemsTxt: plural(l.items, 'verification item') + ' linked',
        hasRepoint: l.repoint > 0, repointTxt: plural(l.repoint, 'verification item') + ' must move to the requirement that takes the place of the one removed' + (l.methodShift ? '. In ' + plural(l.methodShift, 'case') + ' the removed wording was verified a different way.' : '.') + (l.levelShift ? ' ' + plural(l.levelShift, 'item') + ' would land on a requirement at a different level.' : ''),
        hasGaps: l.gaps > 0, gapsAria: 'See the gaps: ' + l.gaps + (l.gaps === 1 ? ' requirement' : ' requirements') + ' at level ' + l.k + ' without a method or an item',
        gaps: () => this.setState({ view: 'explorer', xLvl: l.k, xGap: true, xFilter: 'all', xAlloc: '', xPage: 0, xPick: '' }),
        isPass: state === 'ok', isWarn: state === 'attn', isInfo: state === 'open', isFail: false,
        stateLabel: label, facts: facts.map((t) => ({ t })), hasFacts: facts.length > 0,
        tr: { lvl: l.k + ' · ' + l.short, now: nf(l.reqs), after: nf(l.after), dec: nf(l.decided) + ' of ' + nf(l.clusters), traced: nf(l.traced) + ' (' + pct(l.traced, l.reqs) + ')', gaps: nf(l.gaps), re: nf(l.repoint) }
      };
    });
    const tot = { lvl: 'All levels', now: nf(V.reqs), after: nf(V.after), dec: nf(V.decided) + ' of ' + nf(V.clusters), traced: nf(V.traced) + ' (' + pct(V.traced, V.reqs) + ')', gaps: nf(V.gaps), re: nf(V.repoint) };
    return {
      vRows: rows, vTable: rows.map((r) => r.tr), vTotal: tot, vGlyphPage: veeGlyph(V, [], true),
      vLeftBig: nf(V.decided) + ' of ' + nf(V.clusters), vLeftSub: nf(V.reqs) + ' requirements now, ' + nf(V.after) + ' after your decisions.' + (V.held ? ' ' + plural(V.held, 'more cluster has', 'more clusters have') + ' a stale or disputed decision, which does not count until it is settled.' : ''),
      vRightBig: nf(V.traced) + ' of ' + nf(V.reqs), vRightSub: plural(V.gaps, 'requirement') + ' with no method or no verification item (' + plural(V.noMethod, 'has', 'have') + ' no method, ' + nf(V.noItem) + ' no item)',
      vMidBig: nf(V.repoint), vMidSub: V.repoint ? (V.repoint === 1 ? 'verification item' : 'verification items') + ' must move to the requirement that takes the place of one removed, before export' + (V.methodShift ? '. In ' + plural(V.methodShift, 'case') + ' the removed wording was verified a different way.' : '.') + (V.levelShift ? ' ' + plural(V.levelShift, 'item') + ' would land on a requirement at a different level, which is a different kind of check.' : '') : 'verification items to move. No requirement has been removed yet.',
      vCrossTxt: V.cross ? plural(V.cross, 'cluster') + ' hold a requirement together with its parent from the level above. The app offers “link as parent and child” or “supersede” for these and never “merge”, because merging would leave one level’s verification with nothing to point at.' : 'No cluster mixes levels.',
      vSample: 'Levels, verification methods and verification items are sample values given to each requirement for this demo. A real import reads the level from a field or from your parent links, and the items from your verify links.',
      vRepointToExport: () => this.setState({ view: 'export' })
    };
  }
  /* the small V that sits on every workspace screen, and the lines the Home, Results and Export strips share */
  valsVeeStrip(S, V) {
    const nf = (n) => n.toLocaleString('en-US');
    const g = veeGlyph(V);
    const worst = V.levels.reduce((a, l) => (l.state === 'attn' && a.state !== 'attn' ? l : a), V.levels[0]);
    return {
      vTop: g, vTopAria: 'Open the V. ' + nf(V.decided) + ' of ' + nf(V.clusters) + ' clusters decided, ' + nf(V.gaps) + ' requirements without a verification method or item, ' + nf(V.repoint) + ' verification items to move.',
      openVee: () => this.setState({ view: 'vee' }),
      vHome: g, vHomeTitle: 'Where the work sits in the V',
      vHomeLines: [
        { shape: 'width:11px;height:11px;border-radius:50%;background:#1C5CAB;display:inline-block;flex:none', t: nf(V.decided) + ' of ' + nf(V.clusters) + ' clusters have a standing decision on the left leg' + (V.held ? ' (' + nf(V.held) + ' more are held as stale or disputed)' : '') },
        { shape: 'width:11px;height:11px;background:#1B6B3A;display:inline-block;flex:none', t: nf(V.gaps) + ' requirements with no verification method or item on the right leg' },
        { shape: 'width:14px;border-top:2px dashed #54626F;display:inline-block;flex:none', t: nf(V.repoint) + ' verification items will have to move to a surviving requirement' }
      ],
      vResultsRows: V.levels.map((l) => ({ lvl: 'Level ' + l.k + ' · ' + l.short, now: nf(l.reqs), after: nf(l.after), gone: l.gone > 0 ? '−' + nf(l.gone) : l.gone < 0 ? '+' + nf(-l.gone) : '0', re: nf(l.repoint), gaps: nf(l.gaps) })),
      vResultsTotal: { lvl: 'All levels', now: nf(V.reqs), after: nf(V.after), gone: V.reqs - V.after ? '−' + nf(V.reqs - V.after) : '0', re: nf(V.repoint), gaps: nf(V.gaps) },
      vResultsNote: V.repoint ? nf(V.repoint) + ' verification items sit on requirements your decisions remove or mark superseded. Each has to be pointed at the requirement that takes its place, or the check proves nothing. The trace map in Export lists every one.' : 'No decision removes a requirement that carries a verification item.',
      vExportLine: V.repoint ? nf(V.repoint) + ' verification items move to a surviving requirement. ' + (worst.state === 'attn' ? 'Most are at level ' + V.levels.reduce((a, l) => (l.repoint > a.repoint ? l : a), V.levels[0]).k + '.' : '') : 'No verification item has to move yet.'
    };
  }
  /* ----- methods and metrics: sample scores for four ways of working, then by category (see data4.js; nothing here is measured) ----- */
  valsMethods(S) {
    const f1 = (p, r) => (p + r > 0 ? (2 * p * r) / (p + r) : 0);
    const f2 = (v) => v.toFixed(2);
    const sgn = (d) => (Math.abs(d) < 0.005 ? '0.00' : (d > 0 ? '+' : '−') + Math.abs(d).toFixed(2));
    const dword = (d) => (Math.abs(d) < 0.005 ? 'no change' : d > 0 ? 'higher' : 'lower');
    const armKey = S.metArm === 'before' ? 'before' : 'after';
    const sortKey = ['gain', 'with', 'without'].indexOf(S.metSort) >= 0 ? S.metSort : 'gain';
    const bar = (v) => 'height:10px;background:#2A6FD6;border-radius:0 5px 5px 0;width:' + Math.round(v * 100) + '%';
    const total = (a) => {
      let tp = 0, pred = 0, gold = 0;
      CAT_SCORES.forEach((r) => { const g = r[2], p = r[ARM_COL[a]][0], rc = r[ARM_COL[a]][1], t = rc * g; tp += t; pred += t / p; gold += g; });
      const P = tp / pred, R = tp / gold;
      return { P, R, F: f1(P, R), fp: Math.round(pred - tp), fn: Math.round(gold - tp), gold };
    };
    const T = {}; ARM_KEYS.forEach((a) => { T[a] = total(a); });
    const bestF = Math.max.apply(null, ARM_KEYS.map((a) => T[a].F));
    const shape = (k) => (ARM_INFO[k].mark === 'mech' ? MARK.mech[1] : MARK.ai[1]);
    const arms = ARM_KEYS.map((a) => ({
      name: ARM_INFO[a].name, sub: ARM_INFO[a].sub, shape: shape(a), p: f2(T[a].P), r: f2(T[a].R), f: f2(T[a].F), fBar: bar(T[a].F),
      best: T[a].F === bestF, change: a === 'mech' ? 'baseline' : sgn(T[a].F - T.mech.F) + ' ' + dword(T[a].F - T.mech.F),
      fp: String(T[a].fp), fn: String(T[a].fn), mins: ARM_OPS[a].mins.toFixed(1), calls: ARM_OPS[a].calls.toLocaleString('en-US'), aiMin: ARM_OPS[a].aiMin ? ARM_OPS[a].aiMin + ' min' : 'none'
    }));
    const M = T.mech, A = T.after, B = T.before;
    const reading = 'In this sample, adding the AI after the mechanical steps moves the score from ' + f2(M.F) + ' to ' + f2(A.F) + ' (' + sgn(A.F - M.F) + ') and cuts wrong suggestions from ' + M.fp + ' to ' + A.fp + ', with ' + ARM_OPS.after.calls.toLocaleString('en-US') + ' AI calls. Running the AI first finds more real pairs (missed: ' + B.fn + ' against ' + M.fn + ') but lets in more wrong ones (' + B.fp + ') and needs about ' + Math.round(ARM_OPS.before.calls / ARM_OPS.after.calls) + ' times the calls.';
    /* each mechanical method, then with AI after and with AI before */
    const lad = LADDER.map(([name, p, r, a, b, n]) => ({ name, p, r, a, b, n })).concat([{ name: 'Combined score (the mechanical result above)', p: M.P, r: M.R, a: [A.P, A.R], b: [B.P, B.R], n: 1126, combined: true }]);
    const ladder = lad.map((x) => {
      const f0 = f1(x.p, x.r), fa = f1(x.a[0], x.a[1]), fb = f1(x.b[0], x.b[1]);
      return { name: x.name, p: f2(x.p), r: f2(x.r), f: f2(f0), fBar: bar(f0), fa: f2(fa), da: sgn(fa - f0) + ' ' + dword(fa - f0), fb: f2(fb), db: sgn(fb - f0) + ' ' + dword(fb - f0), n: x.n.toLocaleString('en-US'), rowStyle: x.combined ? 'background:#F4F6F8;' : '', nameStyle: x.combined ? 'font-weight:700;' : 'font-weight:600;' };
    });
    /* by category: score without AI and with AI (after or before the mechanical steps) */
    const col = ARM_COL[armKey];
    const cats = CAT_SCORES.map((r) => {
      const w0 = f1(r[3][0], r[3][1]), w1 = f1(r[col][0], r[col][1]), nCl = CLUSTERS.filter((c) => c.famKey === r[0]).length;
      return { k: r[0], name: r[1], g: r[2], nCl, m: r[3], w: r[col], w0, w1, d: w1 - w0 };
    });
    const bestWithout = cats.slice().sort((x, y) => y.w0 - x.w0)[0], bestWith = cats.slice().sort((x, y) => y.w1 - x.w1)[0];
    const sorted = cats.slice().sort((x, y) => (sortKey === 'with' ? y.w1 - x.w1 : sortKey === 'without' ? y.w0 - x.w0 : y.d - x.d) || (x.name < y.name ? -1 : 1));
    const pos = (v) => Math.max(0, Math.min(100, ((v - 0.5) / 0.5) * 100));
    const armName = ARM_INFO[armKey].name.toLowerCase();
    const catRows = sorted.map((x) => ({
      name: x.name, sub: x.nCl + ' clusters here · ' + x.g + ' labelled pairs', few: x.g < 60, bestWithout: x === bestWithout, bestWith: x === bestWith,
      line: 'left:' + Math.min(pos(x.w0), pos(x.w1)).toFixed(1) + '%;width:' + Math.abs(pos(x.w1) - pos(x.w0)).toFixed(1) + '%;',
      sq: 'left:' + pos(x.w0).toFixed(1) + '%;', dm: 'left:' + pos(x.w1).toFixed(1) + '%;',
      without: f2(x.w0), withAI: f2(x.w1), delta: sgn(x.d), deltaWord: dword(x.d),
      aria: x.name + ': ' + f2(x.w0) + ' without AI, ' + f2(x.w1) + ' with AI ' + (armKey === 'after' ? 'after' : 'before') + ' the mechanical steps, ' + dword(x.d) + ' by ' + Math.abs(x.d).toFixed(2) + '.',
      p0: f2(x.m[0]), r0: f2(x.m[1]), p1: f2(x.w[0]), r1: f2(x.w[1]), nCl: String(x.nCl), g: String(x.g)
    }));
    const topN = (key) => cats.slice().sort((x, y) => y[key] - x[key]).slice(0, 3).map((x, i) => ({ rank: String(i + 1), name: x.name, v: f2(x[key]) }));
    const gain = cats.slice().sort((x, y) => y.d - x.d)[0], lows = cats.filter((x) => x.d < -0.005).sort((x, y) => x.d - y.d);
    const catNotes = ['The most gained from the AI: ' + gain.name + ' (' + sgn(gain.d) + ').', lows.length ? 'The AI lowers the score in ' + lows.map((x) => x.name + ' (' + sgn(x.d) + ')').join(', ') + ' when it runs ' + (armKey === 'after' ? 'after' : 'before') + ' the mechanical steps.' : 'With the AI running ' + (armKey === 'after' ? 'after' : 'before') + ' the mechanical steps, no category gets worse.', 'Categories with fewer than 60 labelled pairs are marked: their scores can move a lot with a few more labels.'].map((t) => ({ t }));
    const pill = (on) => 'min-height:40px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#7A8793') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';color:#12171C;';
    const armBtns = [['after', 'AI after the mechanical steps'], ['before', 'AI before the mechanical steps']].map(([k, label]) => ({ label, pressed: armKey === k ? 'true' : 'false', style: pill(armKey === k), pick: () => this.setState({ metArm: k }) }));
    const sortBtns = [['gain', 'Biggest gain from AI'], ['with', 'Best with AI'], ['without', 'Best without AI']].map(([k, label]) => ({ label, pressed: sortKey === k ? 'true' : 'false', style: pill(sortKey === k), pick: () => this.setState({ metSort: k }) }));
    /* kept from before */
    const cont = [['118', 'Both suggest a merge', 'Strongest candidates'], ['64', 'Mechanical only', 'Check for lookalikes'], ['31', 'AI only', 'Check for invented links'], ['39', 'Neither', 'Left alone']].map(([n, label, sub]) => ({ n, label, sub }));
    const acc = [['Under 0.50', 0.31], ['0.50 to 0.70', 0.52], ['0.70 to 0.90', 0.74], ['Over 0.90', 0.93]].map(([bin, v]) => ({ bin, v: Math.round(v * 100) + '%', bar: bar(v) }));
    const infos = this.allInfos(S), decs = infos.filter((x) => x.dec);
    const followed = decs.filter((x) => x.dec.vs === 'Agreed with AI').length, over = decs.filter((x) => x.dec.vs === 'Overrode AI').length;
    const edited = decs.filter((x) => x.dec.share && x.dec.share.bucket !== 'as-is').length;
    const undone = S.events.filter((e) => /Reopened|Undo/.test(e.text)).length;
    const second = decs.filter((x) => x.dec.checkedBy || (x.dec.reviewedBy && x.dec.reviewedBy.length)).length;
    const live = [['Decisions made', decs.length + ' of ' + infos.length], ['Agreed with the AI', String(followed)], ['Overrode the AI (note required)', String(over)], ['Edited an AI draft', String(edited)], ['Checked or reviewed by a teammate you asked', String(second)], ['Decisions reopened this session', String(undone)]].map(([k, v]) => ({ k, v }));
    const all = infos.map((x) => x.c.guards).join('').split('');
    const nP = all.filter((x) => x === 'p').length, nW = all.filter((x) => x === 'w').length, nF = all.filter((x) => x === 'f').length;
    const quotes = infos.reduce((n, x) => n + x.c.ai.quotes.length, 0);
    const blocked = infos.filter((x) => x.c.ai.mode === 'judge' && x.c.guards.indexOf('f') >= 0).length;
    const guardStats = [['Checks run', all.length.toLocaleString('en-US')], ['Passed', nP.toLocaleString('en-US') + ' (' + Math.round((nP / all.length) * 100) + '%)'], ['Warnings', String(nW)], ['Blocked a merge', String(nF)], ['AI judgements stopped by a guard', blocked + ' of ' + infos.filter((x) => x.c.ai.mode === 'judge').length], ['Quoted evidence found verbatim', quotes + ' of ' + quotes]].map(([k, v]) => ({ k, v }));
    const lanes = ['A', 'B', 'C'].map((l) => { const g = decs.filter((x) => x.c.lane === l); return { k: 'Lane ' + l + ' decided', v: g.length + ' of ' + infos.filter((x) => x.c.lane === l).length }; });
    return {
      arms, reading, ladder, catRows, armBtns, sortBtns, armName, armShort: armKey === 'after' ? 'after' : 'before',
      topWithout: topN('w0'), topWith: topN('w1'), catNotes,
      showTable: !!S.metTable, showChart: !S.metTable, tableLabel: S.metTable ? 'Show the chart' : 'Show as a table', tablePressed: S.metTable ? 'true' : 'false', toggleTable: () => this.setState({ metTable: !S.metTable }),
      goldPairs: M.gold.toLocaleString('en-US'),
      mtAiNote: (() => { const k = aiCounts(S, CLUSTERS); return !S.aiOn ? 'AI is switched off, so no group goes to a model and no AI answer is shown. The “with AI” scores on this page come from a trial run on the sample data set. They show what the AI added then, and they do not change with the switch.' : k.held ? k.held.toLocaleString('en-US') + ' of ' + k.total.toLocaleString('en-US') + ' groups are held back from the AI by the data sheet, so people review them without an AI answer. The “with AI” scores on this page come from a trial run on the sample data set and do not change with the data sheet.' : ''; })(),
      cont, acc, live, guardStats, laneStats: lanes,
      ...this.valsGoldPanel(S)
    };
  }
  /* ----- results and grade: the consolidated set set against the original, computed from the decisions (see logic3.js) ----- */
  valsResults(S) {
    const infos = this.allInfos(S), U = universe(S);
    const R = resultsOf(S, infos, '');
    const fmt = (n) => n.toLocaleString('en-US');
    const one = (n) => (Math.round(n * 10) / 10).toFixed(1);
    const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0) + '%';
    const goto = (o) => () => this.setState(Object.assign({ view: 'review', qTab: 'all', qSearch: '', qLane: '', qStatus: '', qAlloc: '', qPage: 0, just: '' }, o));
    const openCl = (cid) => () => this.setState({ view: 'review', selected: cid, qTab: 'all', qSearch: '', just: '', openVer: Object.assign({}, S.openVer, { [cid]: S.liveVer[cid] || 0 }) });
    const graded = R.graded;
    /* the grade card */
    const bands = GRADE_BANDS.map(([min, letter], i) => {
      const hi = i === 0 ? 100 : GRADE_BANDS[i - 1][0] - 1, here = graded && letter === R.letter;
      return { letter, range: i === GRADE_BANDS.length - 1 ? 'under ' + GRADE_BANDS[i - 1][0] : min + ' to ' + hi, here, style: 'flex:1 1 0;min-width:0;text-align:center;border-radius:6px;padding:6px 4px;display:flex;flex-direction:column;gap:0;' + (here ? 'background:#12171C;color:#FFFFFF;border:1px solid #12171C;' : 'background:#FFFFFF;color:#2F3B46;border:1px solid #B9C3CD;') };
    });
    const parts = R.parts.map((p) => ({
      name: p.name, weight: String(p.weight), pts: one(p.pts), detail: p.detail, plain: p.plain,
      fill: 'height:10px;background:#2A6FD6;border-radius:0 5px 5px 0;width:' + Math.round(p.v * 100) + '%',
      aria: p.name + ': ' + one(p.pts) + ' of ' + p.weight + ' points.'
    }));
    const provText = R.provisional ? 'Provisional. ' + R.decided + ' of ' + R.clusters + ' clusters (' + pct(R.decided, R.clusters) + ') have a decision that counts. The grade can move a lot until at least 90% do.' : 'Final for this scope: ' + R.decided + ' of ' + R.clusters + ' clusters have a decision that counts.';
    const capText = R.capped ? 'Capped at C. ' + R.unprotected + (R.unprotected === 1 ? ' merge loosens' : ' merges loosen') + ' a requirement without the owners and the process engineer having signed. Fix ' + (R.unprotected === 1 ? 'it' : 'them') + ' to lift the cap.' : R.unprotected ? R.unprotected + (R.unprotected === 1 ? ' merge loosens' : ' merges loosen') + ' a requirement without both signatures. If the grade were above C it would be held at C.' : '';
    /* original against consolidated */
    const wMax = Math.max(R.n, 1);
    const w = (v) => Math.max(1.5, (v / wMax) * 100).toFixed(1) + '%';
    const ba = [
      { label: 'Original', value: fmt(R.n), sub: 'requirements read from the sources', bar: 'height:18px;border-radius:0 4px 4px 0;background:#7B8792;width:' + w(R.n) },
      { label: 'After your decisions so far', value: fmt(R.after), sub: R.n - R.after > 0 ? fmt(R.n - R.after) + ' fewer (' + pct(R.n - R.after, R.n) + ')' : 'no change yet', bar: 'height:18px;border-radius:0 4px 4px 0;background:#2A6FD6;width:' + w(R.after) },
      { label: 'If every suggestion were taken as it stands', value: fmt(R.projected), sub: R.n - R.projected > 0 ? fmt(R.n - R.projected) + ' fewer (' + pct(R.n - R.projected, R.n) + '). A projection, not a decision.' : 'no reduction', bar: 'height:18px;border-radius:0 4px 4px 0;background:repeating-linear-gradient(45deg,#2A6FD6 0 4px,#CDE2FB 4px 8px);width:' + w(R.projected) }
    ];
    /* where each original requirement ended up */
    const DEST = [
      ['asis', 'Stays as it is', 'In no cluster. Nothing similar was found, so nothing changes.', 'background:#DCE7F7;border:1px solid #9DB8E8;'],
      ['keep', 'Kept as the surviving wording', 'The wording that stays, word for word.', DISP_STYLE.keep],
      ['merged', 'Merged into another', 'Covered by a surviving wording. The old ID stays as an alias.', DISP_STYLE.merged],
      ['separate', 'Stays separate', 'Cannot be ranked against the others, or the suggestion was rejected.', DISP_STYLE.separate],
      ['linked', 'Kept and linked', 'Both stay, joined by a “variant of” link.', DISP_STYLE.linked],
      ['escalated', 'Waiting for the owners', 'Escalated. Nothing changes until they answer.', DISP_STYLE.escalated],
      ['superseded', 'Superseded', 'Contained in a kept requirement. ID and links stay.', DISP_STYLE.superseded],
      ['kept1', 'Kept after a person looked', 'Decided on its own and kept as written.', DISP_STYLE.kept1],
      ['reworded', 'Kept with new wording', 'Decided on its own. The wording changed; the ID stays.', DISP_STYLE.reworded],
      ['dropped', 'Dropped', 'Decided on its own. It leaves the set; the ID stays as an alias.', DISP_STYLE.dropped],
      ['notreq', 'Not a requirement', 'Decided on its own. It leaves the set and stays in the document.', DISP_STYLE.notreq],
      ['waiting', 'Not decided yet', 'The cluster has no decision, or its decision is stale or disputed.', DISP_STYLE.pending]
    ];
    const destAll = DEST.map(([k, label, note, sty]) => ({ k, label, note, n: R.kinds[k], sty }));
    const total = destAll.reduce((s, d) => s + d.n, 0);
    const dest = destAll.map((d) => ({ label: d.label, note: d.note, n: fmt(d.n), pct: pct(d.n, R.n), swatch: 'width:16px;height:16px;border-radius:3px;flex:none;box-sizing:border-box;' + d.sty }));
    const destBar = destAll.filter((d) => d.n > 0).map((d) => ({ title: d.label + ': ' + fmt(d.n) + ' (' + pct(d.n, R.n) + ')', style: 'flex:' + d.n + ' 1 0;min-width:3px;height:26px;box-sizing:border-box;border-radius:3px;' + d.sty }));
    /* what would raise the grade */
    const openReq = (id) => () => this.setState({ view: 'explorer', xPick: id, xFilter: 'all', xAlloc: '', xLvl: 0, xGap: false, xPage: 0, rcmp: '', rpick: false });
    const asIds = (ids) => ids.slice(0, 3).map((id) => ({ id, open: CL_BY[id] ? openCl(id) : openReq(id) }));
    const gapOf = (k) => R.parts.find((p) => p.k === k).gap;
    const risePool = [
      { k: 'cover', n: R.waitingClusters, title: 'Decide the ' + fmt(R.waitingClusters) + (R.waitingClusters === 1 ? ' cluster' : ' clusters') + ' still waiting', text: fmt(R.kinds.waiting) + ' requirements have no destination yet. Their suggestions would bring the set to ' + fmt(R.projected) + '.', btn: 'Show them in the queue', go: goto({ qStatus: 'open' }), ids: [] },
      { k: 'sign', n: R.notSigned, title: 'Get ' + R.notSigned + (R.notSigned === 1 ? ' decision' : ' decisions') + ' fully signed', text: 'Each is missing a lens that the sign-off policy requires.', btn: 'Show decisions in review', go: goto({ qStatus: 'review' }), ids: R.ids.sign },
      { k: 'why', n: R.noWhy, title: 'Write the why on ' + R.noWhy + (R.noWhy === 1 ? ' decision' : ' decisions'), text: 'A reason code is not enough. The note says what a person reading the record later needs to know.', btn: '', go: null, ids: R.ids.why },
      { k: 'second', n: R.noSecond, title: 'Ask a teammate to look at ' + R.noSecond + (R.noSecond === 1 ? ' decision' : ' decisions'), text: 'Only the person who decided has seen these. Open one and use “Send to a teammate”.', btn: '', go: null, ids: R.ids.second },
      { k: 'oblig', n: R.unprotected, title: 'Settle ' + R.unprotected + (R.unprotected === 1 ? ' change that loosens' : ' changes that loosen') + ' a requirement', text: 'The owners and the process engineer have not both signed.' + (R.capped ? ' This also lifts the cap at C.' : ''), btn: '', go: null, ids: R.ids.oblig }
    ];
    const rise = risePool.filter((x) => x.n > 0).map((x) => Object.assign(x, { gain: '+' + one(gapOf(x.k)) + ' points at most', g: gapOf(x.k) })).sort((a, b) => b.g - a.g).map((x) => ({
      title: x.title, text: x.text, gain: x.gain, hasBtn: !!x.go, btn: x.btn, go: x.go || (() => {}), ids: asIds(x.ids), hasIds: x.ids.length > 0, more: x.ids.length > 3 ? 'and ' + (x.ids.length - 3) + ' more' : '', hasMore: x.ids.length > 3
    }));
    /* by allocation: every allocation graded on its own */
    const byAlloc = ALLOCS.filter((a) => S.scope === 'all' || a.k === S.scope).map((a) => {
      const r = resultsOf(S, infos, a.k), g = r.graded;
      return {
        name: a.k, n: fmt(r.n), clusters: String(r.clusters), decided: r.decided + ' of ' + r.clusters, decidedBar: 'height:8px;background:#2A6FD6;border-radius:0 4px 4px 0;width:' + (r.clusters ? Math.round((r.decided / r.clusters) * 100) : 0) + '%',
        after: fmt(r.after), projected: fmt(r.projected), letter: g ? r.letter : 'none', score: g ? one(r.score) : 'not graded', prov: r.provisional && g,
        letterStyle: 'display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:34px;border-radius:6px;font-weight:700;font-size:17px;box-sizing:border-box;' + (g ? 'border:2px ' + (r.provisional ? 'dashed' : 'solid') + ' #12171C;color:#12171C;' : 'border:1px dashed #B9C3CD;color:#54626F;font-size:12px;font-weight:600;padding:0 6px;'),
        open: goto({ qAlloc: a.k })
      };
    });
    /* the biggest reductions so far */
    const cuts = R.cuts.slice().sort((a, b) => b.gone - a.gone || (a.id < b.id ? -1 : 1)).slice(0, 6).map((x) => ({ id: x.id, title: x.title, change: x.from + ' wordings become ' + x.to, text: x.text, open: openCl(x.id) }));
    /* checks that should always pass */
    const adds = total === R.n;
    const excluded = infos.filter((x) => x.dec && COUNTED.indexOf(x.st) < 0).length;
    const ready = infos.filter((x) => x.st === 'approved').length;
    const okChip = 'font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;white-space:nowrap;background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;';
    const lookChip = 'font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;white-space:nowrap;background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;';
    const infoChip = 'font-size:12px;font-weight:700;padding:1px 8px;border-radius:999px;white-space:nowrap;background:#F4F6F8;color:#2F3B46;border:1px solid #B9C3CD;';
    const checks = [
      { chip: adds ? 'Passes' : 'Look at this', style: adds ? okChip : lookChip, label: 'Every original requirement has a destination', detail: 'The destinations above add up to ' + fmt(total) + ' of ' + fmt(R.n) + '. None is lost.' },
      { chip: R.unprotected ? 'Look at this' : 'Passes', style: R.unprotected ? lookChip : okChip, label: 'No merge or removal loosens a requirement without both signatures', detail: R.mergeN + R.looseN ? (R.mergeN + R.looseN - R.unprotected) + ' of ' + (R.mergeN + R.looseN) + (R.looseN ? ' merges and removals are clean.' : ' merges are clean.') : 'No merge or removal has been recorded yet.' },
      { chip: 'For information', style: infoChip, label: 'Stale or disputed decisions are left out of the grade', detail: excluded ? excluded + (excluded === 1 ? ' decision does' : ' decisions do') + ' not count until settled.' : 'None right now.' },
      { chip: 'For information', style: infoChip, label: 'Approved and ready to export', detail: ready + ' of ' + R.decided + ' decided clusters have every sign-off they need.' }
    ];
    const scopeTxt = S.scope === 'all' ? 'the whole project' : S.scope;
    return {
      rLine: 'For ' + scopeTxt + ': ' + fmt(R.n) + ' original requirements in ' + R.clusters + ' clusters. ' + R.decided + ' have a decision that counts.',
      gLetter: graded ? R.letter : '–', gAria: graded ? (R.provisional ? 'Provisional grade ' : 'Grade ') + R.letter : 'No grade yet', gGraded: graded, gUngraded: !graded,
      gBox: 'width:132px;height:132px;border-radius:16px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;font-size:84px;line-height:1;font-weight:700;letter-spacing:-.02em;color:#12171C;background:#FFFFFF;flex:none;border:3px ' + (R.provisional || !graded ? 'dashed' : 'solid') + ' #12171C;',
      gScore: graded ? one(R.score) : 'No score yet', gOut: graded ? 'out of 100' : '',
      gBandName: graded ? (R.provisional ? 'Provisional grade' : 'Grade') : 'Nothing to grade',
      gProvText: graded ? provText : 'No cluster has a decision that counts yet. Record one and the grade appears.', gHasCap: !!capText, gCapText: capText, gCapped: R.capped,
      bands, parts,
      gFormula: 'Score = ' + GRADE_PARTS.map((p) => p.weight + ' × ' + p.name.toLowerCase()).join(' + ') + '. Each part is a share from 0 to 1, worked out from the decisions. The letter is A from 90, B from 80, C from 70, D from 60, F below that. Any merge that loosens a requirement without the owners and the process engineer caps the letter at C.',
      ba, baNote: R.projected < R.n ? 'The set shrinks by ' + pct(R.n - R.projected, R.n) + ' if every suggestion is taken as it stands, and every one of those suggestions still needs a decision and its sign-offs. ' + fmt(R.newWord) + ' of the decisions so far introduce new wording.' : 'No reduction is suggested.',
      dest, destBar, destTotal: fmt(total), destAdds: adds,
      rise, hasRise: rise.length > 0, noRise: rise.length === 0,
      byAlloc, cuts, hasCuts: cuts.length > 0, noCuts: cuts.length === 0, checks,
      toMetrics: () => this.setState({ view: 'methods' }), toExport: () => this.setState({ view: 'export' }), toQueue: goto({}),
      resultsSample: 'The decisions that came with the sample project were made by sample teammates, so the grade you see before you decide anything is sample data. Your own decisions change it as soon as you record them.'
    };
  }
  valsGlossary(S) {
    const terms = [
      ['Draft', 'A suggestion nobody has approved yet. Everything you see here is a draft.'],
      ['Cluster', 'A small group of requirements that look alike. You decide what happens to the group.'],
      ['Equivalent', 'Same obligation, worded differently. Safe to merge once checked.'],
      ['Variant', 'Same subject, but a value, unit, shall/should or condition differs. Never merged automatically.'],
      ['Subsumes', 'One requirement contains the other and adds more. Keep the stricter one and link the other.'],
      ['Conflict', 'Both cannot be true at once. Escalated to the owners, never merged.'],
      ['Merge', 'Combine into one surviving requirement. The other IDs stay as aliases so no trace link is lost.'],
      ['Strategy', 'How a merged group picks its wording: most stringent, least stringent, median, one member\'s wording, your own, or an AI draft.'],
      ['Stricter direction', 'For each kind of value a lead sets once whether higher or lower is stricter (a retention period: higher; a response time: lower).'],
      ['Cannot be ranked', 'A member with a different condition or no number. It is kept separate and linked instead of being compared.'],
      ['Weakening', 'A choice that makes the requirement looser than its strictest member. It needs the owners, the PE and a note.'],
      ['Supersede', 'Mark the older requirement as replaced. Its ID and links stay.'],
      ['Baseline', 'A formally frozen version of the requirements. Changing one afterwards needs a change request.'],
      ['Suspect link', 'A trace link flagged for re-checking because something it points to changed.'],
      ['Guard', 'A plain code check that blocks a suggestion if it changes a number, unit, shall/should, a "not" or a condition.'],
      ['Lane A, B, C', 'Risk lanes. A is low risk, B needs you to read the evidence, C is a conflict.'],
      ['Lens', 'One reviewer point of view: systems engineer, process engineer, UI/UX engineer or new user. It comes from your login.'],
      ['Sign-off', 'A lens confirming the decision from its own angle. Which lenses must sign depends on the lane and on whether new wording is introduced. You cannot sign a decision you recorded yourself.'],
      ['Sampled', 'A lens that is only required on a fixed 20% sample of clusters, chosen by a hash of the cluster ID so it never changes.'],
      ['Adjudicator', 'A lead who settles a disagreement between lenses. The dissent is kept in the record.'],
      ['Claim', 'A soft marker that a teammate is looking at a cluster. It expires after 15 minutes and never locks anyone out.'],
      ['Stale', 'A decision whose source requirement changed afterwards. It no longer counts until someone decides again.'],
      ['Revision chain', 'R0 original wordings, R1 grouping, R2 AI draft, R3 and later person edits. A later AI run never replaces a person\'s revision.'],
      ['AI-origin share', 'How much of the final wording is still the AI draft: as is, light edit, heavy edit or rewritten.'],
      ['Reason code', 'A short, searchable reason saved with every decision. "Other" always needs a note.'],
      ['Provenance', 'Who or what made a suggestion: a mechanical method (square), the AI (diamond), a person (circle) or the assistant (speech bubble).'],
      ['Embedding', 'A numeric fingerprint of meaning, used to find requirements that say similar things.'],
      ['NLI', 'A model that says whether one sentence implies, contradicts or is unrelated to another.'],
      ['Gold set', 'Pairs of requirements that people have labelled. Accuracy can only be measured against it.'],
      ['Calibration', 'Whether "90% sure" turns out right about 90% of the time.']
    ];
    return { glossaryOpen: S.glossary, glossary: terms.map(([term, text]) => ({ term, text })), closeGlossary: () => this.setState({ glossary: false }) };
  }
  shownEvents(S) {
    return EV_SEED.concat(S.events).map((e) => (S.tamper && e.seq === 2 ? Object.assign({}, e, { text: 'Blocked by allocation; built 1,090 candidate pairs (edited after the fact)' }) : e));
  }
  /* ----- decisions and audit ----- */
  valsAudit(S) {
    const ev = this.shownEvents(S), U = universe(S);
    const shapes = { mechanical: ['Mechanical', MARK.mech[1]], ai: ['AI', MARK.ai[1]], human: ['Person', MARK.human[1]], bot: ['Assistant', MARK.bot[1]] };
    const bad = S.verified.indexOf('fail:') === 0 ? Number(S.verified.slice(5)) : 0;
    const eventRows = ev.slice().reverse().slice(0, 40).map((e) => ({
      seq: e.seq, time: e.time, kind: shapes[e.type][0], shape: shapes[e.type][1], actor: e.actor, text: e.text, target: e.target, prev: e.prev, hash: e.hash,
      rowStyle: 'display:grid;grid-template-columns:40px 70px 120px 190px minmax(0,1fr) 90px 170px;gap:12px;padding:10px 16px;border-bottom:1px solid #E3E7EA;align-items:start;' + (bad && e.seq === bad ? 'background:#FDE3E0;' : '')
    }));
    const ok = S.verified === 'ok';
    const q = S.lfilter.trim().toLowerCase();
    const all = ledgerRows(S, U.cl).filter((r) => !q || (r.cid + ' ' + r.title + ' ' + r.decision + ' ' + r.reason + ' ' + r.by + ' ' + r.note).toLowerCase().indexOf(q) >= 0);
    const PAGE = 10, pages = Math.max(1, Math.ceil(all.length / PAGE)), page = Math.min(S.lpage, pages - 1);
    const tabStyle = (on) => 'min-height:44px;padding:0 14px;border-radius:6px;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#7A8793') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';';
    const open = (cid) => () => (CL_BY[cid] ? this.setState({ view: 'review', selected: cid, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [cid]: S.liveVer[cid] || 0 }) }) : this.setState({ view: 'explorer', xPick: cid, xFilter: 'all', xAlloc: '', xLvl: 0, xGap: false, xPage: 0, rcmp: '', rpick: false }));
    return {
      logTabs: [['ledger', 'Decision ledger'], ['chain', 'Event chain']].map(([k, label]) => ({ label, pressed: S.logTab === k ? 'true' : 'false', pick: () => this.setState({ logTab: k }), style: tabStyle(S.logTab === k) })),
      isLedger: S.logTab === 'ledger', isChain: S.logTab === 'chain',
      lrows: all.slice(page * PAGE, page * PAGE + PAGE).map((r) => ({ cid: r.cid, title: r.title, when: r.when, decision: r.decision, reason: r.reason, by: r.by, vs: r.vs, state: r.state, note: r.note || 'No note', share: r.share || '', hasShare: !!r.share, open: open(r.cid), openLabel: CL_BY[r.cid] ? 'Open cluster' : 'Open requirement', openAria: (CL_BY[r.cid] ? 'Open cluster ' : 'Open requirement ') + r.cid })),
      lInfo: all.length ? 'Showing ' + (page * PAGE + 1) + ' to ' + Math.min(all.length, page * PAGE + PAGE) + ' of ' + all.length : 'No decisions match', lPageText: 'Page ' + (page + 1) + ' of ' + pages,
      lPrevDisabled: page === 0, lNextDisabled: page >= pages - 1, lPrev: () => this.setState({ lpage: Math.max(0, page - 1) }), lNext: () => this.setState({ lpage: Math.min(pages - 1, page + 1) }),
      lfilterV: S.lfilter, onLfilter: (e) => this.setState({ lfilter: e.target.value, lpage: 0 }),
      eventRows, tamper: S.tamper, evNote: 'Newest first. Showing the latest ' + Math.min(40, ev.length) + ' of ' + ev.length + ' entries.',
      toggleTamper: () => this.setState({ tamper: !S.tamper, verified: '' }),
      verifyChain: () => {
        const result = chainCheck(ev);
        this.setState({ verified: result });
      },
      verifyShown: S.verified !== '',
      verifyStyle: 'border-radius:6px;padding:10px 14px;font-weight:600;' + (ok ? 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;' : 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;'),
      verifyText: ok ? 'Chain verified: all ' + ev.length + ' entries match their fingerprints.' : 'Chain broken at entry ' + bad + '. The entry no longer matches its fingerprint.'
    };
  }
  /* ----- sign-off policy ----- */
  valsPolicy(S) {
    const rows = [
      ['Lane A · no new wording', 'Required', 'Sampled (20%)', 'Not needed', 'Not needed', 'Pick an existing wording word for word.'],
      ['Lane A · new wording', 'Required', 'Required', 'Required', 'Required', 'Your own or AI wording is new text, so all four lenses read it.'],
      ['Lane B · no new wording', 'Required', 'Required', 'Not needed', 'Sampled (20%)', 'Owners also approve if the group spans owners.'],
      ['Lane B · new wording', 'Required', 'Required', 'Required', 'Required', 'Plus owners if the group spans owners.'],
      ['Lane C · conflict', 'Required', 'Required', 'Not needed', 'Not needed', 'Plus the owners and the adjudicator. A conflict is never merged.'],
      ['Baselined requirement', 'As above', 'Required, always', 'As above', 'As above', 'Also needs a linked change request.'],
      ['A lens objects', 'Paused', 'Paused', 'Paused', 'Paused', 'The adjudicator decides. The dissent stays in the record.']
    ].map(([a, b, c, d, e, f]) => ({ a, b, c, d, e, f }));
    const dec = { newWording: S.polNew, weakening: false };
    const fake = { id: 'CL-POLICY-DEMO', lane: S.polLane, crossOwner: S.polCross, baselined: S.polBase };
    const req = required(fake, dec);
    /* the demo cluster is not a real cluster, so its own ID must not decide whether it is sampled: show the sampled lens whenever the rule has one */
    const sk = (S.polNew ? [] : S.polLane === 'A' ? ['PE'] : S.polLane === 'B' ? ['NU'] : []).filter((k) => req[k] !== 'req');
    const out = SLOT_KEYS.filter((k) => req[k] !== 'none' && sk.indexOf(k) < 0).map((k) => ({ label: SLOT_NAME[k] }));
    const samples = sk.map((k) => ({ label: SLOT_NAME[k] + ' only if the 20% sample picks the cluster' }));
    const sel = (on) => 'min-height:44px;padding:0 14px;border-radius:6px;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #7A8793') + ';background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';';
    const tog = (key, label) => ({ label: label + ': ' + (S[key] ? 'yes' : 'no'), pressed: S[key] ? 'true' : 'false', pick: () => this.setState({ [key]: !S[key] }), style: sel(S[key]) });
    return {
      polRows: rows,
      polLanes: ['A', 'B', 'C'].map((l) => ({ label: 'Lane ' + l, pressed: S.polLane === l ? 'true' : 'false', pick: () => this.setState({ polLane: l }), style: sel(S.polLane === l) })),
      polToggles: [tog('polNew', 'New wording'), tog('polCross', 'Spans owners'), tog('polBase', 'Baselined')],
      polOut: out, polSamples: samples, polHasSamples: samples.length > 0,
      polNote: S.polLane === 'C' ? 'Conflicts are escalated, not merged, so wording never changes here.' : 'The sample is chosen by a hash of the cluster ID, so the same clusters are always sampled.',
      syncRules: [
        ['Soft claims', 'Opening a cluster marks it as yours for 15 minutes. It warns teammates and never locks them out.'],
        ['Cluster version', 'Every save checks the version you opened. If it moved, deciding pauses and you reload first.'],
        ['Sibling versions', 'If two people edit at once, both edits are kept as sibling versions and a person picks one.'],
        ['Revision binding', 'A sign-off belongs to one revision hash. Changing the decision clears the sign-offs.'],
        ['Source drift', 'If the model changes under a decision, that decision is marked stale and counts for nothing until it is made again.'],
        ['One lens per person', 'A person signs only for the lens their login gives them, and cannot sign two lenses on one revision.'],
        ['Second pair of eyes', 'The person who recorded a decision cannot sign it. A colleague with the same lens does, so no decision is only ever seen by one person.']
      ].map(([k, v]) => ({ k, v })),
      weakRules: ['pick least stringent, median or your own wording', 'weaken a requirement (a looser value, or shall to should)', 'disagree with the AI (merge a variant, or reject a drafted merge)', 'reject a suggestion in lane B or C', 'reopen any decision'].map((t) => ({ t }))
    };
  }
  /* ----- export ----- */
  valsExport(S) {
    const infos = this.allInfos(S).filter((x) => x.dec);
    const readyC = infos.filter((x) => x.st === 'approved'), waitC = infos.filter((x) => x.st === 'review' || x.st === 'decided'), flagC = infos.filter((x) => attention(x.st));
    const go = (c) => () => this.setState({ view: 'review', selected: c.id, qTab: 'all', just: '' });
    const FM = [['sphinx', 'Sphinx-Needs (reStructuredText)', 'Needs-as-code pages with trace tables', ['requirements.rst', 'traceability.rst', 'change-record.rst', 'alias-map.csv', 'trace-map.json']], ['strictdoc', 'StrictDoc (SDoc)', 'Requirements document with HTML or PDF output', ['requirements.sdoc', 'change-record.sdoc', 'alias-map.csv', 'trace-map.json']], ['docx', 'Word (.docx)', 'Built from a Word template', ['Requirements-' + S.baseId + '.docx', 'alias-map.csv', 'trace-map.json']], ['reqif', 'ReqIF 1.2', 'Round trip back to MSOSA', ['requirements.reqif', 'alias-map.csv', 'trace-map.json']]];
    const fm = FM.find((f) => f[0] === S.fmt) || FM[0];
    const n = readyC.length;
    const nAll = universe(S).cl.length;
    return {
      readyCount: n, noReady: n === 0, waitCount: waitC.length, flagCount: flagC.length, undecidedCount: nAll - this.allInfos(S).filter((x) => x.dec).length,
      ready: readyC.slice(0, 8).map((x) => ({ id: x.c.id, title: x.c.title, decision: describeDec(x.dec), change: go(x.c) })), moreReady: n > 8 ? 'and ' + (n - 8) + ' more approved clusters' : '', hasMoreReady: n > 8,
      waiting: waitC.slice(0, 5).map((x) => ({ id: x.c.id, missing: x.q.missing.map((k) => SLOT_NAME[k]).join(', '), change: go(x.c) })), moreWait: waitC.length > 5 ? 'and ' + (waitC.length - 5) + ' more' : '', hasMoreWait: waitC.length > 5,
      baseId: S.baseId, onBase: (e) => this.setState({ baseId: e.target.value, published: false }),
      formats: FM.map(([k, name, sub]) => ({ name, sub, on: S.fmt === k, pick: () => this.setState({ fmt: k, published: false }) })),
      prepareDisabled: n === 0, prepareLabel: n === 0 ? 'Prepare draft package' : 'Prepare ' + n + ' ' + (n === 1 ? 'change' : 'changes') + ' as a draft package',
      prepareHelp: n === 0 ? 'Disabled until at least one change is approved by every lens its policy requires.' : 'Stale and disputed clusters are left out. Preparing is logged, and you can prepare again after more approvals.',
      published: S.published && n > 0, packageFiles: fm[3].join(', '),
      prepare: () => this.setState({ published: true, events: this.mk(S.events, 'human', this.person(S).name + ' · ' + (this.person(S).lens || ''), 'Prepared draft package ' + S.baseId + ' (' + fm[1] + ', ' + n + (n === 1 ? ' change' : ' changes') + ')', S.baseId) })
    };
  }
  /* ----- the assistant ----- */
  valsAssist(S) {
    const U = universe(S);
    let c = CL_BY[S.selected];
    if (!c || (S.scope !== 'all' && c.alloc !== S.scope)) c = U.order[0];
    c = aiCl(S, c);
    const cid = c.id, ms = membersOf(S, c), P = this.person(S);
    const log = S.chat[cid] || [];
    const blindHidden = this.blindOn(S) && !decOf(S, cid) && !S.blindDone[cid] && c.ai.mode !== 'none';
    const reply = (intent) => assistReply(S, c, ms, intent, blindHidden);
    const push = (user, r) => this.setState({ chat: Object.assign({}, S.chat, { [cid]: log.concat([{ who: 'you', text: user }, { who: 'bot', text: r.text, quotes: (r.quotes || []).map(([w, t]) => ({ who: w, text: t })), draft: r.draft || '', refs: (r.refs || []).join(' · ') }]) }) });
    const ask = (intent, label) => () => push(label, reply(intent));
    const msgs = log.map((m, i) => ({
      isYou: m.who === 'you', isBot: m.who === 'bot', text: m.text, hasQuotes: !!(m.quotes && m.quotes.length), quotes: m.quotes || [], hasDraft: !!m.draft, draft: m.draft || '', hasRefs: !!m.refs, refs: m.refs || '',
      useDraft: () => { this.setState({ res: Object.assign({}, S.res, { [cid]: Object.assign({}, S.res[cid] || {}, { outcome: 'merge', strat: 'own', own: m.draft, ownSeed: m.draft }) }), view: 'review', chat: Object.assign({}, S.chat, { [cid]: log.concat([{ who: 'bot', text: 'Done. The draft is now in "Write your own wording" in the Resolve panel. Edit it there. Nothing is saved until you record the decision, and your edits are measured against my draft.', quotes: [], draft: '', refs: '' }]) }), events: this.mk(S.events, 'bot', 'Assistant for ' + P.name, 'Drafted wording; ' + P.name + ' took it as a starting point (not saved)', cid) }); setTimeout(() => { try { const el = document.querySelector('.rv-resolve'); if (el && el.scrollIntoView) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); } catch (e) { /* no scrolling */ } }, 80); },
      useDisabled: !this.canAct(S) || !!decOf(S, cid), tagStyle: CHIP + MARK.bot[2]
    }));
    return {
      chatShown: S.chatOpen, aCluster: cid + ' · ' + c.title, aActor: P.name + (P.lens ? ' · ' + P.lens : ' · observer'),
      msgs, hasMsgs: msgs.length > 0, noMsgs: msgs.length === 0, chips: CHIPS.map(([k, label]) => ({ label, onClick: ask(k, label), off: !!c.aiHeld, style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:' + (c.aiHeld ? 'not-allowed' : 'pointer') + ';font-size:13px;border:1px solid #0B6E99;background:#E3F4FB;color:#0B4F6E;font-weight:600;' + (c.aiHeld ? 'opacity:.55;' : '') })),
      aHeld: !!c.aiHeld, aHeldNote: c.aiHeld ? 'Not used on this group. ' + c.aiHeld.text : '',
      chatV: S.chatInput, onChat: (e) => this.setState({ chatInput: e.target.value }),
      sendChat: () => { const t = S.chatInput.trim(); if (!t) return; const i = intentOf(t); if (!i) { this.setState({ chatInput: '', chat: Object.assign({}, S.chat, { [cid]: log.concat([{ who: 'you', text: t }, { who: 'bot', text: 'In this prototype I answer the six suggested questions. In the real tool I would answer this from the project, as you, using only what you may read.', quotes: [], draft: '', refs: '' }]) }) }); return; } this.setState({ chatInput: '' }); push(t, reply(i)); },
      sendDisabled: S.chatInput.trim().length === 0 || !!c.aiHeld, closeChat: () => this.setState({ chatOpen: false }),
      blindNote: blindHidden ? 'Blind-first is on, so I will not tell you what the AI judged until you record your own first impression.' : ''
    };
  }
  renderVals() {
    const S = this.S;
    const v = { accent: this.props.accent ?? '#1A4DB5', view: S.view };
    v.isOpen = S.view === 'open';
    v.isImport = S.view === 'import';
    v.isVerify = v.isImport && S.source === 'doc' && S.impStep === 'verify';
    v.isMap = v.isImport && !v.isVerify;
    v.inWorkspace = !(v.isOpen || v.isImport);
    v.alignOpen = false;
    v.isHome = S.view === 'home';
    v.isOverview = S.view === 'overview';
    v.isReview = S.view === 'review';
    v.isExplorer = S.view === 'explorer';
    v.isMethods = S.view === 'methods';
    v.isResults = S.view === 'results';
    v.isVee = S.view === 'vee';
    v.isGold = S.view === 'gold';
    v.isAudit = S.view === 'audit';
    v.isPolicy = S.view === 'policy';
    v.isAi = S.view === 'ai';
    v.isExport = S.view === 'export';
    Object.assign(v, this.valsOpen(S), this.valsImport(S), this.valsVerify(S), this.valsShell(S), this.valsGlossary(S), this.valsConn(S));
    // the page's name, for the tab, for a screen reader when it changes, and for the skip link
    v.pageTitle = v.isOpen ? 'Open a requirements project' : v.isVerify ? 'Check statements found in a document' : v.isImport ? 'Map fields and choose scope' : v.pageName;
    v.pageAnnounce = 'Now showing: ' + v.pageTitle;
    v.skipToMain = (e) => { if (e && e.preventDefault) e.preventDefault(); const m = typeof document !== 'undefined' ? document.getElementById('main-content') : null; if (m) m.focus(); };
    if (typeof document !== 'undefined' && document.title !== v.pageTitle + ' · Requirements Consolidator') document.title = v.pageTitle + ' · Requirements Consolidator';
    if (v.inWorkspace) {
      this._V = veeOf(S, this.allInfos(S)); this._T = null;
      Object.assign(v, this.valsVeeStrip(S, this._V));
      if (v.isHome) Object.assign(v, this.valsHome(S), this.valsKeep(S));
      if (v.isOverview) Object.assign(v, this.valsOverview(S));
      if (v.isReview) Object.assign(v, this.valsQueue(S), this.valsDetail(S));
      if (v.isExplorer) Object.assign(v, this.valsExplorer(S));
      if (v.isMethods) Object.assign(v, this.valsMethods(S));
      if (v.isResults) Object.assign(v, this.valsResults(S));
      if (v.isVee) Object.assign(v, this.valsVee(S, this._V));
      if (v.isGold) Object.assign(v, this.valsGold(S));
      if (v.isAudit) Object.assign(v, this.valsAudit(S));
      if (v.isPolicy) Object.assign(v, this.valsPolicy(S));
      if (v.isAi) Object.assign(v, this.valsAi(S));
      if (v.isExport) Object.assign(v, this.valsExport(S), this.valsTrace(S));
      Object.assign(v, this.valsAssist(S));
    }
    return v;
  }
