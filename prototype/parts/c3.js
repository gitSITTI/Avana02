  /* ----- all requirements: map, table, one requirement ----- */
  reqState(S, r) {
    if (!r.cid) return 'alone';
    const st = statusOf(S, CL_BY[r.cid]);
    return st === 'approved' ? 'approved' : st === 'review' || st === 'decided' ? 'review' : attention(st) ? 'attn' : 'open';
  }
  valsExplorer(S) {
    const U = universe(S), P = this.person(S);
    const SQ = 'width:10px;height:10px;border-radius:2px;display:inline-block;box-sizing:border-box;flex:none;';
    const STY = {
      alone: ['Alone · nothing similar found', SQ + 'border:2px solid #7B8792;background:transparent', '#7B8792'],
      open: ['In a cluster · needs a decision', SQ + 'background:#7FB0EE', '#7FB0EE'],
      review: ['Decided · collecting sign-offs', SQ + 'background:#1C5CAB', '#1C5CAB'],
      approved: ['Approved', SQ + 'background:#1B6B3A', '#1B6B3A'],
      attn: ['Needs attention · stale, disagreement or too big', SQ + 'background:repeating-linear-gradient(45deg,#B35A00 0 3px,#FFD9A8 3px 5px)', '#B35A00']
    };
    const stateOf = {}; U.reqs.forEach((r) => { stateOf[r.id] = this.reqState(S, r); });
    const meSet = new Set(); this.allInfos(S).forEach((x) => { if (x.me) x.c.members.forEach((m) => meSet.add(m.id)); });
    const matches = (r) => (S.xFilter === 'all' ? true : S.xFilter === 'mine' ? meSet.has(r.id) : stateOf[r.id] === S.xFilter) && (!S.xAlloc || r.alloc === S.xAlloc);
    const counts = { all: U.reqs.length, alone: 0, open: 0, review: 0, approved: 0, attn: 0 };
    U.reqs.forEach((r) => { counts[stateOf[r.id]]++; });
    const fdefs = [['all', 'All'], ['mine', 'For me'], ['open', 'Needs a decision'], ['review', 'In review'], ['approved', 'Approved'], ['attn', 'Needs attention'], ['alone', 'Alone']];
    const chips = fdefs.map(([k, label]) => ({ label, count: k === 'mine' ? meSet.size : counts[k], pressed: S.xFilter === k ? 'true' : 'false', pick: () => this.setState({ xFilter: k, xPage: 0 }), style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (S.xFilter === k ? 600 : 500) + ';border:1px solid ' + (S.xFilter === k ? 'var(--accent)' : '#8C98A3') + ';background:' + (S.xFilter === k ? '#E8F0FD' : '#FFFFFF') + ';' }));
    const groups = ALLOCS.filter((a) => S.scope === 'all' || a.k === S.scope).map((a) => {
      const rs = U.reqs.filter((r) => r.alloc === a.k);
      return {
        name: a.k, count: rs.length, on: S.xAlloc === a.k, pressed: S.xAlloc === a.k ? 'true' : 'false', pick: () => this.setState({ xAlloc: S.xAlloc === a.k ? '' : a.k, xPage: 0 }),
        cells: rs.map((r) => { const s = stateOf[r.id], hit = matches(r); return { title: r.id + ' · ' + STY[s][0], pick: () => this.setState({ xPick: r.id }), style: STY[s][1].replace('display:inline-block', 'display:block') + ';cursor:pointer;flex:none;opacity:' + (hit ? 1 : 0.15) + (S.xPick === r.id ? ';outline:2px solid #12171C;outline-offset:2px' : '') }; })
      };
    });
    const legend = ['alone', 'open', 'review', 'approved', 'attn'].map((k) => ({ label: STY[k][0], shape: STY[k][1], n: counts[k] }));
    const alloc = ALLOCS.filter((a) => S.scope === 'all' || a.k === S.scope).map((a) => {
      const rs = U.reqs.filter((r) => r.alloc === a.k), n = (k) => rs.filter((r) => stateOf[r.id] === k).length;
      return { name: a.k, total: rs.length, alone: n('alone'), open: n('open'), review: n('review'), approved: n('approved'), attn: n('attn'), clusters: U.cl.filter((c) => c.alloc === a.k).length, pick: () => this.setState({ xAlloc: S.xAlloc === a.k ? '' : a.k, xPage: 0 }), rowStyle: 'display:grid;grid-template-columns:minmax(0,1.4fr) repeat(7,minmax(0,.7fr));gap:8px;padding:8px 16px;border-bottom:1px solid #E3E7EA;align-items:center;' + (S.xAlloc === a.k ? 'background:#F1F6FF;' : '') };
    });
    const list = U.reqs.filter(matches);
    const PAGE = 8, pages = Math.max(1, Math.ceil(list.length / PAGE)), page = Math.min(S.xPage, pages - 1);
    const rows = list.slice(page * PAGE, page * PAGE + PAGE).map((r) => ({ id: r.id, alloc: r.alloc, state: STY[stateOf[r.id]][0], shape: STY[stateOf[r.id]][1], cluster: r.cid || 'none', text: r.text, pick: () => this.setState({ xPick: r.id }), on: S.xPick === r.id, style: 'text-align:left;display:grid;grid-template-columns:160px 20px minmax(0,1fr) 90px;gap:10px;align-items:center;min-height:44px;padding:6px 12px;border-radius:6px;cursor:pointer;border:' + (S.xPick === r.id ? '2px solid var(--accent)' : '1px solid #D5DADE') + ';background:#FFFFFF;' }));
    const pk = S.xPick && REQ_BY[S.xPick] ? REQ_BY[S.xPick] : null;
    const pc = pk && pk.cid ? CL_BY[pk.cid] : null;
    return {
      xChips: chips, groups, legend, allocRows: alloc,
      xRows: rows, xInfo: list.length ? 'Showing ' + (page * PAGE + 1) + ' to ' + (page * PAGE + rows.length) + ' of ' + list.length.toLocaleString('en-US') : 'Nothing matches',
      xPageText: 'Page ' + (page + 1) + ' of ' + pages, xPrevDisabled: page === 0, xNextDisabled: page >= pages - 1,
      xPrev: () => this.setState({ xPage: Math.max(0, page - 1) }), xNext: () => this.setState({ xPage: Math.min(pages - 1, page + 1) }),
      xHasAlloc: !!S.xAlloc, xAllocName: S.xAlloc, xClearAlloc: () => this.setState({ xAlloc: '', xPage: 0 }),
      xShowPick: !!pk,
      xp: pk ? {
        id: pk.id, alloc: pk.alloc, owner: pk.owner, tok: paintOnly(pk.text), stateLabel: STY[stateOf[pk.id]][0], shape: STY[stateOf[pk.id]][1],
        inCluster: !!pc, clusterLine: pc ? pc.id + ' · ' + pc.title + ' · ' + STATUS_LABEL[statusOf(S, pc)] : 'Not in any cluster. Four methods compared it with every other requirement in its allocation and found nothing close.',
        open: pc ? () => this.setState({ view: 'review', selected: pc.id, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [pc.id]: S.liveVer[pc.id] || 0 }) }) : () => {},
        history: reqHistory(S, pk.id)
      } : { id: '', alloc: '', owner: '', tok: [], stateLabel: '', shape: '', inCluster: false, clusterLine: '', open: () => {}, history: [] }
    };
  }
  /* ----- methods and metrics (scaled to the project) ----- */
  valsMethods(S) {
    const MECH = MARK.mech[1], AI = MARK.ai[1];
    const raw = [
      ['Text match (fuzzy)', MECH, 0.61, '0.55–0.67', 0.48, 0.21, 3904], ['Keyword overlap (TF-IDF)', MECH, 0.58, '0.52–0.64', 0.52, 0.18, 3904],
      ['Embedding model A', MECH, 0.71, '0.66–0.76', 0.84, 0.09, 1126], ['Embedding model B', MECH, 0.69, '0.64–0.74', 0.81, 0.11, 1126],
      ['Cross-encoder re-score', MECH, 0.78, '0.73–0.83', 0.76, 0.07, 1126], ['Combined score', MECH, 0.86, '0.81–0.90', 0.80, 0.04, 1126], ['AI judge', AI, 0.83, '0.74–0.90', 0.71, 0.08, CLUSTERS.filter((c) => c.ai.mode === 'judge').length]
    ];
    const bar = (v) => 'height:10px;background:#256ABF;border-radius:0 5px 5px 0;width:' + v * 100 + '%';
    const sources2 = raw.map(([name, shape, p, range, r, ece, n]) => ({ name, shape, p: p.toFixed(2), range, r: r.toFixed(2), ece: ece.toFixed(2), n: n.toLocaleString('en-US'), pBar: bar(p), rBar: bar(r) }));
    const cont = [['118', 'Both suggest a merge', 'Strongest candidates'], ['64', 'Mechanical only', 'Check for lookalikes'], ['31', 'AI only', 'Check for invented links'], ['39', 'Neither', 'Left alone']].map(([n, label, sub]) => ({ n, label, sub }));
    const acc = [['Under 0.50', 0.31], ['0.50 to 0.70', 0.52], ['0.70 to 0.90', 0.74], ['Over 0.90', 0.93]].map(([bin, v]) => ({ bin, v: Math.round(v * 100) + '%', bar: bar(v) }));
    const infos = this.allInfos(S), decs = infos.filter((x) => x.dec);
    const followed = decs.filter((x) => x.dec.vs === 'Agreed with AI').length, over = decs.filter((x) => x.dec.vs === 'Overrode AI').length;
    const edited = decs.filter((x) => x.dec.share && x.dec.share.bucket !== 'as-is').length;
    const undone = S.events.filter((e) => /Reopened|Undo/.test(e.text)).length;
    const live = [['Decisions made', decs.length + ' of ' + infos.length], ['Agreed with the AI', String(followed)], ['Overrode the AI (note required)', String(over)], ['Edited an AI draft', String(edited)], ['Decisions reopened this session', String(undone)]].map(([k, v]) => ({ k, v }));
    const all = infos.map((x) => x.c.guards).join('').split('');
    const nP = all.filter((x) => x === 'p').length, nW = all.filter((x) => x === 'w').length, nF = all.filter((x) => x === 'f').length;
    const quotes = infos.reduce((n, x) => n + x.c.ai.quotes.length, 0);
    const blocked = infos.filter((x) => x.c.ai.mode === 'judge' && x.c.guards.indexOf('f') >= 0).length;
    const guardStats = [['Checks run', all.length.toLocaleString('en-US')], ['Passed', nP.toLocaleString('en-US') + ' (' + Math.round((nP / all.length) * 100) + '%)'], ['Warnings', String(nW)], ['Blocked a merge', String(nF)], ['AI judgements stopped by a guard', blocked + ' of ' + infos.filter((x) => x.c.ai.mode === 'judge').length], ['Quoted evidence found verbatim', quotes + ' of ' + quotes]].map(([k, v]) => ({ k, v }));
    const cats = ['A', 'B', 'C'].map((l) => { const g = decs.filter((x) => x.c.lane === l); return { k: 'Lane ' + l + ' decided', v: g.length + ' of ' + infos.filter((x) => x.c.lane === l).length }; });
    return { sources2, cont, acc, live, guardStats, laneStats: cats };
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
    const tabStyle = (on) => 'min-height:44px;padding:0 14px;border-radius:6px;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#8C98A3') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';';
    const open = (cid) => () => this.setState({ view: 'review', selected: cid, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [cid]: S.liveVer[cid] || 0 }) });
    return {
      logTabs: [['ledger', 'Decision ledger'], ['chain', 'Event chain']].map(([k, label]) => ({ label, pressed: S.logTab === k ? 'true' : 'false', pick: () => this.setState({ logTab: k }), style: tabStyle(S.logTab === k) })),
      isLedger: S.logTab === 'ledger', isChain: S.logTab === 'chain',
      lrows: all.slice(page * PAGE, page * PAGE + PAGE).map((r) => ({ cid: r.cid, title: r.title, when: r.when, decision: r.decision, reason: r.reason, by: r.by, vs: r.vs, state: r.state, note: r.note || 'No note', share: r.share || '', hasShare: !!r.share, open: open(r.cid) })),
      lInfo: all.length ? 'Showing ' + (page * PAGE + 1) + ' to ' + Math.min(all.length, page * PAGE + PAGE) + ' of ' + all.length : 'No decisions match', lPageText: 'Page ' + (page + 1) + ' of ' + pages,
      lPrevDisabled: page === 0, lNextDisabled: page >= pages - 1, lPrev: () => this.setState({ lpage: Math.max(0, page - 1) }), lNext: () => this.setState({ lpage: Math.min(pages - 1, page + 1) }),
      lfilterV: S.lfilter, onLfilter: (e) => this.setState({ lfilter: e.target.value, lpage: 0 }),
      eventRows, tamper: S.tamper, evNote: 'Newest first. Showing the latest ' + Math.min(40, ev.length) + ' of ' + ev.length + ' entries.',
      toggleTamper: () => this.setState({ tamper: !S.tamper, verified: '' }),
      verifyChain: () => {
        let prev = '00000000', result = 'ok';
        for (const e of ev) {
          const payload = [e.seq, e.type, e.actor, e.text, e.target].join('|');
          if (e.prev !== prev || h32(e.prev + payload) !== e.hash) { result = 'fail:' + e.seq; break; }
          prev = e.hash;
        }
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
    const out = SLOT_KEYS.filter((k) => req[k] !== 'none' && !(k === 'PE' && req[k] === 'sample') && !(k === 'NU' && req[k] === 'sample')).map((k) => ({ label: SLOT_NAME[k] }));
    const samples = SLOT_KEYS.filter((k) => req[k] === 'sample').map((k) => ({ label: SLOT_NAME[k] + ' only if the 20% sample picks the cluster' }));
    const sel = (on) => 'min-height:44px;padding:0 14px;border-radius:6px;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #8C98A3') + ';background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';';
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
    const FM = [['sphinx', 'Sphinx-Needs (reStructuredText)', 'Needs-as-code pages with trace tables', ['requirements.rst', 'traceability.rst', 'change-record.rst']], ['strictdoc', 'StrictDoc (SDoc)', 'Requirements document with HTML or PDF output', ['requirements.sdoc', 'change-record.sdoc']], ['docx', 'Word (.docx)', 'Built from a Word template', ['Requirements-' + S.baseId + '.docx']], ['reqif', 'ReqIF 1.2', 'Round trip back to MSOSA', ['requirements.reqif']]];
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
      msgs, hasMsgs: msgs.length > 0, noMsgs: msgs.length === 0, chips: CHIPS.map(([k, label]) => ({ label, onClick: ask(k, label), style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-size:13px;border:1px solid #0B6E99;background:#E3F4FB;color:#0B4F6E;font-weight:600;' })),
      chatV: S.chatInput, onChat: (e) => this.setState({ chatInput: e.target.value }),
      sendChat: () => { const t = S.chatInput.trim(); if (!t) return; const i = intentOf(t); if (!i) { this.setState({ chatInput: '', chat: Object.assign({}, S.chat, { [cid]: log.concat([{ who: 'you', text: t }, { who: 'bot', text: 'In this prototype I answer the six suggested questions. In the real tool I would answer this from the project, as you, using only what you may read.', quotes: [], draft: '', refs: '' }]) }) }); return; } this.setState({ chatInput: '' }); push(t, reply(i)); },
      sendDisabled: S.chatInput.trim().length === 0, closeChat: () => this.setState({ chatOpen: false }),
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
    v.isOverview = S.view === 'overview';
    v.isReview = S.view === 'review';
    v.isExplorer = S.view === 'explorer';
    v.isMethods = S.view === 'methods';
    v.isAudit = S.view === 'audit';
    v.isPolicy = S.view === 'policy';
    v.isExport = S.view === 'export';
    Object.assign(v, this.valsOpen(S), this.valsImport(S), this.valsVerify(S), this.valsShell(S), this.valsGlossary(S));
    if (v.inWorkspace) {
      if (v.isOverview) Object.assign(v, this.valsOverview(S));
      if (v.isReview) Object.assign(v, this.valsQueue(S), this.valsDetail(S));
      if (v.isExplorer) Object.assign(v, this.valsExplorer(S));
      if (v.isMethods) Object.assign(v, this.valsMethods(S));
      if (v.isAudit) Object.assign(v, this.valsAudit(S));
      if (v.isPolicy) Object.assign(v, this.valsPolicy(S));
      if (v.isExport) Object.assign(v, this.valsExport(S));
      Object.assign(v, this.valsAssist(S));
    }
    return v;
  }
