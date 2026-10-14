  /* ----- review queue (windowed, with facets) ----- */
  valsQueue(S) {
    const infos = this.allInfos(S), P = this.person(S);
    const PAGE = 8;
    const byTab = { me: infos.filter((x) => x.me), wait: infos.filter((x) => x.wait), attn: infos.filter((x) => x.attn), all: infos };
    const pill = (on) => 'min-height:44px;padding:0 10px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:' + (on ? 600 : 500) + ';border:1px solid ' + (on ? 'var(--accent)' : '#8C98A3') + ';background:' + (on ? '#E8F0FD' : '#FFFFFF') + ';color:#12171C;';
    const qTabs = [['me', 'For me'], ['wait', 'Waiting on others'], ['attn', 'Needs attention'], ['all', 'All']].map(([k, label]) => ({ label, count: byTab[k].length, pressed: S.qTab === k ? 'true' : 'false', pick: () => this.setState({ qTab: k, qPage: 0 }), style: pill(S.qTab === k) }));
    const q = S.qSearch.trim().toLowerCase();
    const list = (byTab[S.qTab] || infos).filter((x) => (!S.qLane || x.c.lane === S.qLane) && (!S.qStatus || x.st === S.qStatus) && (!S.qAlloc || x.c.alloc === S.qAlloc) && (!q || x.c.id.toLowerCase().indexOf(q) >= 0 || x.c.title.toLowerCase().indexOf(q) >= 0 || x.c.members.some((m) => m.id.toLowerCase().indexOf(q) >= 0 || m.text.toLowerCase().indexOf(q) >= 0)));
    const pages = Math.max(1, Math.ceil(list.length / PAGE));
    const page = Math.min(S.qPage, pages - 1);
    const shown = list.slice(page * PAGE, page * PAGE + PAGE);
    const sel = CL_BY[S.selected] ? S.selected : '';
    const rows = shown.map((x) => {
      const c = x.c, ms = membersOf(S, c), cl = claimOf(S, c.id);
      let status = STATUS_LABEL[x.st];
      if (x.st === 'review' || x.st === 'decided') status += ' · ' + x.q.have.length + ' of ' + x.q.slots.length;
      if (x.st === 'claimed') status = 'Claimed by ' + cl.by.split(' ')[0];
      const on = c.id === sel;
      return {
        id: c.id, title: c.title, lane: 'Lane ' + c.lane, laneStyle: this.laneBadge(c.lane).replace('align-self:flex-start;', ''), rel: REL_LABEL[c.rel], relStyle: CHIP + REL_STYLE[c.rel],
        status, statusStyle: CHIP + STATUS_STYLE[x.st], size: ms.length + ' members' + (spreadOf(c, ms) ? ' · ' + spreadOf(c, ms) : ''),
        current: on ? 'true' : 'false',
        pick: () => this.setState({ selected: c.id, just: '', openVer: Object.assign({}, S.openVer, { [c.id]: S.liveVer[c.id] || 0 }) }),
        style: 'text-align:left;display:flex;flex-direction:column;gap:5px;padding:10px 12px;border-radius:8px;cursor:pointer;min-height:44px;background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #BAC3CA')
      };
    });
    const total = infos.length, decided = infos.filter((x) => x.dec).length, approved = infos.filter((x) => x.st === 'approved').length;
    let mineReq = 0, mineDone = 0;
    if (P.lens) infos.forEach((x) => { if (x.dec && x.q.slots.indexOf(P.lens) >= 0) { mineReq++; if (x.q.sg[P.lens]) mineDone++; } });
    const meter = (label, a, b, color) => ({ label, text: a + ' of ' + b, fill: 'height:8px;background:' + color + ';width:' + (b ? (a / b) * 100 : 0) + '%' });
    const progress = [meter('Decided', decided, total, '#1C5CAB'), meter('Approved by every required lens', approved, total, '#1B6B3A')];
    if (P.lens) progress.push(meter('Your ' + P.lens + ' sign-offs', mineDone, mineReq, '#6A1650'));
    const opts = (arr) => arr.map(([v, t]) => ({ v, t }));
    const hasFilters = !!(S.qLane || S.qStatus || S.qAlloc || S.qSearch);
    const idxNow = infos.findIndex((x) => x.c.id === sel);
    return {
      qTabs, rows, progress, qSearchV: S.qSearch, onSearch: (e) => this.setState({ qSearch: e.target.value, qPage: 0 }),
      laneV: S.qLane, onLane: (e) => this.setState({ qLane: e.target.value, qPage: 0 }), laneOpts: opts([['', 'All lanes'], ['A', 'Lane A'], ['B', 'Lane B'], ['C', 'Lane C']]),
      statusV: S.qStatus, onStatus: (e) => this.setState({ qStatus: e.target.value, qPage: 0 }), statusOpts: opts([['', 'Any status']].concat(Object.keys(STATUS_LABEL).map((k) => [k, STATUS_LABEL[k]]))),
      allocV: S.qAlloc, onAlloc: (e) => this.setState({ qAlloc: e.target.value, qPage: 0 }), allocOpts: opts([['', 'Any allocation']].concat(ALLOCS.map((a) => [a.k, a.k]))),
      hasFilters, clearFilters: () => this.setState({ qLane: '', qStatus: '', qAlloc: '', qSearch: '', qPage: 0 }),
      qInfo: list.length ? 'Showing ' + (page * PAGE + 1) + ' to ' + (page * PAGE + shown.length) + ' of ' + list.length : 'Nothing matches',
      qPageText: 'Page ' + (page + 1) + ' of ' + pages, prevDisabled: page === 0, nextDisabled: page >= pages - 1,
      qPrev: () => this.setState({ qPage: Math.max(0, page - 1) }), qNext: () => this.setState({ qPage: Math.min(pages - 1, page + 1) }),
      emptyQ: list.length === 0,
      nextMe: () => { const mine = infos.filter((x) => x.me && x.c.id !== sel); const after = mine.find((x) => infos.indexOf(x) > idxNow) || mine[0]; if (after) this.setState({ selected: after.c.id, qTab: 'me', just: '', openVer: Object.assign({}, S.openVer, { [after.c.id]: S.liveVer[after.c.id] || 0 }) }); },
      nextMeDisabled: !infos.some((x) => x.me && x.c.id !== sel)
    };
  }
  /* ----- the selected cluster ----- */
  banner(tone, title, lines, actions) {
    const T = { info: 'background:#E8F0FD;border:1px solid #9DB8E8;color:#10337F;', warn: 'background:#FFF4D6;border:1px solid #E5C87A;color:#4A3300;', bad: 'background:#FDE3E0;border:1px solid #E8A29B;color:#6E100A;', ok: 'background:#E1F2E7;border:1px solid #9CCBAE;color:#14502B;', claim: 'background:#EDE8F8;border:1px solid #C4B6EC;color:#2D1F66;' }[tone];
    return {
      style: 'border-radius:8px;padding:12px 16px;display:flex;flex-direction:column;gap:6px;' + T, title,
      lines: (lines || []).map((t) => ({ t })), hasLines: !!(lines && lines.length),
      actions: (actions || []).map((a) => ({ label: a.label, onClick: a.fn, disabled: !!a.disabled, style: 'min-height:44px;padding:0 14px;border-radius:6px;cursor:pointer;font-weight:600;' + (a.primary ? 'background:#12171C;color:#FFFFFF;border:0;' : 'background:#FFFFFF;border:1px solid #6B7782;color:#12171C;') })), hasActions: !!(actions && actions.length)
    };
  }
  lensChecks(S, c, ms, ev, lens) {
    const same = (k) => ms.every((m) => m[k] === ms[0][k]);
    const ok = (i) => c.guards[i] === 'p';
    const text = ev.text || (c.ai.proposal || c.aiDraft || '');
    const words = text.split(/\s+/).filter(Boolean).length;
    const shallN = (text.match(/\bshall\b/gi) || []).length;
    const acr = ms.some((m) => /\bFCS\b/.test(m.text)) && ms.some((m) => /Flight Control Subsystem/.test(m.text));
    const terms = Object.keys(TERMS).filter((t) => ms.some((m) => new RegExp('\\b' + t + '\\b', 'i').test(m.text)));
    const R = {
      SE: [
        [ok(2) && ok(3) && ok(4) && ok(5) ? 'pass' : 'human', ok(2) ? 'Numbers, units, shall/should and not agree across the group.' : 'The group disagrees on a number, unit or modal verb. That is the decision to make.'],
        [same('owner') && same('alloc') ? 'pass' : 'human', same('owner') ? 'Same owner and allocation.' : 'Owners differ (' + joinOr(ms.map((m) => m.owner).filter((x, i, a) => a.indexOf(x) === i)) + '). All must approve a change.'],
        [same('verif') ? 'pass' : 'human', same('verif') ? 'Verification method is the same (' + ms[0].verif + ').' : 'Verification methods differ (' + joinOr(ms.map((m) => m.verif).filter((x, i, a) => a.indexOf(x) === i)) + '). Keep the strictest.'],
        ['human', 'Confirm trace links, rationale and allocation stay with the surviving requirement.']
      ],
      PE: [
        [c.baselined ? 'human' : 'pass', c.baselined ? 'A member is baselined. Change request ' + c.cr + ' must stay linked.' : 'No member is baselined, so normal edit control applies.'],
        ['pass', c.ai.mode === 'none' ? 'No AI was used on this group.' : 'AI record stored: model version, prompt version, inputs and output.'],
        ['pass', 'AI output cannot write to approved fields. Only a human decision can.'],
        [c.crossOwner ? 'human' : 'pass', c.crossOwner ? 'Cross-owner change: every owner must approve.' : 'One owner can approve this.']
      ],
      UX: [
        ['pass', 'Every changed number, unit, shall/should and not is highlighted in the diff.'],
        [shallN <= 1 && words <= 32 ? 'pass' : 'human', words + ' words, ' + shallN + ' "shall". ' + (shallN <= 1 && words <= 32 ? 'One thought per requirement.' : 'Consider splitting it.')],
        [acr ? 'human' : 'pass', acr ? 'Two names for one thing: "FCS" and "Flight Control Subsystem". Pick the project term.' : 'Terms match across the members.'],
        ['pass', 'Status is shown with text, not colour alone.']
      ],
      NU: [
        ['human', 'In one sentence, can you say what this requires? Write it in the box below.'],
        [terms.length ? 'human' : 'pass', terms.length ? 'Terms to look up: ' + terms.join(', ') + '.' : 'No unusual terms.'],
        ['pass', 'Reject and Skip are as easy to reach as Accept.'],
        ['pass', 'Design intent: requirement text stays on your own machines.']
      ]
    }[lens];
    const sty = { pass: 'background:#E1F2E7;color:#14502B;', fail: 'background:#FDE3E0;color:#7A1510;', human: 'background:#FFF0D2;color:#6B3D00;' };
    const lab = { pass: 'Pass', fail: 'Blocked', human: 'Needs you' };
    return { rows: R.map(([s, t]) => ({ text: t, label: lab[s], style: 'flex:none;min-width:78px;text-align:center;font-size:12px;font-weight:600;padding:2px 6px;border-radius:4px;' + sty[s] })), terms, words, shallN };
  }
  lensEvidence(S, c, ms, lens, terms) {
    const uniq = (a) => a.filter((x, i) => a.indexOf(x) === i);
    const hv = h32(c.id);
    const parent = 'SYS-0' + (100 + (parseInt(hv.slice(0, 3), 16) % 900)), vp = 1 + (parseInt(hv.slice(3, 4), 16) % 3);
    const aiRec = c.ai.mode === 'none' ? 'None used' : 'AIR-' + hv.slice(0, 4).toUpperCase();
    const R = {
      SE: [['Parameter', c.param], ['Values', joinOr(groupValues(c, ms))], ['Stricter means', dirWords(S, c)], ['Parent trace', parent + ' · ' + vp + ' verification item' + (vp > 1 ? 's' : '') + ' linked'], ['Verification', uniq(ms.map((m) => m.verif)).join(', ')], ['Allocation', c.alloc]],
      PE: [['Baseline', c.baselined ? 'Baselined (BL-2) · ' + c.cr : 'Pre-baseline'], ['Owners', uniq(ms.map((m) => m.owner)).join(', ')], ['AI record', aiRec], ['Impacted documents', c.alloc + ' requirements specification; interface control document'], ['Rule', 'Sign-offs this cluster needs are shown in the sign-off card below']],
      UX: [['Key terms', terms.length ? terms.join(', ') : 'No project-specific terms'], ['Readers', 'Test engineers and new engineers on ' + c.alloc], ['Wording length', ms.map((m) => m.text.split(/\s+/).length).join(', ') + ' words across the members'], ['Style rule', 'One "shall" and one thought per requirement']],
      NU: [['What you see first', 'Only the wording below. Source, owners and the AI answer open after your own read.'], ['Terms to look up', terms.length ? terms.map((t) => t + ' = ' + TERMS[t]).join('; ') : 'None found']]
    }[lens];
    return R.map(([k, v]) => ({ k, v }));
  }
  valsDetail(S) {
    const U = universe(S);
    let c = CL_BY[S.selected];
    if (!c || (S.scope !== 'all' && c.alloc !== S.scope)) c = U.order[0];
    const P = this.person(S), lens = this.viewLens(S), actor = this.canAct(S), lead = P.role === 'lead';
    const ms = membersOf(S, c), st = statusOf(S, c), dec = decOf(S, c.id), res = resOf(S, c);
    const ev = evaluate(S, c, ms, res);
    const blindOn = this.blindOn(S);
    const hideAI = blindOn && !dec && !S.blindDone[c.id] && c.ai.mode !== 'none';
    const rk = rankedOf(S, c, ms);
    const mi = (m) => c.members.indexOf(m);
    const q = dec ? signState(S, c, dec) : null;
    const cid = c.id;
    const setRes = (o) => this.setState({ res: Object.assign({}, S.res, { [cid]: Object.assign({}, S.res[cid] || {}, o) }) });
    const strictId = rk.length ? rk[0].m.id : '';
    const weakId = rk.length ? rk[rk.length - 1].m.id : '';
    /* header */
    const prov = [{ label: 'Mechanical methods', chip: 'background:#E4E9ED;color:#2F3B46;', shape: MARK.mech[1] }];
    if (c.ai.mode !== 'none') prov.push({ label: c.ai.mode === 'draft' ? 'AI wording draft' : 'AI judge', chip: MARK.ai[2], shape: MARK.ai[1] });
    if (dec) prov.push({ label: dec.strategy === 'own' || dec.share ? 'Human-edited' : 'Human decision', chip: MARK.human[2], shape: MARK.human[1] });
    if (dec && dec.ownFrom === 'assistant') prov.push({ label: 'Assistant draft used', chip: MARK.bot[2], shape: MARK.bot[1] });
    const cl = claimOf(S, cid);
    const canFlip = lead && (c.dir === 'lower' || c.dir === 'higher');
    /* banners */
    const banners = [];
    if (S.preview) banners.push(this.banner('info', 'Previewing the ' + SLOT_NAME[S.preview] + ' lens', ['You see what a ' + SLOT_NAME[S.preview] + ' reviewer sees. Everything is read only while you preview.'], [{ label: 'Back to my own lens', fn: () => this.setState({ preview: '' }), primary: true }]));
    if (cl && cl.by !== P.name && !dec) banners.push(this.banner('claim', cl.by + ' (' + cl.lens + ') is looking at this cluster', [cl.mins + ' minute' + (cl.mins === 1 ? '' : 's') + ' ago. A soft claim expires after 15 minutes and never locks anyone out. If you both decide, the second save is stopped and offered as a sibling version.']));
    if ((S.liveVer[cid] || 0) > (S.openVer[cid] || 0)) banners.push(this.banner('warn', 'This cluster changed after you opened it', ['Priya Raman added a note while you were reading. Reload so that you decide on what is current. Deciding is paused until you do.'], [{ label: 'Reload the cluster', fn: () => this.setState({ openVer: Object.assign({}, S.openVer, { [cid]: S.liveVer[cid] || 0 }) }), primary: true }]));
    const stl = staleOf(S, cid);
    if (stl) banners.push(this.banner('warn', 'Stale: the source changed after this decision', [stl.what, 'The earlier decision and its sign-offs are kept in the record, but they no longer count. Decide again on the current wording (reason code R-SRC).'], [{ label: 'Reopen for review', fn: () => this.setState({ stale: Object.assign({}, S.stale, { [cid]: null }), dec: Object.assign({}, S.dec, { [cid]: null }), sign: Object.assign({}, S.sign, { [cid]: {} }), res: Object.assign({}, S.res, { [cid]: { reason: 'R-SRC' } }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'observer'), 'Reopened after source change (R-SRC)', cid), ...this.bump(S, cid) }), primary: true, disabled: !actor }]));
    const dsp = disputeOf(S, cid);
    if (dsp) {
      const lines = [dsp.by + ' (' + dsp.lens + ') on ' + dsp.at + ': "' + dsp.note + '"', 'Sign-offs are paused. The adjudicator decides and the dissent stays in the record whichever way it goes.'];
      const noteOk = (S.adjNote[cid] || '').trim().length >= 12;
      const acts = lead && actor ? [
        { label: 'Uphold the decision', fn: () => this.setState({ objections: Object.assign({}, S.objections, { [cid]: null }), events: this.mk(S.events, 'human', P.name + ' · adjudicator', 'Upheld the decision; dissent from ' + dsp.by + ' kept. Note: ' + S.adjNote[cid].trim(), cid), ...this.bump(S, cid) }), primary: true, disabled: !noteOk },
        { label: 'Accept the objection and reopen', fn: () => this.setState({ objections: Object.assign({}, S.objections, { [cid]: null }), dec: Object.assign({}, S.dec, { [cid]: null }), sign: Object.assign({}, S.sign, { [cid]: {} }), events: this.mk(S.events, 'human', P.name + ' · adjudicator', 'Accepted the objection from ' + dsp.by + '; decision reopened. Note: ' + S.adjNote[cid].trim(), cid), ...this.bump(S, cid) }), disabled: !noteOk }
      ] : [];
      const b = this.banner('bad', 'Disagreement: ' + dsp.lens + ' has objected', lines, acts);
      b.hasAdj = lead && actor; b.adjV = S.adjNote[cid] || ''; b.onAdj = (e) => this.setState({ adjNote: Object.assign({}, S.adjNote, { [cid]: e.target.value }) });
      b.adjHelp = noteOk ? '' : 'The adjudicator writes a note of at least 12 characters first.';
      banners.push(b);
    }
    const sb = sibsOf(S, cid);
    if (sb) {
      const lines = sb.map((s) => s.rev + ' by ' + s.by + ' (' + s.lens + '): ' + s.text);
      const pickSib = (s, o) => () => { const d = Object.assign({}, dec, { text: s.text, revs: dec.revs.concat([{ rev: 'R4', how: 'human', text: s.text, by: P.name, at: TODAY, note: 'Picked ' + s.rev + ' over ' + o.rev + '. The other version is kept as dissent.' }]), dissent: o.rev + ' by ' + o.by }); this.setState({ sib: Object.assign({}, S.sib, { [cid]: null }), dec: Object.assign({}, S.dec, { [cid]: d }), events: this.mk(S.events, 'human', P.name + ' · ' + P.lens, 'Picked ' + s.rev + ' over ' + o.rev + ' (two edits made at the same time)', cid), ...this.bump(S, cid) }); };
      banners.push(this.banner('claim', 'Two people edited this at the same time', ['Both edits are kept as sibling versions of the same revision. Neither overwrote the other. Pick one; the other stays in the record as dissent.'].concat(lines), [{ label: 'Keep ' + sb[0].rev, fn: pickSib(sb[0], sb[1]), primary: true, disabled: !actor }, { label: 'Keep ' + sb[1].rev, fn: pickSib(sb[1], sb[0]), disabled: !actor }]));
    }
    if (st === 'oversized') banners.push(this.banner('bad', 'Too big to resolve as one group', [ms.length + ' members is over the limit of 12. Peel out the members that do not belong (use Peel out in the table). Deciding unlocks at 12 or fewer.']));
    const rr = SEED.rerun[cid];
    if (rr && dec && !S.sibNote[cid]) banners.push(this.banner('claim', 'A later AI run arrived as a separate version (' + rr.rev + ')', [rr.note, rr.rev + ': ' + rr.text], [{ label: 'Dismiss', fn: () => this.setState({ sibNote: Object.assign({}, S.sibNote, { [cid]: true }) }), primary: true }]));
    if (S.just === cid && dec) banners.push(this.banner('ok', 'Decision recorded as ' + dec.rev, ['It is a draft until the lenses this cluster needs have signed. Your reason and note are saved with the revision.'], [{ label: 'Next cluster for me', fn: () => this.nextForMe(), primary: true }]));
    /* the group, every wording measured against one reference */
    const strictM = rk.length ? rk[0].m : ms[0];
    const refM = ms.find((m) => m.id === S.ref[cid]) || strictM;
    const ranked = rk.map((x) => x.m).concat(ms.filter((m) => !rk.some((x) => x.m === m)));
    const cmpOthers = ranked.filter((m) => m !== refM);
    const al = alignRows(refM.text, cmpOthers.map((m) => m.text));
    const kindChip = (k) => 'display:inline-block;width:4px;align-self:stretch;flex:none;background:' + CH_DOT[k] + ';';
    const faded = 'color:#5A6672;';
    const refBg = 'background:color-mix(in srgb,var(--accent) 6%,#FFFFFF);';
    const cellOuter = (span, bg) => 'grid-column:span ' + span + ';display:flex;align-items:center;padding:8px 3px;border-bottom:1px solid #E7ECF1;' + bg;
    const rowHead = (m, isRef) => {
      const r = rk.find((x) => x.m === m);
      const rankText = !r ? 'Cannot be ranked' : m.id === strictId && rk.length > 1 && rk[0].r !== rk[rk.length - 1].r ? 'Strictest' : m.id === weakId && rk.length > 1 && rk[0].r !== rk[rk.length - 1].r ? 'Weakest' : 'Ranked';
      const covered = dec ? dec.covers.indexOf(m.id) >= 0 : false, kept = dec ? dec.kept.indexOf(m.id) >= 0 : false;
      const survives = !dec && res.outcome === 'merge' && ev.chosen === m;
      const label = 'M' + (mi(m) + 1);
      return {
        label, id: m.id, owner: m.owner, verif: m.verif, isRef, notRef: !isRef, refAria: 'Use as reference: ' + label, peelAria: 'Peel out ' + label,
        rankText, rankStyle: CHIP + (rankText === 'Strictest' ? 'background:#E1F2E7;color:#14502B;' : rankText === 'Weakest' ? 'background:#FFF0D2;color:#6B3D00;' : rankText === 'Cannot be ranked' ? 'background:#F4F6F8;color:#4F5B66;border:1px dashed #6B7782;' : 'background:#E4E9ED;color:#2F3B46;'),
        tag: survives ? 'Survives' : covered ? 'Covered' : kept ? 'Kept separate' : '', hasTag: survives || covered || kept, tagStyle: CHIP + (survives ? 'background:#12171C;color:#FFFFFF;' : 'background:#E8F0FD;color:#123C8C;'),
        setRef: () => this.setState({ ref: Object.assign({}, S.ref, { [cid]: m.id }) }),
        canPeel: actor && !dec && ms.length > 2 && c.members.length > 2,
        peel: () => this.setState({ peeled: Object.assign({}, S.peeled, { [cid]: (S.peeled[cid] || []).concat([m.id]) }), ref: Object.assign({}, S.ref, { [cid]: S.ref[cid] === m.id ? null : S.ref[cid] }), events: this.mk(S.events, 'human', P.name + ' · ' + P.lens, 'Peeled ' + m.id + ' out of the group (it does not belong)', cid) }),
        refStr: isRef ? 'true' : 'false', rowBg: survives ? 'background:#F1F6FF;' : '', headBg: isRef ? refBg : 'background:#FFFFFF;'
      };
    };
    const summaryOf = (r) => (r.same ? 'Same words as the reference' : r.reworded ? 'Reworded' : r.nChanges + (r.nChanges === 1 ? ' change' : ' changes'));
    const chipsOf = (r, max) => r.changes.slice(0, max).map((x) => ({ text: x.text, bar: kindChip(x.kind), title: CH_NAME[x.kind] + ': ' + x.text })).concat(r.changes.length > max ? [{ text: '+' + (r.changes.length - max) + ' more', bar: kindChip('other'), title: 'More changes are shown in the wording above' }] : []);
    const segStyle = (s) => s.same ? faded : s.ghost ? 'padding:0 6px;border-radius:6px;border:1px dashed #8C98A3;color:#5A6672;text-decoration:line-through;font-size:14px;' : CH_STYLE[s.kind] + 'padding:1px 7px;border-radius:6px;font-weight:600;';
    const refSegs = []; { const toks = refM.text.split(' ').filter(Boolean), ks = kindsOfTokens(toks); let run = []; const flush = () => { if (run.length) { refSegs.push({ t: run.join(' '), style: '', ghost: false, chg: false, title: '' }); run = []; } }; toks.forEach((w, i) => { if (ks[i]) { flush(); refSegs.push({ t: w, style: SLOT_STYLE[ks[i]] + 'padding:1px 7px;border-radius:6px;', ghost: false, chg: false, title: '' }); } else run.push(w); }); flush(); }
    const mrows = [Object.assign(rowHead(refM, true), { segs: refSegs, hasSegs: true, summary: 'Everything below is compared with this wording', changes: [], hasChanges: false, cells: [] })].concat(cmpOthers.map((m, k) => {
      const r = al.rows[k];
      return Object.assign(rowHead(m, false), {
        segs: r.segs.map((s) => ({ t: s.t, style: segStyle(s), ghost: !!s.ghost, chg: !!s.chg, title: s.chg ? (s.was ? 'The reference has: ' + s.was : 'Not in the reference') : s.ghost ? 'The reference has this; this wording does not' : '' })), hasSegs: true,
        summary: summaryOf(r), changes: chipsOf(r, 4), hasChanges: r.changes.length > 0,
        cells: r.cells.map((x) => ({ text: x.text, ghost: !!x.ghost, chg: !!x.chg, empty: !!x.empty, outer: cellOuter(x.span, ''), inner: x.empty ? '' : x.same ? faded : segStyle({ ghost: x.ghost, kind: x.kind }) }))
      });
    }));
    mrows[0].cells = al.refCells.map((x) => ({ text: x.text, ghost: false, chg: false, empty: !!x.empty, outer: cellOuter(1, refBg), inner: x.kind ? SLOT_STYLE[x.kind] + 'padding:1px 3px;border-radius:4px;' : '' }));
    const trackCols = 'grid-template-columns:var(--lab) repeat(' + al.tracks.length + ',max-content);';
    /* fields other than the words */
    const FIELDS = [['owner', 'Owner'], ['level', 'Level'], ['verif', 'Verification'], ['alloc', 'Allocated to'], ['base', 'Baseline']];
    const diffF = FIELDS.filter(([k]) => ms.some((m) => m[k] !== refM[k]));
    const ledRows = [refM].concat(cmpOthers).map((m) => ({ label: 'M' + (mi(m) + 1), id: m.id, cells: diffF.map(([k]) => { const d = m[k] !== refM[k]; return { v: m[k], differs: d, style: d ? 'background:#FFF0D2;color:#6B3D00;font-weight:600;border-radius:6px;padding:2px 8px;' : faded + 'padding:2px 8px;' }; }) }));
    const ledger = { hasLedger: diffF.length > 0, noLedger: diffF.length === 0, head: diffF.map(([, n]) => ({ name: n })), rows: ledRows, cols: 'grid-template-columns:168px repeat(' + diffF.length + ',minmax(120px,1fr));' };
    const peeledN = (S.peeled[cid] || []).length;
    /* AI card */
    const ai = c.ai;
    const record = ai.mode === 'none'
      ? [['Model', 'None used'], ['Decided by', 'NLI contradiction score and the negation guard'], ['Inputs', ms.slice(0, 3).map((m) => m.id).join(', ') + (ms.length > 3 ? ' and ' + (ms.length - 3) + ' more' : '')]]
      : [['Model', 'Local judge model, version pinned (sample)'], ['Prompt', 'Template v3, members shown in two orders'], ['Runs', ai.votes || 'Wording draft only'], ['Inputs', ms.length + ' members, current versions'], ['Output', 'Structured JSON with verbatim quotes'], ['Guards', 'Ten code checks ran before you saw this']];
    const scores = [['Text match (fuzzy)', c.m.fuzzy], ['Keyword overlap (TF-IDF)', c.m.tfidf], ['Meaning (embedding)', c.m.embed], ['Cross-encoder', c.m.cross], ['A implies B (NLI)', c.m.eAB], ['B implies A (NLI)', c.m.eBA], ['Contradiction (NLI)', c.m.contra], ['Combined: same obligation', c.m.p]].map(([name, v]) => ({ name, value: v.toFixed(2), bar: 'height:10px;background:#256ABF;border-radius:0 5px 5px 0;width:' + Math.max(1, v * 100) + '%' }));
    const gs = c.guards.split('');
    const gNames = { p: ['Pass', 'font-weight:600;color:#14502B;'], w: ['Warning', 'font-weight:600;color:#6B3D00;'], f: ['Blocks merge', 'font-weight:600;color:#7A1510;'] };
    const guards = gs.map((s, i) => ({ isPass: s === 'p', isWarn: s === 'w', isFail: s === 'f', isInfo: false, name: GUARDS[i], tag: gNames[s][0], tagStyle: 'font-size:12px;' + gNames[s][1], note: c.gNotes[i] || '' }));
    const nF = gs.filter((s) => s === 'f').length, nW = gs.filter((s) => s === 'w').length;
    const aiQuotes = ai.quotes.map(([who, text]) => ({ who, text }));
    /* lens panel */
    const lc = this.lensChecks(S, c, ms, ev, lens);
    const nuKey = cid + ':nu';
    const nuText = S.lensNote[nuKey] || '';
    const lp = {
      lensName: SLOT_NAME[lens], question: LENS_Q[lens], look: LENS_LOOK[lens], means: LENS_MEANS[lens], rows: lc.rows, evidence: this.lensEvidence(S, c, ms, lens, lc.terms),
      isNU: lens === 'NU', nuV: nuText, onNu: (e) => this.setState({ lensNote: Object.assign({}, S.lensNote, { [nuKey]: e.target.value }) }),
      nuHelp: nuText.trim().length >= 20 ? 'Thank you. This is stored with your sign-off.' : 'Write at least 20 characters. If you cannot, that is a finding: sign off is blocked until a newcomer can say it back.',
      colorStyle: 'border-top:4px solid ' + { SE: '#1C5CAB', PE: '#6A3FC0', UX: '#B35A00', NU: '#1B6B3A' }[lens] + ';'
    };
    /* sign-off card */
    const forecast = dec ? q.req : required(c, { newWording: res.outcome === 'merge' && ev.newWording, weakening: res.outcome === 'merge' && ev.weakening });
    const sg = dec ? q.sg : {};
    const slotRows = SLOT_KEYS.filter((k) => forecast[k] !== 'none').map((k) => {
      const s = sg[k];
      return { name: SLOT_NAME[k], tag: forecast[k] === 'sample' ? 'sampled' : '', hasTag: forecast[k] === 'sample', state: s ? 'Signed by ' + s.by + ' · ' + s.at : dec ? 'Waiting' : 'Needed after the decision', style: 'border-radius:6px;padding:8px 12px;display:flex;flex-direction:column;gap:2px;' + (s ? 'background:#E1F2E7;border:1px solid #9CCBAE;color:#14502B;' : 'background:#FFFFFF;border:1px dashed #6B7782;color:#2F3B46;') };
    });
    const notNeeded = SLOT_KEYS.filter((k) => forecast[k] === 'none' && k !== 'ADJ').map((k) => k).join(', ');
    const mySlot = P.lens;
    const reqMine = !!mySlot && forecast[mySlot] !== 'none';
    const signedMine = !!(dec && sg[mySlot]);
    const decidedOK = dec && st !== 'stale' && st !== 'dispute' && st !== 'siblings';
    const selfMade = !!(dec && dec.by === P.name);
    const objText = S.lensNote[cid + ':obj'] || '';
    const nuBlock = mySlot === 'NU' && nuText.trim().length < 20;
    const logSign = (slot, on) => this.setState({ sign: Object.assign({}, S.sign, { [cid]: (() => { const cur = Object.assign({}, signOf(S, cid)); if (on) cur[slot] = { by: P.name, at: TODAY, rev: dec.rev }; else delete cur[slot]; return cur; })() }), events: this.mk(S.events, 'human', P.name + ' · ' + (slot === 'OWN' ? 'owners' : slot === 'ADJ' ? 'adjudicator' : P.lens), (on ? 'Signed off as ' : 'Withdrew sign-off as ') + SLOT_NAME[slot] + (slot === 'NU' && on ? ' (explained back)' : ''), cid), ...this.bump(S, cid) });
    const sgv = {
      slots: slotRows, notNeeded: notNeeded ? 'Not needed on this cluster: ' + notNeeded + '.' : '',
      revLine: dec ? 'Sign-offs bind to revision ' + dec.rev + ' (hash ' + h32(cid + dec.text + dec.rev) + '). Any change to the decision clears them.' : 'No decision yet. Sign-offs open once a decision exists.',
      canSign: !!(actor && decidedOK && reqMine && !signedMine && !selfMade), signLabel: 'Sign off as ' + (mySlot ? SLOT_NAME[mySlot] : ''), signDisabled: nuBlock, doSign: () => logSign(mySlot, true),
      signHelp: nuBlock ? 'New user sign-off needs your explain-it-back sentence in the lens panel.' : 'Your sign-off says: ' + LENS_MEANS[mySlot || 'SE'],
      canWithdraw: !!(actor && dec && signedMine), doWithdraw: () => logSign(mySlot, false),
      canObject: !!(actor && decidedOK && reqMine && !signedMine && !selfMade), objV: objText, onObj: (e) => this.setState({ lensNote: Object.assign({}, S.lensNote, { [cid + ':obj']: e.target.value }) }), objDisabled: objText.trim().length < 12,
      doObject: () => this.setState({ objections: Object.assign({}, S.objections, { [cid]: { by: P.name, lens: P.lens, at: TODAY, note: objText.trim() } }), events: this.mk(S.events, 'human', P.name + ' · ' + P.lens, 'Requested changes: ' + objText.trim(), cid), ...this.bump(S, cid) }),
      selfMade: !!(actor && decidedOK && reqMine && selfMade && !signedMine), selfText: 'You recorded this decision, so a colleague signs it as a second pair of eyes. You can still withdraw or reopen it below.',
      notMine: !!(actor && dec && !reqMine && mySlot), notMineText: dec ? 'Your lens is not needed on this cluster under the policy. You can still read everything.' : '',
      canOwn: !!(actor && lead && decidedOK && forecast.OWN !== 'none' && !sg.OWN), doOwn: () => logSign('OWN', true),
      canAdj: !!(actor && lead && decidedOK && forecast.ADJ !== 'none' && !sg.ADJ), doAdj: () => logSign('ADJ', true),
      readOnly: !actor && !!dec, readOnlyText: P.role === 'observer' ? 'Observers can read but not sign.' : 'You are previewing another lens, so signing is switched off.'
    };
    /* resolve panel */
    const avail = strategyAvail(S, c, ms, rk);
    const outcomes = c.actions.map(([k, label]) => ({ label, on: res.outcome === k, pressed: res.outcome === k ? 'true' : 'false', pick: () => setRes({ outcome: k }), style: 'text-align:left;min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-weight:' + (res.outcome === k ? 600 : 500) + ';border:' + (res.outcome === k ? '2px solid var(--accent)' : '1px solid #8C98A3') + ';background:' + (res.outcome === k ? '#F1F6FF' : '#FFFFFF') + ';' }));
    const merging = res.outcome === 'merge';
    const strats = STRATS.map((s) => ({
      k: s.k, name: s.name, sub: s.sub, on: res.strat === s.k, pressed: res.strat === s.k ? 'true' : 'false', disabled: !!avail[s.k], why: avail[s.k], hasWhy: !!avail[s.k],
      pick: () => setRes(s.k === 'own' && !res.own ? { strat: s.k, ownSeed: '', own: strictId ? ms.find((m) => m.id === strictId).text : ms[0].text } : s.k === 'ai' && !res.aiText ? { strat: s.k, aiText: c.aiDraft } : { strat: s.k }),
      markStyle: { sq: MARK.mech[1], ci: MARK.human[1], di: MARK.ai[1] }[s.mark] + ';flex:none;margin-top:4px',
      style: 'text-align:left;display:flex;gap:10px;align-items:flex-start;min-height:44px;padding:8px 12px;border-radius:6px;cursor:pointer;border:' + (res.strat === s.k ? '2px solid var(--accent)' : '1px solid #BAC3CA') + ';background:' + (res.strat === s.k ? '#F1F6FF' : '#FFFFFF') + ';'
    }));
    const memberOpts = ms.map((m, i) => ({ v: m.id, t: 'M' + (i + 1) + ' · ' + m.id + ' · ' + (m.v !== null && m.v !== undefined ? fmtVal(c, m.v) : m.cond || 'no number') }));
    const sideOpts = ev.sideOpts.map((o) => ({ label: o.label + ' (' + (o.m.v !== null ? fmtVal(c, o.m.v) : o.m.id) + ')', pressed: res.side === o.k ? 'true' : 'false', pick: () => setRes({ side: o.k }), style: 'min-height:44px;padding:0 12px;border-radius:6px;cursor:pointer;font-weight:600;border:' + (res.side === o.k ? '2px solid var(--accent)' : '1px solid #8C98A3') + ';background:' + (res.side === o.k ? '#F1F6FF' : '#FFFFFF') + ';' }));
    const aiTextNow = res.aiText || c.aiDraft || '';
    const aiS = res.strat === 'ai' && c.aiDraft ? aiShare(c.aiDraft, aiTextNow) : null;
    const ownS = res.strat === 'own' && res.ownSeed ? aiShare(res.ownSeed, res.own) : null;
    const share = aiS || ownS;
    const prevLabel = !merging ? '' : ev.err ? '' : ev.chosen ? 'Wording of ' + 'M' + (mi(ev.chosen) + 1) + ' · ' + ev.chosen.id + ', word for word' : res.strat === 'ai' ? 'AI draft, new wording' : ownS ? 'Your wording, started from the assistant draft' : 'Your wording, new';
    const survivor = ev.chosen ? ev.chosen.id : (ev.covers[0] || ms[0].id);
    const others = ev.covers.filter((id) => id !== survivor);
    const owners = ms.map((m) => m.owner).filter((x, i, a) => a.indexOf(x) === i);
    const happens = [];
    if (res.outcome === 'merge' && !ev.err) {
      happens.push(survivor + ' survives' + (ev.chosen ? ' with its wording unchanged.' : ' with the new wording.'));
      if (others.length) happens.push(others.join(', ') + (others.length > 1 ? ' become aliases' : ' becomes an alias') + ' of ' + survivor + '. Every trace link is kept.');
      if (ev.kept.length) happens.push(ev.kept.join(', ') + ' stay separate and are linked as related.');
      if (ms.some((m) => m.verif === 'Test')) happens.push('Test procedures linked to any member are flagged suspect until re-checked.');
    } else if (res.outcome === 'link') happens.push('Nothing is merged. A "variant of" link joins the ' + ms.length + ' requirements.');
    else if (res.outcome === 'escalate') { happens.push('A question goes to ' + joinOr(owners) + '.'); happens.push('No requirement is edited until they answer.'); }
    else if (res.outcome === 'reject') { happens.push('The suggestion is closed as not a duplicate. Nothing changes in the model.'); happens.push('The rejection is kept as a labelled example for the gold set.'); }
    else if (res.outcome === 'supersede') happens.push('The older requirement is marked superseded. Its ID and links stay.');
    if (owners.length > 1 && res.outcome !== 'escalate') happens.push(joinOr(owners) + ' are asked to approve.');
    const blindPending = blindOn && !dec && !S.blindDone[cid] && c.ai.mode !== 'none';
    const why = canRecord(S, c, ev, res, st, P, blindPending);
    const gIcon = { pass: 'pass', warn: 'warn', block: 'fail', info: 'info' };
    const rguards = ev.guards.map((g) => ({ name: g.name, note: g.note, isPass: g.st === 'pass', isWarn: g.st === 'warn', isFail: g.st === 'block', isInfo: g.st === 'info', tag: { pass: 'Pass', warn: 'Warning', block: 'Blocks', info: 'Note' }[g.st], tagStyle: 'font-size:12px;font-weight:600;color:' + { pass: '#14502B', warn: '#6B3D00', block: '#7A1510', info: '#10337F' }[g.st] + ';' }));
    const gSummary = ev.blocks ? ev.blocks + ' blocking' : ev.warns ? ev.warns + ' warning' + (ev.warns > 1 ? 's' : '') : 'all clear';
    const fcSlots = SLOT_KEYS.filter((k) => forecast[k] !== 'none').map((k) => ({ label: SLOT_NAME[k] + (forecast[k] === 'sample' ? ' (sampled)' : '') }));
    const rp = {
      decided: !!dec, undecided: !dec,
      outcomes, showStrats: merging && !dec, strats,
      showMember: merging && res.strat === 'member', memberOpts, memberV: res.member || ms[0].id, onMember: (e) => setRes({ member: e.target.value }),
      showSide: merging && res.strat === 'median' && sideOpts.length > 0, sideOpts,
      showOwn: merging && res.strat === 'own', ownV: res.own, onOwn: (e) => setRes({ own: e.target.value }),
      showAI: merging && res.strat === 'ai' && !!c.aiDraft, aiV: aiTextNow, onAiText: (e) => setRes({ aiText: e.target.value }),
      hasShare: !!share && merging, shareLine: share ? 'AI-origin share: ' + share.bucket + (share.pct ? ' · ' + share.pct + '% of words changed by a person' : '') + '. This is kept with the revision.' : '',
      showPreview: merging && !ev.err, pTok: paintOnly(ev.text || 'x'), pLabel: prevLabel, hasErr: merging && !!ev.err, pErr: ev.err,
      happens: happens.map((t) => ({ t })), guards: rguards, gSummary,
      forecast: fcSlots, forecastNote: !dec ? 'This choice needs: ' : '',
      reasonOpts: [{ v: '', t: 'Choose a reason code' }].concat(REASONS.map(([v, t]) => ({ v, t: t }))), reasonV: res.reason, onReason: (e) => setRes({ reason: e.target.value }),
      noteV: res.note, onNote: (e) => setRes({ note: e.target.value }), noteWhy: ev.noteWhy ? 'A note is required because ' + ev.noteWhy + '.' : 'A note is optional here. Your reason code is saved either way.', noteReq: !!ev.noteWhy,
      needsAck: c.lane !== 'A', acked: !!res.ack, toggleAck: () => setRes({ ack: !res.ack }),
      recordLabel: 'Record decision', recordDisabled: !!why || !actor, recordWhy: why || (actor ? 'Ready. Recording saves revision R3 and starts the sign-offs.' : ''),
      record: () => this.record(c),
      skip: () => this.nextForMe(),
      decLines: dec ? [['Decision', describeDec(dec)], ['Result', dec.text ? '“' + dec.text + '”' : 'No wording change'], ['Reason', (REASON_NAME[dec.reason] || dec.reason) + ' (' + dec.reason + ')'], ['Note', dec.note || 'None'], ['By', dec.by + ' · ' + (dec.lens || '') + ' · ' + dec.at], ['Against the AI', dec.vs], ['Covers', dec.covers.length ? dec.covers.join(', ') : '—'], ['Kept separate', dec.kept.length ? dec.kept.join(', ') : '—']].concat(dec.share ? [['AI-origin share', dec.share.bucket + (dec.share.pct ? ' · ' + dec.share.pct + '% changed' : '')]] : []).concat(dec.dissent ? [['Dissent kept', dec.dissent]] : []).map(([k, v]) => ({ k, v })) : [],
      reopenV: res.reopen, onReopen: (e) => setRes({ reopen: e.target.value }), reopenDisabled: res.reopen.trim().length < 12 || !actor,
      doReopen: () => this.setState({ dec: Object.assign({}, S.dec, { [cid]: null }), sign: Object.assign({}, S.sign, { [cid]: {} }), res: Object.assign({}, S.res, { [cid]: { reason: 'R-OTH' } }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || ''), 'Reopened a decision. Reason: ' + res.reopen.trim(), cid), ...this.bump(S, cid), just: '' }),
      aiHint: hideAI ? 'The AI answer is hidden until you record your first impression above.' : c.ai.mode === 'none' ? 'No AI was used on this group.' : c.ai.mode === 'draft' ? 'The AI drafted merged wording (shown in the AI card).' : 'The AI judged this group ' + c.ai.verdict + ' (' + c.ai.conf + '%). It cannot decide for you.'
    };
    /* revision chain */
    const chain = chainOf(S, c).map((r) => ({ rev: r.rev, markStyle: MARK[r.kind][1], markLabel: MARK[r.kind][0], chipStyle: CHIP + MARK[r.kind][2], title: r.title, by: r.by, at: r.at, detail: r.detail, hasDetail: !!r.detail, text: r.text, hasText: !!r.text }));
    const ch = { items: chain, hasShare: !!(dec && dec.share), shareLine: dec && dec.share ? 'AI-origin share of the final wording: ' + dec.share.bucket + (dec.share.pct ? ' (' + dec.share.pct + '% of words changed after the AI draft)' : '') + '. A later AI run never replaces a revision that a person edited; it arrives as a separate version.' : 'A later AI run never replaces a revision that a person edited. It arrives as a separate version.' };
    const focusSoon = (id) => setTimeout(() => { try { const e = document.getElementById(id); if (e) e.focus(); } catch (x) { /* no DOM */ } }, 60);
    const openAlign = () => { this.setState({ alignOpen: true }); focusSoon('al-close'); };
    const closeAlign = () => { this.setState({ alignOpen: false }); focusSoon('al-open'); };
    const onSheetKey = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); closeAlign(); return; }
      if (e.key !== 'Tab') return;
      const box = e.currentTarget, f = box.querySelectorAll('button:not(:disabled),[href],input,select,textarea,[tabindex]:not([tabindex="-1"])');
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    /* assemble */
    const status = STATUS_LABEL[st] + (q ? ' · ' + q.have.length + ' of ' + q.slots.length + ' signed' : '');
    const dirCtl = { canFlip: canFlip && actor, flipLabel: 'Flip direction', flip: () => this.setState({ dirs: Object.assign({}, S.dirs, { [c.famKey]: dirEff(S, c) === 'higher' ? 'lower' : 'higher' }), events: this.mk(S.events, 'human', P.name + ' · lead', 'Set stricter direction for "' + c.param + '" to ' + (dirEff(S, c) === 'higher' ? 'lower' : 'higher') + ' is stricter', cid) }) };
    return {
      banners: banners.map((b) => Object.assign({ hasAdj: false, adjV: '', onAdj: () => {}, adjHelp: '' }, b)), hasBanners: banners.length > 0,
      mrows, nMembers: ms.length, peeledNote: peeledN ? peeledN + ' member' + (peeledN > 1 ? 's were' : ' was') + ' peeled out of this group by a person. They are no longer part of it.' : '',
      refLabel: 'M' + (mi(refM) + 1) + ' · ' + refM.id, refIsStrict: refM === strictM && rk.length > 1, trackCols, ledger,
      alignOpen: !!S.alignOpen, openAlign, closeAlign, onSheetKey,
      blindPressed: blindOn ? 'true' : 'false', blindLabel: blindOn ? 'on' : 'off', toggleBlind: () => this.setState({ blind: !blindOn }),
      toggleWhy: () => this.setState({ why: Object.assign({}, S.why, { [cid]: !S.why[cid] }) }),
      d: {
        id: cid, title: c.title, rel: REL_LABEL[c.rel], relPlain: REL_PLAIN[c.rel], relStyle: CHIP + REL_STYLE[c.rel], laneName: LANE_NAME[c.lane], laneStyle: this.laneBadge(c.lane).replace('align-self:flex-start;', ''),
        status, statusStyle: CHIP + STATUS_STYLE[st], prov, paramLine: c.param + ' · stricter means ' + dirWords(S, c), claimTxt: cl && cl.by !== P.name && !dec ? 'Claimed by ' + cl.by.split(' ')[0] : '', hasClaim: !!(cl && cl.by !== P.name && !dec), claimStyle: CHIP + STATUS_STYLE.claimed,
        flipLabel: dirCtl.flipLabel, canFlip: dirCtl.canFlip, flip: dirCtl.flip,
        scores, mNote: c.mNote, guards, guardSummary: (10 - nF - nW) + ' of 10 pass' + (nF ? ', ' + nF + ' blocking' : '') + (nW ? ', ' + nW + ' warning' : ''),
        aiJudge: ai.mode === 'judge', aiVerdict: ai.verdict, aiConf: ai.conf, aiVotes: ai.votes,
        hideAI, showAI: !hideAI, blindEcho: blindOn && !!S.blindDone[cid], blindSaid: S.blindDone[cid] || '', aiVerdictShort: ai.verdict || (ai.mode === 'draft' ? 'wording draft only' : 'no judgement needed'),
        blindOptions: ['Same obligation', 'Variant', 'Conflict', 'Not sure'].map((label) => ({ label, style: BLIND_STYLE, pick: () => this.setState({ blindDone: Object.assign({}, S.blindDone, { [cid]: label }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || ''), 'Recorded blind first impression: ' + label.toLowerCase(), cid) }) })),
        aiWhy: ai.why, hasQuotes: aiQuotes.length > 0, quotes: aiQuotes, aiAction: !!ai.action, aiActionText: ai.action || '',
        hasProposal: !!ai.proposal, proposalLabel: ai.mode === 'draft' ? 'AI-drafted merged wording' : 'AI-suggested handling', proposalText: ai.proposal,
        whyOpen: S.why[cid] ? 'true' : 'false', whyOpenBool: !!S.why[cid], record: record.map(([k, v]) => ({ k, v }))
      },
      lp, sg: sgv, rp, ch
    };
  }
  nextForMe() {
    const S = this.S, infos = this.allInfos(S), cur = infos.findIndex((x) => x.c.id === S.selected);
    const mine = infos.filter((x) => x.me && x.c.id !== S.selected);
    const next = mine.find((x) => infos.indexOf(x) > cur) || mine[0] || infos[Math.min(cur + 1, infos.length - 1)];
    if (next) this.setState({ selected: next.c.id, just: '', openVer: Object.assign({}, S.openVer, { [next.c.id]: S.liveVer[next.c.id] || 0 }) });
  }
  record(c) {
    const S = this.S, P = this.person(S), ms = membersOf(S, c), res = resOf(S, c), ev = evaluate(S, c, ms, res);
    const st = statusOf(S, c);
    const blindPending = this.blindOn(S) && !decOf(S, c.id) && !S.blindDone[c.id] && c.ai.mode !== 'none';
    if (canRecord(S, c, ev, res, st, P, blindPending) || !this.canAct(S)) return;
    let share = null, revs = [];
    if (res.outcome === 'merge' && res.strat === 'ai') { share = aiShare(c.aiDraft, ev.text); revs.push({ rev: 'R2', how: 'ai', text: c.aiDraft, by: 'AI draft', at: TODAY }); }
    else if (res.outcome === 'merge' && res.strat === 'own' && res.ownSeed) { share = aiShare(res.ownSeed, ev.text); revs.push({ rev: 'R2', how: 'ai', text: res.ownSeed, by: 'Assistant draft', at: TODAY }); }
    revs.push({ rev: 'R3', how: 'human', text: ev.text, by: P.name, at: TODAY, note: res.note.trim() });
    const merged = res.outcome === 'merge';
    const dec = { outcome: res.outcome, strategy: merged ? res.strat : '', member: res.member, text: merged ? ev.text : '', newWording: merged && ev.newWording, weakening: merged && ev.weakening, covers: merged ? ev.covers : [], kept: merged ? ev.kept : [], reason: res.reason, note: res.note.trim(), by: P.name, lens: P.lens, at: TODAY, rev: 'R3', vs: vsAI(c, res), share, revs, ownFrom: merged && res.strat === 'own' && res.ownSeed ? 'assistant' : '' };
    this.setState({ dec: Object.assign({}, S.dec, { [c.id]: dec }), sign: Object.assign({}, S.sign, { [c.id]: {} }), just: c.id, events: this.mk(S.events, 'human', P.name + ' · ' + P.lens, 'Decision: ' + describeDec(dec).toLowerCase() + ' · reason ' + dec.reason + (dec.note ? ' · note recorded' : ''), c.id), ...this.bump(S, c.id) });
  }
