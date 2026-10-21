#!/usr/bin/env node
/* What the page's AI gate says about every group of the sample, for the gateway to be compared with (reqin/tests/test_gateway_page.py), and the sample's requirements
   with their markings and wording, from which `reqin-gateway markings --list` builds the demo gateway's markings file.

   usage:  node export_ai_groups.js [page.html] < configs.json > groups.json
     configs.json   {"configs": [{"on": true, "sheet": {...the data sheet...}}, ...]}            (omit it to get only the requirements and the groups)
     groups.json    {"requirements": [{"id","marking","text"}], "clusters": {"CL-001": ["REQ-..", ...]}, "decisions": [{"CL-001": ["open","none"], ...}, ...]}
   The sample is generated from fixed seeds, so the result is the same every time. Nothing is written to a file by this script. */
const fs = require('fs'), path = require('path');
const pageFile = process.argv[2] || path.join(__dirname, 'project', 'Main.dc.html');
const html = fs.readFileSync(pageFile, 'utf8');
const code = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/)[1];
class DCLogic { constructor() { this.state = {}; this.props = {}; } setState() { } }
const E = new Function('DCLogic', code + '\nreturn { REQS, CLUSTERS, aiMarkOf, aiGateOf };')(DCLogic);
let input = {};
try { const raw = fs.readFileSync(0, 'utf8').trim(); if (raw) input = JSON.parse(raw); } catch (e) { input = {}; }
const out = {
  requirements: E.REQS.map((r) => ({ id: r.id, marking: E.aiMarkOf(r.id), text: r.text })),
  clusters: Object.fromEntries(E.CLUSTERS.map((c) => [c.id, c.members.map((m) => m.id)])),
  decisions: (input.configs || []).map((cfg) => Object.fromEntries(E.CLUSTERS.map((c) => { const g = E.aiGateOf({ aiOn: cfg.on, aiSheet: cfg.sheet }, c); return [c.id, [g.code, g.level]]; })))
};
process.stdout.write(JSON.stringify(out));
