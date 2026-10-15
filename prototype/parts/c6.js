  /* ----- the trace map in Export (the rules and the files are in trace.js) ----- */
  traceAll(S) { return this._T || (this._T = trOf(S, this.allInfos(S), '')); }
  traceShown(S) { return S.trOnly === 'all' ? this.traceAll(S) : trOf(S, this.allInfos(S), 'approved'); }
  traceDownload(S, kind) {
    const only = S.trOnly === 'all' ? '' : 'approved', T = this.traceShown(S), P = this.person(S);
    const tab = TR_TABS.find((t) => t.k === S.trTab) || TR_TABS[0];
    const name = kind === 'json' ? 'trace-map.json' : TR_CSV[tab.k].file;
    const rows = kind === 'json' ? T.aliases.length + T.items.length + T.links.length + T.bases.length : T[tab.k].length;
    trSave(name, kind === 'json' ? JSON.stringify(trFile(S, T, only), null, 2) : trCsv(T, tab.k), kind === 'json' ? 'application/json' : 'text/csv');
    this.setState({
      trMsg: 'Prepared ' + name + ' with ' + rows + (rows === 1 ? ' row' : ' rows') + (only ? ' (approved changes only).' : ' (every decided change).'),
      events: this.mk(S.events, 'human', P.name + ' · ' + (P.lens || 'Observer'), 'Downloaded ' + name + ' for ' + S.baseId + ' (' + rows + (rows === 1 ? ' row, ' : ' rows, ') + (only ? 'approved changes only' : 'every decided change') + ')', S.baseId)
    });
  }
  valsTrace(S) {
    const nf = (n) => n.toLocaleString('en-US');
    const T = this.traceShown(S), only = S.trOnly !== 'all', tab = TR_TABS.find((t) => t.k === S.trTab) || TR_TABS[0], n = T.n;
    const act = (a) => (a.action === 'move' ? 'Move to ' + (trIsNew(a.to) ? 'the new requirement from ' + a.to.slice(4) : a.to) + (a.levelChange ? ', which is at a different level' : '') + (a.methodChange ? ', which is checked a different way' : '') : a.action === 'choose' ? 'Needs a requirement to point at' : 'Read again against the new wording');
    const LINK = { child_moves: 'Moves under a new parent', child_needs_parent: 'Needs a new parent', parent_bare: 'Left with nothing below it' };
    const st = (x) => TR_STATUS[x.status];
    const DEFS = {
      aliases: { head: ['Old ID', 'Becomes', 'What happened', 'Decided in', 'Status'], row: (a) => [a.old, trNowTxt(a.now), TR_WHAT[a.kind], a.src, st(a)] },
      items: { head: ['Item', 'Method', 'Was on', 'What to do', 'Status'], row: (x) => [x.item, x.method || 'None', x.from, act(x), st(x)] },
      links: { head: ['Requirement', 'What changes', 'Was', 'Now', 'Status'], row: (x) => [x.req, LINK[x.kind], x.from, x.kind === 'parent_bare' ? '' : trNowTxt(x.to), st(x)] },
      bases: { head: ['Requirement', 'Baseline', 'Change request', 'What changes', 'Status'], row: (b) => [b.req, b.bl, b.cr || 'Missing', b.change, st(b)] }
    };
    const def = DEFS[tab.k], list = T[tab.k], SHOW = 12;
    const lines = [];
    if (n.aliases) lines.push(nf(n.aliases) + (n.aliases === 1 ? ' old ID retires' : ' old IDs retire') + '. ' + nf(n.targets) + (n.targets === 1 ? ' requirement takes' : ' requirements take') + ' their place.');
    if (n.moves + n.choose + n.reread) lines.push(nf(n.moves) + (n.moves === 1 ? ' verification item moves' : ' verification items move') + ', ' + nf(n.reread) + ' to read again' + (n.choose ? ', and ' + nf(n.choose) + (n.choose === 1 ? ' has' : ' have') + ' no requirement to point at yet' : '') + '.');
    if (n.kidsMoved + n.kidsLost + n.bare) lines.push(nf(n.kidsMoved) + (n.kidsMoved === 1 ? ' requirement below moves' : ' requirements below move') + ' under a new parent' + (n.kidsLost ? ', ' + nf(n.kidsLost) + ' need one chosen' : '') + (n.bare ? ', and ' + nf(n.bare) + (n.bare === 1 ? ' parent is' : ' parents are') + ' left with nothing below it' : '') + '.');
    if (n.bases) lines.push(nf(n.bases) + (n.bases === 1 ? ' baselined requirement changes' : ' baselined requirements change') + (n.baseNoCr ? '; ' + nf(n.baseNoCr) + (n.baseNoCr === 1 ? ' has' : ' have') + ' no change request' : ' and each has a change request') + '.');
    const tabs = TR_TABS.map((t) => ({ name: t.name, count: nf(T[t.k].length), on: t.k === tab.k, pressed: t.k === tab.k ? 'true' : 'false', style: 'min-height:44px;padding:0 14px;border-radius:8px;cursor:pointer;font-weight:600;border:' + (t.k === tab.k ? '2px solid var(--accent)' : '1px solid #7A8793') + ';background:' + (t.k === tab.k ? '#F1F6FF' : '#FFFFFF') + ';', pick: () => this.setState({ trTab: t.k }), aria: t.name + ', ' + T[t.k].length + (T[t.k].length === 1 ? ' row' : ' rows') }));
    const none = T.empty;
    return {
      trLines: lines.map((t) => ({ t })), trEmpty: none, trShow: !none,
      trEmptyText: only ? 'No approved change moves anything yet. Approve a decision that removes a requirement, or show every decided change.' : 'No decided change moves anything yet.',
      trOnlyApproved: only, trOnlyAll: !only, trPickApproved: () => this.setState({ trOnly: 'approved' }), trPickAll: () => this.setState({ trOnly: 'all' }),
      trTabs: tabs, trTabName: tab.name, trTabEmpty: list.length === 0,
      trCols: def.head.map((h) => ({ h })),
      trRows: list.slice(0, SHOW).map((x) => { const c = def.row(x); return { first: c[0], rest: c.slice(1).map((t) => ({ t })) }; }),
      trMore: list.length > SHOW ? 'and ' + nf(list.length - SHOW) + ' more in the file' : '', trHasMore: list.length > SHOW,
      trNoFile: none, trNoFileCsv: list.length === 0,
      trJson: () => this.traceDownload(S, 'json'), trCsv: () => this.traceDownload(S, 'csv'), trCsvLabel: 'Download this table (' + TR_CSV[tab.k].file + ')',
      trMsg: S.trMsg, trHasMsg: !!S.trMsg
    };
  }
