#!/usr/bin/env node
/* Writes the demo seed for the reference server: the sample's people, and the sample's own activity (the decisions, sign-offs, claims, objections and
   flags the page shows when it is not connected) as documents. `reqin-server demo` loads it, so a connected page starts with the same made-up project.

   usage:  node export_seed.js [page.html] [out.json]      defaults: project/Main.dc.html  demo/seed.json
   The result is the same every time (the sample is generated from fixed seeds), so `make proto` rebuilds it and checks it against the committed file. */
const fs = require('fs'), path = require('path');
const pageFile = process.argv[2] || path.join(__dirname, 'project', 'Main.dc.html');
const outFile = process.argv[3] || path.join(__dirname, 'demo', 'seed.json');
const html = fs.readFileSync(pageFile, 'utf8');
const code = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/)[1];
class DCLogic { constructor() { this.state = {}; this.props = {}; } setState() { } }
const E = new Function('DCLogic', code + '\nreturn { SEED, PEOPLE, DEFAULTS, connDocsOf, connWire, connPlace };')(DCLogic);

const byName = {};
E.PEOPLE.forEach((p) => { byName[p.name] = p.k; });
const keyOf = (name) => { if (!byName[name]) throw new Error('the sample names "' + name + '", who is not one of its people'); return byName[name]; };
/* the sample as the page would hold it after somebody had decided all of this */
const S = Object.assign({}, E.DEFAULTS, { dec: E.SEED.dec, sign: E.SEED.sign, objections: E.SEED.dispute, claims: E.SEED.claims, stale: E.SEED.stale, sib: E.SEED.sibs });
const flat = E.connDocsOf(S);
const lead = (E.PEOPLE.find((p) => p.role === 'lead') || {}).k;
const docs = Object.keys(flat).sort().map((id) => {
  let body = flat[id], by;
  const kind = id.split('/')[0];
  if (kind === 'sign') {
    body = E.connWire({ revs: { ['dec/' + id.split('/')[1]]: 1 } }, id, body);      // every seeded decision is at revision 1 on the server
    by = keyOf(flat[id].by);
  } else if (kind === 'dec' || kind === 'obj' || kind === 'claim') by = keyOf(flat[id].by);
  else if (kind === 'sib') by = keyOf(flat[id].v[0].by);
  else by = lead;                                                                    // a "source changed" flag has no author in the sample: the lead holds it
  return { id, by, body };
});
const seed = {
  format: 'reqin-demo-seed/1', project: 'demo',
  note: 'Made-up sample data for the prototype: the same air vehicle project the page shows without a server. Written by prototype/export_seed.js; do not edit by hand.',
  people: E.PEOPLE.map((p) => ({ key: p.k, name: p.name, role: p.role, lens: p.lens })),
  docs
};
fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(seed, null, 1) + '\n');
console.log('wrote ' + outFile + ': ' + seed.people.length + ' people, ' + docs.length + ' documents');
