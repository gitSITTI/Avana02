  /* ----- AI use: the switch, the data sheet, and what the gate does with each group (the rules and the words are in aigate.js) ----- */
  aiCan(S) { return this.person(S).role === 'lead' && !S.preview; }
  aiWhyNot(S) { return S.preview ? 'Leave the lens preview first. Nothing is changed from a preview.' : this.person(S).role === 'lead' ? '' : 'Only the lead can change the switch or the data sheet. Ask ' + (PEOPLE.find((p) => p.role === 'lead') || {}).name + '.'; }
  aiEvent(S, text) { const P = this.person(S); return this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), text, 'AI use'); }
  aiSwitch() {
    const S = this.S; if (!this.aiCan(S)) return;
    const on = !S.aiOn, c = aiCounts(Object.assign({}, S, { aiOn: on }), CLUSTERS);
    this.setState({
      aiOn: on, events: this.aiEvent(S, 'AI use switched ' + (on ? 'on' : 'off') + ' for the whole project'),
      aiMsg: { bad: false, text: on ? 'AI is switched on. ' + (c.open ? c.open + ' of ' + c.total + ' groups can go to the model.' : 'No group can go to the model yet: see what is holding them back below.') : 'AI is switched off for the whole project. Every AI answer is hidden until it is switched on again.' }
    });
  }
  aiBegin() { const S = this.S; if (!this.aiCan(S)) return; this.setState({ aiEdit: aiDraftOf(S.aiSheet), aiMsg: null }); }
  aiCancel() { this.setState({ aiEdit: null, aiMsg: { bad: false, text: 'Nothing was changed.' } }); }
  aiSet(patch) { const S = this.S; if (!S.aiEdit) return; this.setState({ aiEdit: Object.assign({}, S.aiEdit, patch) }); }
  aiDraftProblems(d) {
    const sh = aiSheetFromDraft(d), out = aiSheetProblems(sh).slice();
    if (!String(d.reviewed_by).trim()) out.push('reviewer');
    return out;
  }
  aiSave() {
    const S = this.S; if (!this.aiCan(S) || !S.aiEdit) return;
    const d = S.aiEdit, sh = aiSheetFromDraft(d);
    if (this.aiDraftProblems(d).length) return;
    const P = this.person(S), who = String(d.reviewed_by).trim().slice(0, 120);
    const next = Object.assign(sh, { model: sh.model.slice(0, 120), reviewed_by: who, reviewed_at: TODAY, entered_by: P.name });
    const diff = aiDiff(S.aiSheet, next);
    this.setState({
      aiSheet: next, aiEdit: null,
      events: this.aiEvent(S, 'AI data sheet ' + (diff.length ? 'changed (' + diff.join('; ') + ')' : 'confirmed unchanged') + ' and marked reviewed by ' + who + ' [sheet ' + aiSheetFp(next) + ']'),
      aiMsg: { bad: false, text: 'The data sheet is saved and marked reviewed by ' + who + '. The gate now reads it.' }
    });
  }
  aiWithdraw() {
    const S = this.S; if (!this.aiCan(S) || !aiReviewed(S.aiSheet)) return;
    const next = Object.assign({}, S.aiSheet, { reviewed_by: '', reviewed_at: '' });
    this.setState({ aiSheet: next, aiEdit: null, events: this.aiEvent(S, 'AI data sheet approval withdrawn; nothing goes to the AI until it is reviewed again [sheet ' + aiSheetFp(next) + ']'), aiMsg: { bad: false, text: 'Approval withdrawn. Nothing goes to the AI until the sheet is reviewed again.' } });
  }
  aiDownload() {
    const S = this.S, f = aiUseFile(S);
    trSave('ai-use.json', JSON.stringify(f, null, 2), 'application/json');
    this.setState({ aiMsg: { bad: false, text: 'Prepared ai-use.json: the switch, the data sheet, ' + f.groups.held + ' held groups and the reason for each. It holds no requirement text.' }, events: this.aiEvent(S, 'Downloaded ai-use.json (' + f.groups.held + ' of ' + f.groups.total + ' groups held back)') });
  }
  valsAi(S) {
    const nf = (n) => n.toLocaleString('en-US'), can = this.aiCan(S), sh = S.aiSheet, rev = aiReviewed(sh), probs = aiProblemsOf(sh);
    const cnt = aiCounts(S, CLUSTERS), mk = aiMarkCountsOnce(), kind = !S.aiOn ? 'off' : !rev ? 'unreviewed' : probs.length ? 'sheet' : 'open';
    const ST = {
      off: ['AI is switched off', 'Nothing goes to a model. Reviewers work from the mechanical results alone, and every earlier AI answer is hidden until the switch is turned on.', 'isInfo'],
      unreviewed: ['AI is on, but nothing is sent', 'The data sheet has not been reviewed. Until a reviewer’s name and a date are on it, no group goes to the model.', 'isWarn'],
      sheet: ['AI is on, but nothing is sent', 'The data sheet has ' + probs.length + (probs.length === 1 ? ' problem' : ' problems') + ' (listed under it). Until the sheet is consistent, no group goes to the model.', 'isWarn'],
      open: ['AI is on', nf(cnt.open) + ' of ' + nf(cnt.total) + ' groups can go to the model. ' + (cnt.held ? nf(cnt.held) + (cnt.held === 1 ? ' is' : ' are') + ' held back, and each one says why.' : 'None are held back.'), 'isPass']
    }[kind];
    const guardIcon = { isPass: false, isWarn: false, isFail: false, isInfo: false }; guardIcon[ST[2]] = true;
    const why = this.aiWhyNot(S);
    /* what is holding groups back */
    const rowsAll = [
      ['Open to the AI', cnt.open, 'open'],
      ['Switched off', cnt.by.off, 'held'], ['Data sheet not reviewed', cnt.by.unreviewed, 'held'], ['Data sheet has a problem', cnt.by.sheet, 'held'],
      ['Marked export controlled, above what the sheet approves', cnt.exp, 'held'], ['Marked CUI, above what the sheet approves', cnt.cui, 'held'],
      ['A marking this page does not recognise', cnt.by.unknown, 'held'], ['No marking recorded, and the sheet keeps those from the AI', cnt.by.unstated, 'held'], ['Classified marking', cnt.by.classified, 'held']
    ].filter((r) => r[1] > 0 || r[2] === 'open');
    const holds = rowsAll.map(([name, n, tone]) => ({ name, n: nf(n), pct: cnt.total ? Math.round((n / cnt.total) * 100) + '%' : '0%', bar: 'height:10px;border-radius:0 5px 5px 0;background:' + (tone === 'open' ? '#0A665A' : '#B25D12') + ';display:block;width:' + (cnt.total ? Math.max(n ? 1 : 0, (n / cnt.total) * 100).toFixed(1) : 0) + '%', aria: name + ': ' + n + ' of ' + cnt.total + ' groups' }));
    const marks = [['none', 'No marking'], ['cui', 'CUI'], ['exp', 'Export controlled'], ['classified', 'Classified'], ['unknown', 'Marking not recognised'], ['unstated', 'No marking recorded']].map(([k, name]) => ({ name, n: nf(mk[k]), pct: mk.total ? (mk[k] / mk.total * 100 < 1 && mk[k] ? '<1%' : Math.round(mk[k] / mk.total * 100) + '%') : '0%' }));
    /* the sheet as it is saved */
    const yes = (b) => (b ? 'Yes' : 'No');
    const sheetRows = [
      ['Model', sh.model || 'Not named'], ['Where it runs', AI_WHERE_NAME[sh.where]], ['Does requirement text leave your network?', yes(sh.leaves)],
      ['Prompts and answers', AI_LOG_NAME[sh.log] + (sh.log !== 'none' ? ', ' + sh.days + (sh.days === 1 ? ' day' : ' days') : '')],
      ['Highest marking approved', AI_LEVEL_NAME[sh.approved]], ['A requirement with no marking recorded', AI_UNSTATED_NAME[sh.unstated]],
      ['Reviewed by', rev ? sh.reviewed_by + ', ' + sh.reviewed_at + (sh.entered_by ? ' (entered by ' + sh.entered_by + ')' : '') : 'Not reviewed']
    ].map(([k, v]) => ({ k, v }));
    const pill = (on) => 'min-height:44px;padding:0 14px;border-radius:8px;cursor:pointer;font-weight:' + (on ? 600 : 500) + ';border:' + (on ? '2px solid var(--accent)' : '1px solid #7A8793') + ';background:' + (on ? '#F1F6FF' : '#FFFFFF') + ';color:#12171C;';
    /* the sheet being changed */
    const d = S.aiEdit, editing = !!d, dp = editing ? this.aiDraftProblems(d) : [];
    const set = (patch) => () => this.aiSet(patch);
    const grp = (legend, key, opts, cur) => ({ legend, items: opts.map(([val, label]) => ({ label, pressed: cur === val ? 'true' : 'false', style: pill(cur === val), pick: set({ [key]: val }) })) });
    const groups = editing ? [
      grp('Where does the model run?', 'where', AI_WHERE.map((w) => [w, AI_WHERE_NAME[w]]), d.where),
      grp('Does requirement text leave your network on its way to the model?', 'leaves', [[true, 'Yes'], [false, 'No']], d.leaves),
      grp('Prompts and answers are', 'log', AI_LOG.map((w) => [w, AI_LOG_NAME[w]]), d.log),
      grp('Highest marking you approve for the AI', 'approved', AI_LEVELS.map((w) => [w, AI_LEVEL_NAME[w]]), d.approved),
      grp('A requirement with no marking recorded', 'unstated', AI_UNSTATED.map((w) => [w, AI_UNSTATED_NAME[w]]), d.unstated)
    ] : [];
    const dsum = editing ? aiSheetFromDraft(d) : null;
    /* groups held back, the first few */
    const heldAll = CLUSTERS.map((c) => ({ c, g: aiGateOf(S, c) })).filter((x) => !x.g.open);
    const heldRows = heldAll.slice(0, 8).map((x) => ({ id: x.c.id, title: x.c.title, why: aiHeldText(x.g, sh), openAria: 'Open ' + x.c.id + ' in the review queue', open: () => this.setState({ view: 'review', selected: x.c.id, qTab: 'all', just: '', openVer: Object.assign({}, S.openVer, { [x.c.id]: S.liveVer[x.c.id] || 0 }) }) }));
    const hist = S.events.filter((e) => e.target === 'AI use').slice(-6).reverse().map((e) => ({ when: e.time, who: e.actor, what: e.text }));
    return {
      auHead: ST[0], auLine: ST[1], auSt: guardIcon,
      auSwitchLabel: S.aiOn ? 'Switch AI off for the whole project' : 'Switch AI on for the whole project', auSwitch: () => this.aiSwitch(), auCan: can, auCanNot: !can, auWhy: why,
      auHolds: holds, auMarks: marks, auTotal: nf(cnt.total), auReqTotal: nf(mk.total),
      auSheetRows: sheetRows, auReviewed: rev, auNotReviewed: !rev, auSheetProblems: probs.map((p) => ({ t: AI_PROBLEM[p] })), auHasSheetProblems: probs.length > 0,
      auBegin: () => this.aiBegin(), auWithdraw: () => this.aiWithdraw(), auShowEditBtn: can && !editing, auShowWithdraw: can && !editing && rev,
      auEditing: editing, auGroups: groups, auModel: editing ? d.model : '', auDays: editing ? d.days : '', auReviewer: editing ? d.reviewed_by : '',
      auOnModel: (e) => this.aiSet({ model: e.target.value }), auOnDays: (e) => this.aiSet({ days: e.target.value }), auOnReviewer: (e) => this.aiSet({ reviewed_by: e.target.value }),
      auDaysOff: editing ? d.log === 'none' : false,
      auDraftProblems: dp.map((p) => ({ t: p === 'reviewer' ? 'Write who reviewed this sheet (name and office).' : AI_PROBLEM[p] })), auHasDraftProblems: dp.length > 0,
      auDraftOk: editing && dp.length === 0, auSaveDisabled: !editing || dp.length > 0, auSave: () => this.aiSave(), auCancel: () => this.aiCancel(),
      auDraftLine: editing ? (dp.length ? 'Fix the ' + dp.length + (dp.length === 1 ? ' thing' : ' things') + ' above to save.' : 'Saving marks the sheet reviewed by the name you wrote, today. Nothing changes until you save.') : '',
      auHeldRows: heldRows, auHasHeld: heldRows.length > 0, auNoHeld: heldRows.length === 0, auHeldMore: heldAll.length > heldRows.length ? 'and ' + nf(heldAll.length - heldRows.length) + ' more in ai-use.json' : '', auHasHeldMore: heldAll.length > heldRows.length,
      auHist: hist, auHasHist: hist.length > 0, auNoHist: hist.length === 0,
      auDownload: () => this.aiDownload(), auMsg: S.aiMsg ? S.aiMsg.text : '', auHasMsg: !!S.aiMsg, auMsgBad: !!(S.aiMsg && S.aiMsg.bad),
      auRules: [
        'The switch is off: nothing goes to a model.',
        'The data sheet has no reviewer’s name and date: nothing goes.',
        'The sheet contradicts itself, such as a vendor service with text that does not leave: nothing goes, and nothing is quietly capped.',
        'A group is judged by its most restrictive requirement. One CUI requirement makes the group CUI.',
        'A classified marking, or a marking this page does not recognise, never goes. Add the marking style to the rules in the open instead of guessing.',
        'A group marked above what the sheet approves is held back. Export-controlled text can only be approved for a model on your own servers.',
        'A requirement with no marking recorded is kept from the AI, unless the sheet says to treat it as unmarked.'
      ].map((t) => ({ t }))
    };
  }
