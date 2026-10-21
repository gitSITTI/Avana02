  /* ----- one requirement at a time: put another beside it, then decide it (the rules are in single.js) ----- */
  rdForm(S, r) {
    return Object.assign({ kind: '', reason: '', text: r.text, note: '', q: '', cr: '', edit: false }, S.rform[r.id] || {});
  }
  rdPatch(S, id, patch) { this.setState({ rform: Object.assign({}, S.rform, { [id]: Object.assign({}, S.rform[id] || {}, patch) }) }); }
  rdSignNow(S, r, slot, on) {
    const dec = rdDec(S, r.id), P = this.person(S);
    if (!dec || !this.canAct(S)) return;
    const cur = Object.assign({}, signOf(S, r.id));
    if (on) cur[slot] = { by: P.name, at: TODAY, rev: dec.rev }; else delete cur[slot];
    this.setState({ sign: Object.assign({}, S.sign, { [r.id]: cur }), events: this.mk(S.events, 'human', P.name + ' · ' + (slot === 'OWN' ? 'owners' : P.lens), (on ? 'Signed off as ' : 'Withdrew sign-off as ') + SLOT_NAME[slot] + (slot === 'NU' && on ? ' (explained back)' : ''), r.id) });
  }
  rdRecord(S, r) {
    const P = this.person(S), f = this.rdForm(S, r), prev = rdStand(S, r);
    if (!this.canAct(S) || rdProblems(S, r, f).length) return;
    const g = f.kind === 'reword' ? rdGuards(r, f.text) : null;
    const dec = {
      outcome: f.kind, reason: f.kind === 'ask' ? '' : f.reason, note: (f.note || '').trim(), text: f.kind === 'reword' ? f.text.trim() : '',
      cover: f.kind === 'drop' && f.reason === 'S-COV' ? S.rcmp : '', q: f.kind === 'ask' ? f.q.trim() : '', to: r.owner, cr: trBase(r.id) && (f.kind === 'reword' || RD_REMOVES(f.kind)) ? trCrNorm(f.cr) : '',
      newWording: f.kind === 'reword', weakening: !!(g && g.weakening) || RD_REMOVES(f.kind), by: P.name, lens: P.lens, at: TODAY, rev: 'S' + (((prev && prev.rev && parseInt(prev.rev.slice(1), 10)) || 0) + 1),
      asked: prev && prev.outcome === 'ask' ? { q: prev.q, by: prev.by, at: prev.at } : (prev && prev.asked) || null
    };
    const what = f.kind === 'ask' ? 'Asked the owner (' + r.owner + '): ' + dec.q : RD_BY[f.kind].name + ' · reason ' + dec.reason + (dec.cover ? ' · covered by ' + dec.cover : '') + (dec.cr ? ' · change request ' + dec.cr : '') + (dec.note ? ' · note recorded' : '');
    this.setState({ rdec: Object.assign({}, S.rdec, { [r.id]: dec }), sign: Object.assign({}, S.sign, { [r.id]: {} }), rform: Object.assign({}, S.rform, { [r.id]: undefined }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Requirement ' + r.id + ': ' + what, r.id) });
    this.goldFocus('xp-h');
  }
  rdWithdraw(S, r) {
    const P = this.person(S);
    if (!this.canAct(S) || !rdDec(S, r.id)) return;
    this.setState({ rdec: Object.assign({}, S.rdec, { [r.id]: undefined }), sign: Object.assign({}, S.sign, { [r.id]: {} }), rform: Object.assign({}, S.rform, { [r.id]: undefined }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Withdrew the decision on ' + r.id + '. It goes back to “stays as it is”.', r.id) });
    this.goldFocus('xp-h');
  }
  /* the panel for the requirement picked on All requirements */
  valsSingle(S, pk) {
    if (!pk) return { on: false };
    const P = this.person(S), act = this.canAct(S), id = pk.id;
    const alone = rdAlone(S, pk), dec = rdStand(S, pk), f = this.rdForm(S, pk), editing = !dec || f.edit;
    const cid = pk.cid && !alone ? pk.cid : '', cl = cid ? CL_BY[cid] : null;
    const btn = (on) => 'text-align:left;display:flex;gap:10px;align-items:flex-start;width:100%;min-height:44px;padding:8px 12px;border-radius:8px;cursor:' + (act ? 'pointer' : 'not-allowed') + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #7A8793') + ';background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';';
    const short = (t) => (t.length > 96 ? t.slice(0, 93) + '…' : t);
    // ---- put another requirement beside this one
    const cmpId = S.rcmp && S.rcmp !== id && REQ_BY[S.rcmp] ? S.rcmp : '';
    const near = rdNear(id, 5).map((n) => ({
      id: n.id, text: short(REQ_BY[n.id].text), line: 'Text match ' + n.t.toFixed(2) + ' · keyword overlap ' + n.k.toFixed(2), on: cmpId === n.id, pressed: cmpId === n.id ? 'true' : 'false',
      pick: () => this.setState({ rcmp: cmpId === n.id ? '' : n.id, rpick: false }), aria: 'Put ' + n.id + ' beside ' + id
    }));
    let cmp = { on: false };
    if (cmpId) {
      const o = REQ_BY[cmpId], i = REQ_IX[id], j = REQ_IX[cmpId], lo = Math.min(i, j), hi = Math.max(i, j);
      const t = goldTextScore(lo, hi), k = goldKeywordScore(lo, hi), dt = diffTokens(pk.text, o.text);
      const vA = VREQ[id], vB = VREQ[cmpId], where = (r) => (r.cid ? (rdAlone(S, r) ? 'Alone (taken out of ' + r.cid + ')' : r.cid + ' · ' + STATUS_LABEL[statusOf(S, CL_BY[r.cid])]) : 'Alone');
      const fact = (label, a, b) => ({ label, a: String(a), b: String(b), diff: String(a) !== String(b) });
      const same = pk.cid && pk.cid === o.cid;
      cmp = {
        on: true, id: o.id, alloc: o.alloc, a: dt.a.map((x) => ({ t: x.t, style: x.style })), b: dt.b.map((x) => ({ t: x.t, style: x.style })),
        facts: [fact('Allocation', pk.alloc, o.alloc), fact('Owner', pk.owner, o.owner), fact('Level', 'L' + vA.lvl + ' ' + VLEVELS[vA.lvl - 1].short, 'L' + vB.lvl + ' ' + VLEVELS[vB.lvl - 1].short),
          fact('Verification', vA.vm || 'none', vB.vm || 'none'), fact('Verification items', vA.vi, vB.vi), fact('Where it is', where(pk), where(o))],
        scoreLine: 'Text match ' + t.toFixed(2) + ' (word by word, 1 is identical). Keyword overlap ' + k.toFixed(2) + ' (words few requirements use count for more).',
        readLine: (t >= 0.9 || k >= 0.9 ? 'Almost the same words.' : t >= 0.6 || k >= 0.6 ? 'Reads alike.' : 'Little in common.') + (same ? ' Both are in ' + pk.cid + ', so they were decided together.' : ''),
        swap: () => this.setState({ xPick: o.id, rcmp: id }), clear: () => this.setState({ rcmp: '' }), aria: 'Requirement ' + o.id + ' beside ' + id
      };
    }
    // ---- the decision on record
    let d = { on: false, imp: { on: false, head: '', lines: [] } };
    if (dec) {
      const q = dec.outcome === 'ask' ? null : rdSignState(S, pk, dec), sg = q ? q.sg : {}, status = rdStatus(S, pk);
      const lines = [['Decision', RD_BY[dec.outcome].name]];
      if (dec.reason) lines.push(['Reason', RD_REASON_NAME[dec.reason] + ' (' + dec.reason + ')']);
      if (dec.outcome === 'reword') lines.push(['New wording', '“' + dec.text + '”']);
      if (dec.cover) lines.push(['Covered by', dec.cover]);
      if (dec.cr) lines.push(['Change request', dec.cr + (trBase(id) ? ' · baseline ' + trBase(id).bl : '')]);
      if (dec.outcome === 'ask') lines.push(['Question for ' + dec.to, dec.q]);
      if (dec.asked) lines.push(['Earlier question', dec.asked.q + ' (' + dec.asked.by + ', ' + dec.asked.at + ')']);
      lines.push(['Note', dec.note || 'None']);
      lines.push(['By', dec.by + ' · ' + (dec.lens || 'Observer') + ' · ' + dec.at]);
      const mySlot = P.lens, selfMade = dec.by === P.name, lead = P.role === 'lead';
      const nuKey = id + ':nu', nuText = S.lensNote[nuKey] || '', nuBlock = mySlot === 'NU' && nuText.trim().length < RD_NU_MIN;
      const slots = q ? q.slots.map((k) => ({ name: SLOT_NAME[k], tag: q.req[k] === 'sample' ? 'sampled' : '', hasTag: q.req[k] === 'sample', state: sg[k] ? 'Signed by ' + sg[k].by + ' · ' + sg[k].at : 'Waiting', done: !!sg[k] })) : [];
      const reqMine = !!mySlot && !!q && q.req[mySlot] && q.req[mySlot] !== 'none';
      d = {
        on: true, status: RD_STATUS_LABEL[status], lines: lines.map(([k, v]) => ({ k, v })), imp: trImpactLines(S, pk, dec.outcome, dec.cover), slots, hasSlots: slots.length > 0,
        isAsk: dec.outcome === 'ask', owner: dec.to,
        canSign: !!(act && q && reqMine && !sg[mySlot] && !selfMade), signLabel: 'Sign off as ' + (mySlot ? SLOT_NAME[mySlot] : ''), signDisabled: nuBlock, doSign: () => this.rdSignNow(S, pk, mySlot, true),
        signHelp: nuBlock ? 'New user sign-off needs your explain-it-back sentence below (at least ' + RD_NU_MIN + ' characters).' : 'Your sign-off says: ' + LENS_MEANS[mySlot || 'SE'],
        isNU: mySlot === 'NU' && !!q && reqMine && !sg.NU, nuV: nuText, onNu: (e) => this.setState({ lensNote: Object.assign({}, S.lensNote, { [nuKey]: e.target.value }) }),
        canWithdrawSign: !!(act && q && mySlot && sg[mySlot] && sg[mySlot].by === P.name), doWithdrawSign: () => this.rdSignNow(S, pk, mySlot, false),
        canOwn: !!(act && lead && q && q.req.OWN !== 'none' && !sg.OWN), doOwn: () => this.rdSignNow(S, pk, 'OWN', true),
        selfNote: !!(act && q && reqMine && selfMade && !sg[mySlot]), selfText: 'You recorded this decision, so a colleague signs it as a second pair of eyes.',
        canChange: act && !f.edit, change: () => this.rdPatch(S, id, { edit: true, kind: dec.outcome === 'ask' ? '' : dec.outcome, reason: dec.reason || '', text: dec.text || pk.text, note: dec.note || '', q: '' }),
        answerLabel: dec.outcome === 'ask' ? 'Record the owner’s answer' : 'Change the decision',
        canWithdraw: act, withdraw: () => this.rdWithdraw(S, pk), readOnly: !act, readOnlyText: P.role === 'observer' ? 'Observers can read but not decide or sign.' : 'You are previewing another lens, so deciding and signing are switched off.'
      };
    }
    // ---- the form
    const kinds = RD_KINDS.map((k) => ({ name: k.name, help: k.help, on: f.kind === k.k, pressed: f.kind === k.k ? 'true' : 'false', pick: () => this.rdPatch(S, id, { kind: k.k, reason: '', edit: true }), style: btn(f.kind === k.k), off: !act }));
    const reasons = f.kind && RD_REASONS[f.kind].length ? [{ v: '', t: 'Choose a reason' }].concat(RD_REASONS[f.kind].map(([v, t]) => ({ v, t: t + ' (' + v + ')' }))) : [];
    const g = f.kind === 'reword' ? rdGuards(pk, f.text) : null;
    const problems = rdProblems(S, pk, f);
    const peel = cl ? {
      has: true, cid, title: cl.title, open: () => this.setState({ view: 'review', selected: cid, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [cid]: S.liveVer[cid] || 0 }) }),
      can: act && !decOf(S, cid) && membersOf(S, cl).length > 2, no: !(act && !decOf(S, cid) && membersOf(S, cl).length > 2),
      why: decOf(S, cid) ? 'The cluster already has a decision. Reopen it first if this requirement does not belong there.' : membersOf(S, cl).length <= 2 ? 'It is one of only two. If they are not duplicates, close the suggestion on the cluster instead.' : 'Taking it out removes it from the cluster. The others can still be decided together.',
      doIt: () => { this.setState({ peeled: Object.assign({}, S.peeled, { [cid]: (S.peeled[cid] || []).concat([id]) }), ref: Object.assign({}, S.ref, { [cid]: S.ref[cid] === id ? null : S.ref[cid] }), events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Peeled ' + id + ' out of the group (it does not belong)', cid) }); this.goldFocus('xp-h'); }
    } : { has: false };
    return {
      on: true, alone, canDecide: alone, notAlone: !alone, peel, near, hasNear: near.length > 0, cmp, hasCmp: cmp.on,
      picking: !!S.rpick, pickLabel: S.rpick ? 'Cancel choosing' : 'Choose another from the list', pickToggle: () => this.setState({ rpick: !S.rpick }), pickHelp: S.rpick ? 'Click a square on the map or a row in the list to put it beside ' + id + '.' : '',
      d, hasDec: !!dec, showForm: alone && act && editing, showFormLocked: alone && !act && !dec,
      kinds, kind: f.kind, hasKind: !!f.kind,
      hasReason: reasons.length > 0, reasons, reasonV: f.reason, onReason: (e) => this.rdPatch(S, id, { reason: e.target.value, edit: true }),
      isReword: f.kind === 'reword', textV: f.text, onText: (e) => this.rdPatch(S, id, { text: e.target.value, edit: true }), useOld: () => this.rdPatch(S, id, { text: pk.text, edit: true }),
      guards: g ? g.items.map((x) => ({ name: x.name, tag: { pass: 'Pass', warn: 'Needs the owners', block: 'Blocks' }[x.st], note: x.note, tagStyle: 'font-size:12px;font-weight:600;color:' + (x.st === 'pass' ? '#14502B' : x.st === 'warn' ? '#6B3D00' : '#7A1510') })) : [], hasGuards: !!g && g.items.length > 0,
      changes: g ? g.changes.map((c) => ({ t: c.text })) : [], hasChanges: !!g && g.changes.length > 0,
      isDrop: f.kind === 'drop' && f.reason === 'S-COV', coverLine: cmpId ? 'Covered by ' + cmpId + ' (the requirement beside this one).' : 'No covering requirement chosen. Put it beside this one with “Compare with” first.', coverOk: !!cmpId,
      isAsk: f.kind === 'ask', qV: f.q, onQ: (e) => this.rdPatch(S, id, { q: e.target.value, edit: true }), askLine: 'Sent to the owner: ' + pk.owner + ' (' + pk.alloc + '). Nothing changes until the answer is recorded.',
      imp: trImpactLines(S, pk, f.kind, f.kind === 'drop' && f.reason === 'S-COV' ? cmpId : ''),
      needCr: !!trBase(id) && (f.kind === 'reword' || RD_REMOVES(f.kind)), crV: f.cr, onCr: (e) => this.rdPatch(S, id, { cr: e.target.value, edit: true }),
      crLabel: 'Change request' + (trBase(id) ? ' (baseline ' + trBase(id).bl + ')' : ''), crHelp: 'This requirement is in a baseline, so changing it needs a change request. Write its number, like CR-2041.',
      noteV: f.note, onNote: (e) => this.rdPatch(S, id, { note: e.target.value, edit: true }),
      noteLabel: f.kind === 'keep' ? 'Why? (optional, but it counts for the grade when it is at least ' + RD_NOTE_MIN + ' characters)' : 'Why? (at least ' + RD_NOTE_MIN + ' characters)',
      problems: problems.map((t) => ({ t })), hasProblems: problems.length > 0, noRecord: !(act && problems.length === 0), showNote: !!f.kind && f.kind !== 'ask',
      record: () => this.rdRecord(S, pk), recordLabel: f.kind === 'ask' ? 'Send the question' : dec ? 'Record the new decision' : 'Record this decision', cancel: () => this.rdPatch(S, id, { edit: false, kind: '', reason: '' }), hasCancel: !!dec && f.edit,
      willSign: f.kind && f.kind !== 'ask' ? 'Needs sign-off from: ' + SLOT_KEYS.filter((k) => rdRequired(pk, { outcome: f.kind, weakening: RD_REMOVES(f.kind) || !!(g && g.weakening) })[k] !== 'none').map((k) => SLOT_NAME[k]).join(', ') + '.' : '', hasWillSign: !!f.kind && f.kind !== 'ask'
    };
  }
