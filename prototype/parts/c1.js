  get S() { return Object.assign({}, DEFAULTS, this.state || {}); }
  person(S) { return PEOPLE.find((p) => p.k === S.person) || PEOPLE[0]; }
  viewLens(S) { return S.preview || this.person(S).lens || 'SE'; }
  canAct(S) { return this.person(S).role !== 'observer' && !S.preview; }
  blindOn(S) { return S.blind === null ? this.viewLens(S) === 'NU' : S.blind; }
  mk(list, type, actor, text, target) {
    const all = EV_SEED.concat(list);
    const prev = all[all.length - 1].hash;
    const seq = all.length + 1;
    const payload = [seq, type, actor, text, target].join('|');
    return list.concat([{ seq, type, actor, text, target, time: new Date().toTimeString().slice(0, 8), prev, hash: h32(prev + payload), payload }]);
  }
  bump(S, cid) { const v = (S.liveVer[cid] || 0) + 1; return { liveVer: Object.assign({}, S.liveVer, { [cid]: v }), openVer: Object.assign({}, S.openVer, { [cid]: v }) }; }
  info(S, c) {
    const P = this.person(S), lens = P.lens, lead = P.role === 'lead';
    const st = statusOf(S, c), dec = decOf(S, c.id);
    let me = false, wait = false, q = null;
    if (dec) q = signState(S, c, dec);
    if (P.role !== 'observer') {
      if (st === 'open' || st === 'claimed') me = lens === 'SE';
      else if (dec && (st === 'decided' || st === 'review')) {
        const own = dec.by === P.name;
        const need = (!own && q.missing.indexOf(lens) >= 0) || (lead && (q.missing.indexOf('OWN') >= 0 || q.missing.indexOf('ADJ') >= 0));
        me = need; wait = !need;
      } else if (attention(st)) me = lead;
    }
    return { c, st, dec, q, me, wait, attn: attention(st) };
  }
  allInfos(S) { return universe(S).order.map((c) => this.info(S, c)); }
  openCount(S) { return this.allInfos(S).filter((x) => x.me).length; }
  /* ----- open and import ----- */
  chipStyle(k) { return 'font-family:IBM Plex Mono,monospace;font-size:11px;padding:2px 8px;border-radius:3px;white-space:nowrap;' + TRUST[k].style; }
  goImport(src) { return () => this.setState({ source: src, view: 'import', impStep: 'verify', mapEdit: '', yamlOpen: false }); }
  valsOpen(S) {
    const dropFile = FILES.find((f) => f.f === S.drop);
    const cardStyle = (later) => 'text-align:left;background:#FFFFFF;border-radius:8px;padding:16px;display:flex;flex-direction:column;gap:8px;cursor:pointer;min-height:44px;' + (later ? 'border:1px dashed #6B7782;color:#3C4852;' : 'border:1px solid #BAC3CA;');
    return {
      sources: SOURCES.map((s) => ({ ...s, trustStyle: this.chipStyle(s.trust), btn: s.later ? 'See how' : 'Choose', style: cardStyle(s.later), pick: s.later ? () => this.setState({ openNote: S.openNote === 'mdzip' ? '' : 'mdzip' }) : this.goImport(s.k) })),
      trustLegend: ['Structured', 'Tabular', 'Parsed', 'Extracted'].map((k) => ({ name: k, means: TRUST[k].means, style: this.chipStyle(k) })),
      files: FILES.map((f) => ({ name: f.f, on: S.drop === f.f, style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-family:IBM Plex Mono,monospace;font-size:13px;background:' + (S.drop === f.f ? '#F1F6FF' : '#FFFFFF') + ';border:' + (S.drop === f.f ? '2px solid var(--accent)' : '1px solid #8C98A3') + ';', pick: () => this.setState({ drop: f.f, openNote: f.src === 'mdzip' ? 'mdzip' : '' }) })),
      dropShown: !!dropFile, dropEmpty: !dropFile, dropRec: dropFile ? dropFile.rec : '', dropTrust: dropFile ? dropFile.trust : 'Later',
      dropTrustName: dropFile ? (dropFile.trust === 'Later' ? 'Not read directly yet' : dropFile.trust) : '',
      dropTrustStyle: this.chipStyle(dropFile ? dropFile.trust : 'Later'), dropUsable: !!dropFile && dropFile.src !== 'mdzip',
      useDrop: () => { if (dropFile && dropFile.src !== 'mdzip') this.goImport(dropFile.src)(); },
      mdzipHelp: S.openNote === 'mdzip', useReqif: this.goImport('reqif'),
      recents: RECENTS.map((r) => ({ ...r, pick: this.goImport(r.k) })),
      openSample: this.goImport('sample'),
      people: PEOPLE.map((p) => ({ name: p.name, role: ROLE_NAME[p.role], lens: p.lens ? SLOT_NAME[p.lens] + ' lens' : 'No lens', on: S.person === p.k, pick: () => this.setState({ person: p.k, preview: '' }), style: 'text-align:left;display:flex;flex-direction:column;gap:2px;padding:10px 12px;border-radius:6px;cursor:pointer;min-height:44px;border:' + (S.person === p.k ? '2px solid var(--accent)' : '1px solid #BAC3CA') + ';background:' + (S.person === p.k ? '#F1F6FF' : '#FFFFFF') + ';' })),
      meName: this.person(S).name
    };
  }
  /* effective mapping for one slot: the person's choice wins and is labelled Exact; otherwise the proposal */
  impEff(S, slot) {
    const I = IMPORTS[S.source] || IMPORTS.sample;
    const o = S.mapOver[S.source + ':' + slot];
    if (o !== undefined) return o ? [o, 'Exact'] : [null, 'Low'];
    return I.map[slot];
  }
  impCell(I, col, ri, slot) {
    const i = I.cols.indexOf(col);
    if (i < 0) return '—';
    let v = String(I.rows[ri][i] == null ? '' : I.rows[ri][i]);
    if (slot === 'verification' && I.vmap && I.vmap[col] && I.vmap[col][v]) v = I.vmap[col][v];
    if (I.strip && I.strip.indexOf(col) >= 0) v = v.replace(/<[^>]+>/g, '');
    return v.trim() ? v : '—';
  }
  yamlFor(S) {
    const I = IMPORTS[S.source] || IMPORTS.sample;
    const L = ['# PROPOSED by the app. Not trusted until a person confirms it (the "Confirm mapping and import" button).', 'profile: ' + I.profile, 'adapter: ' + I.adapter, 'namespace: ' + I.ns + '   # keep stable across re-imports: it is part of every ID', 'containers: ' + I.containers, 'fields:'];
    const none = [];
    SLOTS.forEach(([slot]) => {
      const col = this.impEff(S, slot)[0];
      if (!col) { none.push(slot); return; }
      let extra = '';
      if (slot === 'verification' && I.vmap && I.vmap[col]) extra = ', map: {' + Object.keys(I.vmap[col]).map((k) => k + ': ' + I.vmap[col][k]).join(', ') + '}';
      if (slot === 'text' && I.strip && I.strip.indexOf(col) >= 0) extra = ', strip_markup: true';
      L.push('  ' + (slot + ':').padEnd(14) + '{from: "' + col + '"' + extra + '}');
    });
    if (none.length) L.push('# no source field for: ' + none.join(', ') + '  (these stay empty slots, never guesses)');
    if (I.query) L.push('# source option (not part of the profile): query = ' + I.query);
    return L.join('\n');
  }
  valsImport(S) {
    const I = IMPORTS[S.source] || IMPORTS.sample;
    const conf = { Exact: 'background:#E1F2E7;color:#14502B;', High: 'background:#E1F2E7;color:#14502B;', Medium: 'background:#FFF0D2;color:#6B3D00;', Low: 'background:#FDE3E0;color:#7A1510;' };
    const base = 'font-family:IBM Plex Mono,monospace;font-size:12px;text-align:center;padding:3px 0;border-radius:4px;';
    const nJ = CLUSTERS.filter((c) => c.ai.mode === 'judge').length, nD = CLUSTERS.filter((c) => c.ai.mode === 'draft').length, nOver = CLUSTERS.filter((c) => c.members.length > 12).length;
    const stages = [
      ['Read and normalise', TOTAL_REQS.toLocaleString('en-US') + ' requirements; modal verbs, negations, numbers and units tagged'],
      ['Collapse exact copies', '31 exact or near-exact groups'],
      ['Block by allocation and parameter', '8 allocations, 41 parameter blocks. Only requirements in the same block are compared, so the comparison stays small and fast.'],
      ['Fuzzy and keyword candidates', '3,904 candidate pairs inside the blocks'],
      ['Embedding shortlist', '1,126 pairs kept from 3,904'],
      ['Re-score with cross-encoder and NLI', 'Both directions, 1,126 pairs'],
      ['Combine scores', 'Draft probabilities, uncalibrated until a gold set is labelled'],
      ['Cluster (average link) and label relationships', CLUSTERS.length + ' clusters; the largest has ' + Math.max.apply(null, CLUSTERS.map((c) => c.members.length)) + ' members'],
      ['Oversized check', nOver + ' clusters have more than 12 members and must be split before deciding'],
      ['AI judge on the uncertain band', nJ + ' clusters judged with quoted evidence; ' + nD + ' more only had merged wording drafted'],
      ['Guard checks', 'Ten code checks run on every AI proposal']
    ];
    const per = (k) => REQS.filter((r) => r.alloc === k).length;
    const ncl = (k) => CLUSTERS.filter((c) => c.alloc === k).length;
    const pilotOpts = ALLOCS.map((a) => ({ v: a.k, t: a.k + ' · ' + per(a.k) + ' requirements · ' + ncl(a.k) + ' clusters' }));
    const rec = ALLOCS.filter((a) => per(a.k) >= 100 && per(a.k) <= 200).map((a) => a.k);
    const scopeStyle = (on) => 'text-align:left;display:flex;flex-direction:column;gap:6px;padding:14px 16px;border-radius:8px;cursor:pointer;min-height:44px;background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #BAC3CA') + ';';
    /* ---- mapping rows ---- */
    const none = [];
    const rows = SLOTS.map(([slot, name, desc]) => {
      const [col, cf] = this.impEff(S, slot);
      if (!col) none.push(name);
      const editing = S.mapEdit === slot;
      return {
        name, desc, src: col || 'not found: empty slot', srcStyle: col ? 'font-weight:600;' : 'font-weight:600;color:#7A1510;', sample: col ? this.impCell(I, col, 0, slot) : '—',
        conf: cf, confStyle: base + conf[cf], btn: col ? 'Change' : 'Choose', btnLabel: (col ? 'Change' : 'Choose') + ' the source field for ' + name, editing, notEditing: !editing,
        sel: col || '', opts: [{ v: '', t: '(leave empty)' }].concat(I.cols.map((c) => ({ v: c, t: c }))), selLabel: 'Source field for ' + name,
        toggle: () => this.setState({ mapEdit: editing ? '' : slot }),
        onSel: (e) => this.setState({ mapOver: Object.assign({}, S.mapOver, { [S.source + ':' + slot]: e.target.value }), mapEdit: '' })
      };
    });
    /* ---- first three records, as the review screens will show them ---- */
    const idc = this.impEff(S, 'uid')[0], txc = this.impEff(S, 'text')[0], vec = this.impEff(S, 'verification')[0], alc = this.impEff(S, 'allocation')[0];
    const nVer = Object.keys(S.docVer).filter((k) => S.docVer[k]).length;
    const preview = [0, 1, 2].map((i) => ({
      id: idc ? this.impCell(I, idc, i, 'uid') : '—', text: txc ? this.impCell(I, txc, i, 'text') : '—', ver: vec ? this.impCell(I, vec, i, 'verification') : '—', alloc: alc ? this.impCell(I, alc, i, 'allocation') : '—',
      fid: I.fidelity + (S.source === 'doc' && S.docVer[i] ? ' · verified' : '')
    }));
    /* ---- dry-run report ---- */
    const cnt = I.counts || { read: TOTAL_REQS, kept: TOTAL_REQS, rej: 0, filt: 0, why: '' };
    const dry = [];
    const add = (ok, text) => dry.push({ isPass: ok, isWarn: !ok, isFail: false, isInfo: false, tag: ok ? 'Pass' : 'Needs you', text });
    add(true, 'Every row accounted for: ' + cnt.read.toLocaleString('en-US') + ' read = ' + cnt.kept.toLocaleString('en-US') + ' kept + ' + cnt.rej + ' rejected + ' + cnt.filt + ' filtered' + (cnt.filt ? ' (' + cnt.why + ')' : ''));
    if (S.source === 'doc') {
      const inv = DOC_ITEMS.filter((it, i) => it.invented && !S.docIds[i]).length;
      add(inv === 0, inv === 0 ? 'Every record has an ID' : inv + ' record has no ID in the document, so one was invented and is labelled as invented');
      const un = DOC_ITEMS.length - nVer;
      add(un === 0, un === 0 ? 'All ' + DOC_ITEMS.length + ' records verified against the page' : un + ' of ' + DOC_ITEMS.length + ' records are not verified yet. They come in, and stay marked Extracted.');
    } else add(true, 'No duplicate IDs; no ID had to be invented');
    add(false, 'Profile is proposed: confirm it');
    add(none.length === 0, none.length === 0 ? 'Every slot has a source field' : none.length + ' slot' + (none.length > 1 ? 's have' : ' has') + ' no source field: ' + none.join(', '));
    if (!this.impEff(S, 'allocation')[0]) add(false, 'Without Allocated to, comparisons cannot be blocked by allocation: expect slower runs and more false pairs');
    add(true, I.safe);
    const nNeeds = dry.filter((d) => d.isWarn).length;
    return {
      sourceTitle: I.title,
      impFile: I.file, impProfile: I.profile, impWhere: I.where, impTrust: I.fidelity, impTrustStyle: this.chipStyle(I.fidelity), impNote: I.note, impIllustrative: !!I.illustrative,
      impQuery: I.query || '', hasQuery: !!I.query,
      crumbs: (S.source === 'doc' ? ['1 · SOURCE', '2 · VERIFY STATEMENTS', '3 · MAP FIELDS, CHOOSE SCOPE, PREPARE', '4 · WORKSPACE'] : ['1 · SOURCE', '2 · MAP FIELDS, CHOOSE SCOPE, PREPARE', '3 · WORKSPACE']).map((label, i, arr) => {
        const cur = S.source === 'doc' ? (S.impStep === 'verify' ? 1 : 2) : 1;
        const link = i < cur && i < arr.length - 1;
        return { label, link, plain: !link, sepBefore: i > 0, style: i === cur ? 'color:#12171C;font-weight:600;' : '', go: i === 0 ? () => this.setState({ view: 'open' }) : () => this.setState({ impStep: 'verify' }) };
      }),
      fields: rows, preview, dry, nNeeds, nNeedsText: nNeeds + ' item' + (nNeeds === 1 ? '' : 's') + ' need you',
      stages: stages.map(([name, detail]) => ({ name, detail })),
      yamlOpen: S.yamlOpen, yamlText: this.yamlFor(S), toggleYaml: () => this.setState({ yamlOpen: !S.yamlOpen }),
      yamlBtn: S.yamlOpen ? 'Hide profile (YAML)' : 'Save profile (YAML)',
      scopeOpts: [
        { k: 'all', name: 'Whole project', sub: TOTAL_REQS.toLocaleString('en-US') + ' requirements, ' + CLUSTERS.length + ' clusters. Use this once the pilot has set the thresholds.', on: S.scopeChoice === 'all', style: scopeStyle(S.scopeChoice === 'all'), pick: () => this.setState({ scopeChoice: 'all' }) },
        { k: 'pilot', name: 'Pilot on one allocation (recommended first)', sub: 'Review one allocation of 100 to 200 requirements end to end. It measures the real effort and calibrates the methods before the full set.', on: S.scopeChoice === 'pilot', style: scopeStyle(S.scopeChoice === 'pilot'), pick: () => this.setState({ scopeChoice: 'pilot' }) }
      ],
      pilotShown: S.scopeChoice === 'pilot', pilotOpts, pilotAlloc: S.pilotAlloc, onPilot: (e) => this.setState({ pilotAlloc: e.target.value }),
      pilotNote: 'Allocations of 100 to 200 requirements: ' + rec.join(', ') + '.',
      backToOpen: () => this.setState({ view: 'open' }),
      backFromMap: S.source === 'doc' ? () => this.setState({ impStep: 'verify' }) : () => this.setState({ view: 'open' }),
      enterWorkspace: () => this.setState({ view: 'overview', scope: S.scopeChoice === 'pilot' ? S.pilotAlloc : 'all', qPage: 0, selected: S.scopeChoice === 'pilot' ? (ORDER.find((c) => c.alloc === S.pilotAlloc) || ORDER[0]).id : S.selected })
    };
  }
  /* the "verify statements found in a document" step */
  valsVerify(S) {
    const nVer = Object.keys(S.docVer).filter((k) => S.docVer[k]).length;
    const nSel = Object.keys(S.docSel).filter((k) => S.docSel[k]).length;
    const set = (key, patch) => this.setState({ [key]: Object.assign({}, S[key], patch) });
    const items = DOC_ITEMS.map((it, i) => {
      const typed = (S.docIds[i] || '').trim(), ver = !!S.docVer[i], on = S.docFocus === i;
      const uid = it.invented && typed ? typed : it.uid;
      return {
        uid, loc: 'Found at ' + it.loc, text: it.text, sel: !!S.docSel[i], verified: ver, notVerified: !ver, invented: !!it.invented, aria: 'Select ' + uid,
        uidStyle: 'font-weight:600;font-family:IBM Plex Mono,monospace;font-size:13px;' + (it.invented && !typed ? 'color:#7A1510;' : ''),
        rowStyle: 'padding:12px 16px;border-bottom:1px solid #E3E7EA;display:flex;flex-direction:column;gap:6px;' + (on ? 'background:#F1F6FF;box-shadow:inset 4px 0 0 var(--accent);' : ''),
        invNote: typed ? 'ID typed by you' : 'ID invented: the document has none. Confirm it or type the real one.', invStyle: typed ? 'background:#E1F2E7;color:#14502B;' : 'background:#FFF0D2;color:#6B3D00;',
        idVal: typed, idLabel: 'ID for the statement at ' + it.loc,
        onId: (e) => set('docIds', { [i]: e.target.value }), toggle: () => set('docSel', { [i]: !S.docSel[i] }), focus: () => this.setState({ docFocus: i })
      };
    });
    const focus = DOC_ITEMS[S.docFocus] || DOC_ITEMS[0];
    const pageBlocks = DOC_PAGE.map((b) => {
      const sp = b.spans.map((x) => {
        const on = x.it === S.docFocus, found = x.it >= 0, ver = found && S.docVer[x.it];
        const hi = on ? 'background:#FFE08A;outline:2px solid #8A5A00;font-weight:600;' : ver ? 'background:#E1F2E7;' : found ? 'text-decoration:underline dotted #4F5B66;' : '';
        return { t: x.t, style: hi, cellStyle: 'padding:5px 7px;border-right:1px solid #6B7782;min-width:0;overflow-wrap:anywhere;' + (b.head ? 'font-weight:700;background:#EEF1F3;' : '') + hi };
      });
      return { isH: b.kind === 'h', isP: b.kind === 'p', isRow: b.kind === 'row', text: b.kind === 'h' ? b.spans[0].t : '', spans: sp, rowStyle: 'display:grid;grid-template-columns:minmax(70px,.9fr) minmax(0,2.4fr) minmax(70px,1fr);border:1px solid #6B7782;border-top:0;font-size:12px;' };
    });
    return {
      docItems: items, docFile: IMPORTS.doc.file, docCount: DOC_ITEMS.length, docVerCount: nVer, docSelCount: nSel,
      docHead: DOC_ITEMS.length + ' STATEMENTS FOUND · ' + nVer + ' VERIFIED · ' + nSel + ' SELECTED',
      docFocusLoc: 'Selected record is at ' + focus.loc, docFocusRaw: 'locator ' + focus.raw, pageBlocks,
      verifySel: () => { const v = Object.assign({}, S.docVer); Object.keys(S.docSel).forEach((k) => { if (S.docSel[k]) v[k] = true; }); this.setState({ docVer: v, docSel: {} }); },
      unverifySel: () => { const v = Object.assign({}, S.docVer); Object.keys(S.docSel).forEach((k) => { if (S.docSel[k]) delete v[k]; }); this.setState({ docVer: v, docSel: {} }); },
      selectAll: () => { const o = {}; DOC_ITEMS.forEach((it, i) => { o[i] = nSel < DOC_ITEMS.length; }); this.setState({ docSel: o }); },
      selectAllLabel: nSel < DOC_ITEMS.length ? 'Select all' : 'Clear selection',
      verifyDisabled: nSel === 0,
      toMap: () => this.setState({ impStep: 'map' }),
      toMapLabel: 'Continue with ' + DOC_ITEMS.length + ' records (' + nVer + ' verified' + (nVer < DOC_ITEMS.length ? ', ' + (DOC_ITEMS.length - nVer) + ' stay marked Extracted' : '') + ')',
      verifyBack: () => this.setState({ view: 'open' })
    };
  }
  /* ----- shell ----- */
  valsShell(S) {
    const P = this.person(S), lead = P.role === 'lead';
    const items = [['overview', 'Overview'], ['review', 'Review queue'], ['explorer', 'All requirements'], ['methods', 'Methods and metrics'], ['audit', 'Decisions and audit'], ['policy', 'Sign-off policy'], ['export', 'Export to documents']];
    const nMe = this.openCount(S);
    const nav = items.map(([k, label]) => {
      const on = S.view === k;
      return {
        label, onClick: () => this.setState({ view: k }), current: on ? 'page' : 'false', hasCount: k === 'review', count: String(nMe),
        style: 'text-align:left;display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:44px;padding:0 12px;border-radius:6px;border:0;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';background:' + (on ? '#2B4259' : 'transparent') + ';color:#E8EDF1'
      };
    });
    const switcher = PEOPLE.map((p) => ({ name: p.name.split(' ')[0], sub: p.lens ? p.lens + (p.role === 'lead' ? ' · lead' : '') : 'observer', pressed: S.person === p.k ? 'true' : 'false', onClick: () => this.setState({ person: p.k, preview: '', just: '' }), style: 'text-align:left;min-height:44px;padding:4px 10px;border-radius:6px;cursor:pointer;display:flex;flex-direction:column;border:1px solid ' + (S.person === p.k ? '#FFFFFF' : '#33475A') + ';background:' + (S.person === p.k ? '#FFFFFF' : 'transparent') + ';color:' + (S.person === p.k ? '#14202B' : '#E8EDF1') + ';font-weight:' + (S.person === p.k ? 600 : 500) }));
    const previews = [{ k: '', label: 'My own lens' }].concat(LENSES.map((l) => ({ k: l.k, label: l.name }))).map((o) => ({ label: o.label, pressed: S.preview === o.k ? 'true' : 'false', onClick: () => this.setState({ preview: o.k }), style: 'text-align:left;min-height:36px;padding:0 10px;border-radius:6px;cursor:pointer;font-size:13px;border:1px solid ' + (S.preview === o.k ? '#FFFFFF' : '#33475A') + ';background:' + (S.preview === o.k ? '#FFFFFF' : 'transparent') + ';color:' + (S.preview === o.k ? '#14202B' : '#E8EDF1') }));
    const sel = CL_BY[S.selected];
    const decSel = sel && decOf(S, sel.id);
    const sim = [
      { label: 'A teammate claims the open cluster', hint: 'Shows the soft-claim chip.', disabled: !sel, onClick: () => this.setState({ claims: Object.assign({}, S.claims, { [sel.id]: { by: 'Priya Raman', lens: 'PE', mins: 0 } }) }) },
      { label: 'A teammate changes the open cluster', hint: 'Bumps its version under you.', disabled: !sel, onClick: () => { const v = (S.liveVer[sel.id] || 0) + 1; this.setState({ liveVer: Object.assign({}, S.liveVer, { [sel.id]: v }), events: this.mk(S.events, 'human', 'Priya Raman · PE', 'Added a note on the cluster (simulated)', sel.id) }); } },
      { label: 'The source drifts under a decision', hint: 'Needs a decided cluster.', disabled: !sel || !decSel, onClick: () => this.setState({ stale: Object.assign({}, S.stale, { [sel.id]: { req: sel.members[0].id, when: TODAY, what: 'The source text of ' + sel.members[0].id + ' changed in the model after this decision was made.', hash: h32(sel.id + 'drift') } }), events: this.mk(S.events, 'mechanical', 'Refresh', 'Source drift detected on ' + sel.members[0].id, sel.id) }) }
    ].map((x) => ({ ...x, style: 'text-align:left;min-height:44px;padding:4px 10px;border-radius:6px;cursor:pointer;display:flex;flex-direction:column;border:1px dashed #6E8296;background:transparent;color:#E8EDF1;' }));
    const scopeTxt = S.scope === 'all' ? 'Whole project' : 'Pilot · ' + S.scope;
    return {
      projectName: 'Reference air vehicle',
      nav, switcher, previews, sim, isLead: lead,
      meName: P.name, meLens: P.lens ? SLOT_NAME[P.lens] + ' lens' : 'No lens', meRole: ROLE_NAME[P.role],
      titleCells: [
        { label: 'PROJECT', value: 'Reference air vehicle (synthetic)' },
        { label: 'SCOPE', value: scopeTxt },
        { label: 'BASELINE', value: 'None · pre-baseline' },
        { label: 'STATUS', value: 'DRAFT' },
        { label: 'SIGNED IN AS', value: P.name + ' · ' + (S.preview ? 'previewing ' + S.preview : P.lens || 'observer') }
      ],
      chatToggle: () => this.setState({ chatOpen: !S.chatOpen }),
      chatLabel: S.chatOpen ? 'Hide the assistant' : 'Ask the assistant',
      chatPressed: S.chatOpen ? 'true' : 'false',
      openGlossary: () => this.setState({ glossary: true }),
      closeProject: () => this.setState({ view: 'open', chatOpen: false })
    };
  }
  laneBadge(l) {
    const c = { A: 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;', B: 'background:#FFF0D2;color:#6B3D00;border:1px solid #A15C00;', C: 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;' }[l];
    return 'align-self:flex-start;font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:600;letter-spacing:.04em;padding:2px 8px;border-radius:4px;' + c;
  }
  /* ----- overview ----- */
  valsOverview(S) {
    const infos = this.allInfos(S), U = universe(S), P = this.person(S);
    const lanes = [['A', 'Lane A · low risk', 'Guards pass and the methods agree. Fast triage.'], ['B', 'Lane B · needs evidence', 'A guard warns, a value differs or owners differ. Read before you decide.'], ['C', 'Lane C · conflicts', 'The requirements contradict each other. Escalate; never merge.']].map(([k, name, sub]) => {
      const mine = infos.filter((x) => x.c.lane === k);
      return { name, sub, badge: this.laneBadge(k), of: mine.length, n: mine.filter((x) => !x.dec).length };
    });
    const ramp = ['#86B6EF', '#5598E7', '#2A78D6', '#1C5CAB', '#184F95', '#14407A'];
    const nPairs = S.scope === 'all' ? 3904 : Math.round(3904 * U.reqs.length / TOTAL_REQS), nShort = Math.round(nPairs * 1126 / 3904);
    const funnel = [['Requirements read', U.reqs.length], ['Candidate pairs (inside blocks)', nPairs], ['After embedding shortlist', nShort], ['Requirements in a cluster', U.cl.reduce((s, c) => s + c.members.length, 0)], ['Clusters', U.cl.length], ['Judged by the AI', U.cl.filter((c) => c.ai.mode === 'judge').length]].map(([label, value], i) => ({
      label, value: value.toLocaleString('en-US'), bar: 'height:20px;border-radius:0 4px 4px 0;background:' + ramp[i] + ';width:' + Math.max(1.5, (value / Math.max(nPairs, U.reqs.length)) * 80) + '%'
    }));
    const signoffMeters = LENSES.map((l) => {
      let req = 0, done = 0;
      infos.forEach((x) => { if (x.dec && x.q.slots.indexOf(l.k) >= 0) { req++; if (x.q.sg[l.k]) done++; } });
      return { name: l.name, label: done + ' of ' + req + ' required', fill: 'height:8px;background:#1C5CAB;width:' + (req ? (done / req) * 100 : 0) + '%' };
    });
    const nMe = infos.filter((x) => x.me).length;
    const forMe = P.role === 'observer' ? 'You can look at everything and change nothing.' : P.lens === 'SE' ? 'clusters waiting for your decision or your SE sign-off' : 'clusters waiting for your ' + (P.lens ? SLOT_NAME[P.lens].toLowerCase() : '') + ' sign-off';
    return {
      openCount: nMe, forMe, lanes, funnel, signoffMeters,
      overviewLine: (S.scope === 'all' ? 'Sample run: ' : 'Pilot run on ' + S.scope + ': ') + U.reqs.length.toLocaleString('en-US') + ' requirements, ' + U.cl.length + ' clusters, ' + nPairs.toLocaleString('en-US') + ' candidate pairs. Every number on these screens comes from a synthetic sample, not from your files.',
      showHint: S.hint && this.props.showHints !== false,
      dismissHint: () => this.setState({ hint: false }),
      startReview: () => { const first = infos.find((x) => x.me) || infos.find((x) => !x.dec) || infos[0]; this.setState({ view: 'review', selected: first.c.id, qTab: 'me', qPage: 0 }); },
      tryGroup: () => this.setState({ view: 'review', selected: 'CL-050', qTab: 'all', qSearch: '', qLane: '', qStatus: '', qAlloc: '' }),
      tryGroupShown: S.scope === 'all' || S.scope === 'Data Recorder',
      openMap: () => this.setState({ view: 'explorer' })
    };
  }
