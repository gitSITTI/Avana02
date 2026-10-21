"""Mutation run for the connectors (reqin/src/reqin/adapters and the helpers in connect.py they stand on): each rule a connector keeps is broken in a copy, one at a
time, and the connector tests must fail. A rule that can be removed without a test noticing is a rule nobody has checked.

What is covered: jira, polarion, jama, sysml1_xmi (the .xmi / .mdzip reader), agility, the OSLC configuration handling, the sql adapter (parent column, links
query, query files, the read-only guard), the DOCTYPE check in connect.py, and the outside-link count in ingest.py.
What is NOT covered: sysml_api, sysml_text, tabular, reqif_adapter, docx, pdf, the DXL script, the Jama token helper, the rest of connect.py and oslc_rm.py. A rule in
those files that nobody thought to break is not shown to be checked by this run.

The tests that must notice are the connector ones, run together (TESTS below). They test against in-memory fakes written from each vendor's documentation, so a
"CAUGHT" says the tests would notice if the code stopped doing what the documentation-shaped fake expects. It says nothing about a real server.

Usage: python3 tools/mutation/connectors.py [part of a name ...]
       python3 tools/mutation/connectors.py --list        the names
       python3 tools/mutation/connectors.py --patterns    only check that every change still matches the code exactly once (fast; no tests are run)
Exit status 1 when a change goes unnoticed and is not listed in EQUIVALENT with the reason it is harmless. Before the first change the connector tests are run on the
untouched copy and the run stops if they do not pass.   See README.md in this folder."""
import atexit
import os
import shutil
import signal
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'reqin')
MUT = tempfile.mkdtemp(prefix='reqin-mutation-connectors-')
atexit.register(shutil.rmtree, MUT, True)

TESTS = ('tests/test_connect.py tests/test_live_connectors.py tests/test_connectors_more.py tests/test_sysml1_xmi.py tests/test_sql_packs.py '
         'tests/test_reqif_archives.py tests/test_behaviour.py tests/test_doors9.py tests/test_connector_edges.py')
A = 'src/reqin/adapters/'
JIRA, POL, JAMA, XMI, AGI, OSLC, SQL = (A + f for f in ('jira.py', 'polarion.py', 'jama.py', 'sysml1_xmi.py', 'agility.py', 'oslc_rm.py', 'sql.py'))
CON, ING = 'src/reqin/connect.py', 'src/reqin/ingest.py'

# (name, file, old text that must occur exactly once, new text)
MUTANTS = [
    # ---- Jira ---------------------------------------------------------------------------------------------------------------------------------------------------
    ('jira: an issue that comes back twice is kept twice', JIRA, 'if k in seen:\n                    dup += 1\n                    continue', 'if False:\n                    dup += 1\n                    continue'),
    ('jira: the search window is not checked', JIRA, 'isinstance(tot, int) and tot > WINDOW:', 'isinstance(tot, int) and tot > WINDOW * 100:'),
    ('jira: the next page starts after a full page whatever came back', JIRA, 'start += len(issues)', 'start += size'),
    ('jira: Cloud reads the old search endpoint', JIRA, 'url = f"{base}/rest/api/{ver}/search/jql"', 'url = f"{base}/rest/api/{ver}/search"'),
    ('jira: Cloud never sends the page token back', JIRA, 'params["nextPageToken"] = token', 'pass'),
    ('jira: a page token that repeats is not noticed', JIRA, 'if nxt in tokens_seen or nxt == token:', 'if False:'),
    ('jira: Cloud stops at the first page', JIRA, 'if not issues or not nxt or body.get("isLast") is True:', 'if True:'),
    ('jira: isLast is ignored', JIRA, 'or body.get("isLast") is True:', 'or False:'),
    ('jira: a link is read from the wrong end', JIRA, 'a, b = (out_end, in_end) if side == "outward" else (in_end, out_end)', 'a, b = (in_end, out_end) if side == "outward" else (out_end, in_end)'),
    ('jira: an inward link names the wrong ends', JIRA, 'out_end, in_end = str(entry["inwardIssue"].get("key") or ""), k', 'out_end, in_end = k, str(entry["inwardIssue"].get("key") or "")'),
    ('jira: the same link seen from both issues is two links', JIRA, 'if (l[0], l[1], l[2]) not in seen_l:', 'if True:'),
    ('jira: a rejected login in the field-name lookup is carried past', JIRA, 'if isinstance(e, ConnectError) and e.status == 401:\n                    raise', 'if False:\n                    raise'),
    ('jira: a JQL with no ORDER BY is not mentioned', JIRA, 'if not re.search(r"\\border\\s+by\\b", jql, re.I):', 'if False:'),
    ('jira: no JQL reads everything', JIRA, "if not jql:\n            raise ConnectError(\"option 'jql' is required", "if False:\n            raise ConnectError(\"option 'jql' is required"),
    ('jira: a Cloud site is taken for Data Center', JIRA, 'host.endswith(".atlassian.net")', 'host.endswith(".atlassian.com")'),
    ('jira: the API version defaults the wrong way round', JIRA, '("3" if flavor == "cloud" else "2")', '("2" if flavor == "cloud" else "3")'),
    ('jira: the parent field is not asked for', JIRA, 'for needed in ("issuelinks", parent_field):', 'for needed in ("issuelinks",):'),
    ('jira: the project is the name instead of the key', JIRA, 'rec["project"] = plain(val.get("key"))', 'rec["project"] = plain(val.get("name"))'),
    ('jira: a total that does not match what came back is not said', JIRA, 'reported_total != len(rows) + dup:', 'reported_total != len(rows) + dup + 10 ** 9:'),
    ('jira: a peek reads everything', JIRA, 'if peek and page_no >= peek:', 'if False:'),
    ('jira: the parent is not handed over', JIRA, 'parent_native_id=r["parent"],', 'parent_native_id=None,'),
    ('jira: an unmapped link type takes the other direction', JIRA, 'kind, side = (tname.lower() or "link"), "outward"', 'kind, side = (tname.lower() or "link"), "inward"'),
    ('jira: unmapped link types are not counted', JIRA, 'unmapped[tname] += 1', 'pass'),
    ('jira: the revision ignores what changed', JIRA, 'json.dumps([[r["key"], r["fields"].get("updated", "")] for r in rows])', 'json.dumps([[r["key"], ""] for r in rows])'),
    ('jira: a link with an empty end is kept', JIRA, 'if not out_end or not in_end:\n                        continue', 'if False:\n                        continue'),
    ('jira: a reply that is not a search result is trusted', JIRA, 'if not isinstance(body, dict) or not isinstance(body.get("issues"), list):', 'if False:'),
    ('jira: Data Center stops before the end of the total', JIRA, 'if not issues or (isinstance(reported_total, int) and start >= reported_total):', 'if True:'),
    ('jira: Data Center with no total reads on past a short page', JIRA, 'if reported_total is None and len(issues) < size:', 'if False:'),
    ('jira: the server\'s field names lose to the user\'s', JIRA, 'names = {**from_server, **names}', 'names = {**names, **from_server}'),
    # ---- Polarion -----------------------------------------------------------------------------------------------------------------------------------------------
    ('polarion: the next link may point at another host', POL, 'if not self._same_host(base, nxt):', 'if False:'),
    ('polarion: a next link that points back is not noticed', POL, 'if nxt in seen_urls or nxt == url:', 'if False:'),
    ('polarion: a page of work items already read is not noticed', POL, 'if body["data"] and new_here == 0:', 'if False:'),
    ('polarion: a work item that comes back twice is kept twice', POL, 'if rid in seen:\n                    dup += 1\n                    continue', 'if False:\n                    dup += 1\n                    continue'),
    ('polarion: no sort is sent by default', POL, 'sort = str(o.get("sort", "id") or "")', 'sort = str(o.get("sort", "") or "")'),
    ('polarion: the linked work items are not asked for', POL, 'params["include"] = "linkedWorkItems"', 'pass'),
    ('polarion: a link is read from the wrong end', POL, 'a, b = (owner, target) if side == "owner" else (target, owner)', 'a, b = (target, owner) if side == "owner" else (owner, target)'),
    ('polarion: the parent role is read as a link', POL, 'if parent_role and role == parent_role:', 'if False:'),
    ('polarion: an unmapped role takes the other direction', POL, 'kind, side = (role.lower() or "link"), "owner"', 'kind, side = (role.lower() or "link"), "linked"'),
    ('polarion: the same link twice is two links', POL, 'if (a, b, kind) not in seen_l:', 'if True:'),
    ('polarion: a 404 later on gets the REST-is-off advice', POL, 'if first and e.status == 404:', 'if e.status == 404:'),
    ('polarion: a link id of the wrong shape is read anyway', POL, 'if not parsed:\n                    unread += 1', 'if False:\n                    unread += 1'),
    ('polarion: a link id with an empty part is read', POL, 'if len(parts) != 5 or not all(parts):', 'if len(parts) != 5:'),
    ('polarion: a link resource with no target is trusted', POL, 'if res and res["target"]:', 'if res:'),
    ('polarion: links are read when they were switched off', POL, 'or []) if include_links else []:', 'or []) if True else []:'),
    ('polarion: a next link with no scheme is used as it is', POL, 'if not nxt.startswith(("http://", "https://")):', 'if False:'),
    ('polarion: a total that does not match is not said', POL, 'total != len(items) + dup:', 'total != len(items) + dup + 10 ** 9:'),
    ('polarion: the count stops the read too early', POL, '(total is not None and len(items) + dup >= total)', '(total is not None)'),
    ('polarion: the next page number never moves', POL, 'params["page[number]"] = int(params["page[number]"]) + 1', 'params["page[number]"] = int(params["page[number]"]) + 0'),
    ('polarion: an item with no id is kept', POL, 'if not rid:\n                    continue', 'if False:\n                    continue'),
    ('polarion: the id field is the whole resource id', POL, 'f.setdefault("id", rid.split("/")[-1])', 'f.setdefault("id", rid)'),
    ('polarion: rich text keeps its type to itself', POL, 'out[f"{k}_type"] = str(v["type"])', 'pass'),
    ('polarion: any included thing is a link', POL, 'str(inc.get("type", "")).lower() == "linkedworkitems"', 'True'),
    ('polarion: a relative next link goes to the wrong place', POL, 'nxt = f"{p.scheme}://{p.netloc}{nxt}"', 'nxt = f"{rest}{nxt}"'),
    # ---- Jama ---------------------------------------------------------------------------------------------------------------------------------------------------
    ('jama: the next page starts after a full page whatever came back', JAMA, '        start += got\n', '        start += size\n'),
    ('jama: the server\'s own count of a page is ignored', JAMA, 'got = info.get("resultCount") if isinstance(info.get("resultCount"), int) else len(data)', 'got = len(data)'),
    ('jama: the total never ends the read', JAMA, '(isinstance(total, int) and start >= total)', 'False'),
    ('jama: no total and a short page never ends the read', JAMA, '(total is None and got < size)', 'False'),
    ('jama: a page that advances by nothing does not end the read', JAMA, 'if not data or got == 0 or', 'if not data or False or'),
    ('jama: a link is read from the wrong end', JAMA, '(b, a) if direction == "downstream_to_upstream" else (a, b)', '(a, b) if direction == "downstream_to_upstream" else (b, a)'),
    ('jama: the link direction defaults the wrong way round', JAMA, 'str(o.get("link_direction") or "downstream_to_upstream")', 'str(o.get("link_direction") or "upstream_to_downstream")'),
    ('jama: two projects with one name pick the first', JAMA, 'if len(hit) != 1:', 'if not hit:'),
    ('jama: a rejected login in the item-type lookup is carried past', JAMA, 'if e.status == 401:\n                raise                                        # the credentials', 'if False:\n                raise                                        # the credentials'),
    ('jama: a rejected login in the relationship-type lookup is carried past', JAMA, 'if e.status == 401:\n                    raise\n                notes.append(f"relationship type names', 'if False:\n                    raise\n                notes.append(f"relationship type names'),
    ('jama: a rejected login in the pick list lookup is carried past', JAMA, 'if e.status == 401:\n                    raise\n                cache[vid] = vid', 'if False:\n                    raise\n                cache[vid] = vid'),
    ('jama: an item that comes back twice is kept twice', JAMA, 'if iid in seen:\n                    dup += 1\n                    continue', 'if False:\n                    dup += 1\n                    continue'),
    ('jama: the item type filter lets everything through', JAMA, 'if keep and not ({tid.lower(), tinfo["name"].lower(), tinfo["key"].lower()} & keep):\n                continue', 'if False:\n                continue'),
    ('jama: the $id suffix stays on field names', JAMA, 'name = _SUFFIX.sub("", fk)', 'name = fk'),
    ('jama: a field named like a built-in overwrites it', JAMA, 'rec[name if name not in rec else fk] = plain(fv)', 'rec[name] = plain(fv)'),
    ('jama: a folder above an item is its parent record', JAMA, 'if r["parent"] not in have:\n                r["parent"] = None', 'if False:\n                r["parent"] = None'),
    ('jama: an item with no parent gets the parent "None"', JAMA, '"parent": str(loc) if loc not in (None, "") else None', '"parent": str(loc)'),
    ('jama: relationships are read in a peek', JAMA, 'not in ("0", "false", "no") and not peek:', 'not in ("0", "false", "no"):'),
    ('jama: a short relationship page does not end the read', JAMA, 'if len(data) < rel_size or not data:\n                    break', 'if not data:\n                    break'),
    ('jama: a relationship paging that does not advance is not noticed', JAMA, 'if not isinstance(new_last, int) or (last_id is not None and new_last <= last_id):', 'if False:'),
    ('jama: the relationship page never moves on', JAMA, 'params["lastId"] = last_id', 'pass'),
    ('jama: suspect links are not counted', JAMA, 'suspect += 1 if r.get("suspect") else 0', 'suspect += 0'),
    ('jama: the user\'s link names are ignored', JAMA, 'if tname in link_map:\n                        kind = link_map[tname]', 'if False:\n                        kind = link_map[tname]'),
    ('jama: a relationship with an empty end is kept', JAMA, 'if not a or not b:\n                        continue', 'if False:\n                        continue'),
    ('jama: a peek reads everything', JAMA, 'if peek and n_page >= peek:', 'if False:'),
    ('jama: a total that does not match is not said', JAMA, 'reported_total != len(raw_items) + dup:', 'reported_total != len(raw_items) + dup + 10 ** 9:'),
    ('jama: a project key is not looked up', JAMA, 'if want_project in (x[1], x[2])', 'if want_project in (x[1],)'),
    ('jama: a pick list value that is not an id is looked up', JAMA, 'if not vid.isdigit():\n            return value', 'if False:\n            return value'),
    ('jama: a pick list option with no name loses its id', JAMA, 'cache[vid] = plain(((body or {}).get("data") or {}).get("name")) or vid', 'cache[vid] = plain(((body or {}).get("data") or {}).get("name"))'),
    ('jama: the same pick list failure is said once per option', JAMA, 'if not any(n.startswith("pick list option") for n in notes):', 'if True:'),
    ('jama: an item type with no name has no id either', JAMA, '"itemType": tinfo["name"] or tid,', '"itemType": tinfo["name"],'),
    ('jama: a project given as a number is looked up as a name', JAMA, 'if want_project.isdigit():', 'if False:'),
    ('jama: the items path option is ignored', JAMA, 'str(o.get("items_path") or "abstractitems").strip("/")', '"abstractitems"'),
    # ---- the .xmi / .mdzip reader --------------------------------------------------------------------------------------------------------------------------------
    ('xmi: a DOCTYPE after the first element is not looked for', XMI, 'if b"<!doctype" in low or b"<!entity" in low:\n                    raise refuse()', 'if False:\n                    raise refuse()'),
    ('xmi: a DOCTYPE in the first 64 KB is not looked for', XMI, 'if b"<!doctype" in head or b"<!entity" in head:\n            raise refuse()', 'if False:\n            raise refuse()'),
    ('xmi: any amount may come before the first element', XMI, 'if len(prefix) > 16 << 20:', 'if False:'),
    ('xmi: the size an entry holds is not enforced as it is read', XMI, 'if self.left < 0:', 'if False:'),
    ('xmi: a zip with no model entry is as sure as one with it', XMI, 'if any(n == MODEL_ENTRY or n.startswith(MODEL_ENTRY + ".") for n in names) else 0.7', 'if any(n == MODEL_ENTRY or n.startswith(MODEL_ENTRY + ".") for n in names) else 0.95'),
    ('xmi: any xml file is taken for a model', XMI, 'return 0.9 if _HINT.search(f.read(8192)) else 0.0', 'return 0.9'),
    ('xmi: the size of a plain file is not checked', XMI, 'if p.stat().st_size > cap:', 'if False:'),
    ('xmi: the size an entry declares is not checked', XMI, 'if sizes[entry] > cap:', 'if False:'),
    ('xmi: any entry is the model when only one is xml', XMI, 'elif not model and len(xml) == 1:', 'elif len(xml) == 1:'),
    ('xmi: two model entries pick the first', XMI, 'if len(model) == 1:', 'if model:'),
    ('xmi: a named entry that is not there is not noticed', XMI, 'if want not in names:', 'if False:'),
    ('xmi: the type prefix is not removed from xmi:type', XMI, 'xtype = xtype.split(":")[-1] if xtype else', 'xtype = xtype if xtype else'),
    ('xmi: a stereotype application is any element with base_', XMI, 'if base and not xtype:', 'if base:'),
    ('xmi: the base pointer is kept as a property', XMI, 'if not k.startswith("{") and not k.startswith("base_"):', 'if not k.startswith("{"):'),
    ('xmi: a profile is not a package around a requirement', XMI, 'e["el"]["type"] in ("Package", "Profile")', 'e["el"]["type"] in ("Package",)'),
    ('xmi: relationships are not collected', XMI, 'if xtype in REL_TYPES:', 'if False:'),
    ('xmi: client and supplier given as child elements are not read', XMI, 'elif parent is not None and "rel" in parent and local in ("client", "supplier"):', 'elif False:'),
    ('xmi: a property given as a child element is not read', XMI, 'if len(el) == 0 and (el.text or "").strip():', 'if False:'),
    ('xmi: a property given as a reference is not read', XMI, 'elif _ref(el.attrib):', 'elif False:'),
    ('xmi: a comment body given as a child element is not read', XMI, 'and local == "body" and (el.text or "").strip():', 'and local == "body" and False:'),
    ('xmi: a stereotype on anything is a requirement class', XMI, 'if a["base_kind"] == "Class":', 'if True:'),
    ('xmi: every stereotype is a requirement', XMI, 'if a["stereo"].lower() in selected:', 'if True:'),
    ('xmi: the nearest requirement above is not the parent', XMI, 'if node["owner"] in req_ids:\n                    return node["owner"]', 'if False:\n                    return node["owner"]'),
    ('xmi: requirements come out in id order, not document order', XMI, 'sorted(by_class, key=lambda c: (order_of(c), c))', 'sorted(by_class)'),
    ('xmi: Id and Text keep the spelling of the file', XMI, 'canon = "Id" if low == "id" else "Text" if low == "text" else k', 'canon = k'),
    ('xmi: a property named like a built-in field replaces it', XMI, 'if gi == 0 and canon not in f:', 'if gi == 0:'),
    ('xmi: a second application\'s Id replaces the first', XMI, 'if gi == 0 and canon not in f:', 'if canon not in f:'),
    ('xmi: a second application\'s properties are dropped', XMI, "f[f\"{g['stereo']}.{k}\"] = v", 'pass'),
    ('xmi: relationship stereotypes are not collected', XMI, 'if a["base_kind"] in REL_TYPES and a["base_id"] in rel_ids:', 'if False:'),
    ('xmi: a relationship with a missing end is read', XMI, 'if not r["client"] or not r["supplier"]:', 'if False:'),
    ('xmi: a relationship between two non-requirements is read', XMI, 'if not any(x in req_ids for x in r["client"] + r["supplier"]):', 'if False:'),
    ('xmi: a relationship with no stereotype has no kind', XMI, 'kind = known[0] if known else (names_[0].lower() if names_ else "dependency")', 'kind = known[0] if known else "dependency"'),
    ('xmi: a link is read from the wrong end', XMI, 'links.append({"source": c, "target": s,', 'links.append({"source": s, "target": c,'),
    ('xmi: link ends outside the file are not counted', XMI, 'outside |= {end for end in (c, s) if end not in elements and end not in req_ids}', 'outside |= set()'),
    ('xmi: used-project proxies are not mentioned', XMI, 're.search(r"shared_model|proxy", n, re.I)', 're.search(r"shared_model", n, re.I)'),
    ('xmi: a changed file is read from the cache', XMI, 'return (src.uri, tuple(sorted((a, str(b)) for a, b in src.options.items())), st.st_size, st.st_mtime_ns)', 'return (src.uri, tuple(sorted((a, str(b)) for a, b in src.options.items())))'),
    ('xmi: the revision is not the file\'s hash', XMI, 'rev = file_sha(src.uri) ', 'rev = "" '),
    ('xmi: relationships with no stereotype are not counted', XMI, 'unstereotyped += 0 if names_ else 1', 'unstereotyped += 0'),
    ('xmi: several comments run together', XMI, '" ".join(cls.get("comments", []))', '"".join(cls.get("comments", []))'),
    ('xmi: the document order of elements is lost', XMI, '"seq": len(elements),', '"seq": 0,'),
    ('xmi: any attribute ending in XMI is an XMI attribute', XMI, '"XMI" in k[1:k.index("}")]', 'True'),
    ('xmi: a reference into another file keeps the file name', XMI, 'return h.rsplit("#", 1)[-1] if h else ""', 'return h'),
    ('xmi: a requirement with no text is not counted', XMI, 'if not f["Text"].strip():\n                no_text += 1', 'if False:\n                no_text += 1'),
    # ---- Agility ------------------------------------------------------------------------------------------------------------------------------------------------
    ('agility: an asset that comes back twice is kept twice', AGI, 'if not oid or oid in seen:\n                        continue', 'if not oid:\n                        continue'),
    ('agility: the next page starts after a full page whatever came back', AGI, 'start += len(assets)', 'start += size'),
    ('agility: a page start that does not match is not noticed', AGI, 'if body.get("pageStart") not in (None, start) and int(body["pageStart"]) != start:', 'if False:'),
    ('agility: the total never ends the read', AGI, '(isinstance(total, int) and start >= total)', 'False'),
    ('agility: XML that is not a list of assets is trusted', AGI, 'if root.tag != "Assets":', 'if False:'),
    ('agility: several related assets keep only the first', AGI, 'refs[0] if len(refs) == 1 else refs}', 'refs[0]}'),
    ('agility: the parent and link attributes are not asked for', AGI, 'for needed in {parent_attr, *link_attrs}:', 'for needed in ():'),
    ('agility: no sort is sent', AGI, 'params["sort"] = sort', 'pass'),
    ('agility: the where clause is not sent', AGI, 'if o.get("where"):\n                    params["where"]', 'if False:\n                    params["where"]'),
    ('agility: the meta check compares dotted names whole', AGI, 'gone = [x for x in sel if x.split(".")[0] not in have]', 'gone = [x for x in sel if x not in have]'),
    ('agility: the meta check is never made', AGI, 'if preflight == "meta":', 'if False:'),
    ('agility: a dependency is read from the wrong end', AGI, 'links.append((oid, tgt, str(kind), oid))', 'links.append((tgt, oid, str(kind), oid))'),
    ('agility: a total that does not match is not said', AGI, 'if reported_total is not None and not peek and reported_total != start:', 'if False:'),
    ('agility: a reference with any prefix is an id', AGI, 'and s.split(":")[0].isalpha() and s.split(":")[1].isdigit() else []', 'and s.split(":")[0].isalpha() else []'),
    ('agility: XML is not recognised', AGI, 'elif body[:7] == b"<Assets" or', 'elif False or'),
    # ---- OSLC configuration -------------------------------------------------------------------------------------------------------------------------------------
    ('oslc: the configuration header is not sent in header mode', OSLC, 'self._config_mode(src) in ("both", "header"):', 'self._config_mode(src) in ("both", "param"):'),
    ('oslc: the configuration parameter is not sent in param mode', OSLC, 'self._config_mode(src) in ("both", "param"):\n            return', 'self._config_mode(src) in ("both", "header"):\n            return'),
    ('oslc: an unknown configuration mode is accepted', OSLC, 'if mode not in ("both", "header", "param"):', 'if False:'),
    ('oslc: the order is not sent', OSLC, 'params["oslc.orderBy"] = o["order_by"]', 'pass'),
    ('oslc: the configuration parameter is left out of the query', OSLC, '"oslc.paging": "true", **cfg}', '"oslc.paging": "true"}'),
    ('oslc: a missing configuration is not mentioned', OSLC, 'if not o.get("configuration"):\n            notes.append', 'if False:\n            notes.append'),
    ('oslc: a login page parses as an empty graph', OSLC, 'if ctype in ("text/html", "application/xhtml+xml") or resp.body.lstrip()[:5].lower() in (b"<!doc", b"<html"):', 'if False:'),
    ('oslc: an empty answer is a result', OSLC, 'if not allow_empty and len(g) == 0:', 'if False:'),
    # ---- the sql adapter ----------------------------------------------------------------------------------------------------------------------------------------
    ('sql: a second statement is allowed', SQL, 'if ";" in q or not _ALLOWED.match(q) or', 'if not _ALLOWED.match(q) or'),
    ('sql: a statement that is not a SELECT is allowed', SQL, 'if ";" in q or not _ALLOWED.match(q) or', 'if ";" in q or'),
    ('sql: a write keyword is allowed', SQL, "or _FORBIDDEN.search(re.sub(r\"'(?:[^']|'')*'\", \"''\", q)):", 'or False:'),
    ('sql: comments are checked as if they were SQL', SQL, 'q = strip_sql_comments(q).strip().rstrip(";").strip()', 'q = q.strip().rstrip(";").strip()'),
    ('sql: dashes inside a string are taken for a comment', SQL, 'm.group(0) if m.group(0).startswith("\'") else " "', '" "'),
    ('sql: the size of a query file is not limited', SQL, 'if not p.is_file() or p.stat().st_size > MAX_QUERY_FILE:', 'if not p.is_file():'),
    ('sql: the query option does not win over the file', SQL, 'if options.get(key):\n        return str(options[key])', 'if False:\n        return str(options[key])'),
    ('sql: a row limit does not stop the read', SQL, 'if limit and n >= limit:\n                    break', 'if False:\n                    break'),
    ('sql: a record can be its own parent', SQL, 'and str(f[pcol]) != nid else None', 'else None'),
    ('sql: a link with an empty end is kept', SQL, 'if a in ("", None) or b in ("", None):\n                continue', 'if False:\n                continue'),
    ('sql: a link with no kind has none', SQL, 'kind = str(r.get("kind") or "trace")', 'kind = str(r.get("kind"))'),
    ('sql: the connector id is not the link locator', SQL, 'locator=str(r.get("ref") or f"link{i + 1}")', 'locator=f"link{i + 1}"'),
    ('sql: a parent column that is not there is not said', SQL, 'if pcol and rows and pcol not in cols:', 'if False:'),
    ('sql: an id column that is not there is not said', SQL, 'if idc and rows and idc not in cols:', 'if False:'),
    ('sql: a links query without source and target is accepted', SQL, 'if sample and not {"source", "target"} <= set(sample[0]):', 'if False:'),
    ('sql: a query file alone is not enough to be recognised', SQL, '(src.options.get("query") or src.options.get("query_file"))', '(src.options.get("query"))'),
    ('sql: the revision ignores the links query', SQL, 'query_text(src.options, "links_query") or ""', '""'),
    ('sql: the revision ignores the parent column', SQL, 'str(src.options.get("parent_column", ""))]', '""]'),
    ('sql: the database is not opened read-only', SQL, 'if eng.dialect.name == "sqlite":', 'if False:'),
    ('sql: the links query skips the guard', SQL, 'return None if raw is None else check_query(raw)', 'return None if raw is None else raw'),
    # ---- the DOCTYPE check shared by the readers ----------------------------------------------------------------------------------------------------------------
    ('dtd: an ENTITY declaration alone is not found', CON, '_DTD = re.compile(rb"<!(?:doctype|entity)", re.I)', '_DTD = re.compile(rb"<!doctype", re.I)'),
    ('dtd: upper case is not found', CON, '_DTD = re.compile(rb"<!(?:doctype|entity)", re.I)', '_DTD = re.compile(rb"<!(?:doctype|entity)")'),
    ('dtd: only the first 64 KB is searched', CON, 'return _DTD.search(raw) is not None', 'return _DTD.search(raw[:65536]) is not None'),
    ('dtd: safe_xml does not look', CON, 'if has_dtd(raw):\n        raise ConnectError(f"{what} has a DOCTYPE', 'if False:\n        raise ConnectError(f"{what} has a DOCTYPE'),
    # ---- the count of links that leave the import ---------------------------------------------------------------------------------------------------------------
    ('ingest: only a link whose target is outside is counted', ING, 'if l.source_mid is None or l.target_mid is None)', 'if l.target_mid is None)'),
    ('ingest: only a link whose source is outside is counted', ING, 'if l.source_mid is None or l.target_mid is None)', 'if l.source_mid is None)'),
]

EQUIVALENT = {
    'jama: an item with no parent gets the parent "None"': 'the step after it sets every parent that is not one of the records to none, and "None" is not the id of a record (Jama ids are numbers)',
}


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT)
    shutil.copytree(SRC + '/src', MUT + '/src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    shutil.copytree(SRC + '/tests', MUT + '/tests', ignore=shutil.ignore_patterns('__pycache__', 'fixtures_approved'))
    for d in ('profiles', 'connectors'):
        shutil.copytree(SRC + '/' + d, MUT + '/' + d, ignore=shutil.ignore_patterns('__pycache__'))


LIMIT = 150      # seconds: the untouched tests take about 15. A change that removes a guard against a paging loop makes the fake loop until max_requests (a million), which is noticed, but only by this clock.


def run():
    """The tests in a process of their own (a group of its own, so a timeout kills the pytest under the shell too) with a memory ceiling, so a runaway cannot take the machine."""
    cmd = 'ulimit -v 4000000; PYTHONPATH=src:tests exec python3 -m pytest %s -q -x -p no:cacheprovider 2>&1 | tail -6' % TESTS
    pr = subprocess.Popen(cmd, cwd=MUT, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        return pr.communicate(timeout=LIMIT)[0]
    except subprocess.TimeoutExpired:
        os.killpg(pr.pid, signal.SIGKILL)
        pr.communicate()
        return CLOCK


CLOCK = 'Error: the tests did not finish within %d s (noticed only by the clock)' % LIMIT


def memory_only(out):
    """The tests died because the change made them eat the memory ceiling, not because a test saw a wrong answer."""
    return 'Cannot allocate memory' in out or 'MemoryError' in out


def failed(out):
    return ' failed' in out or ' error' in out or 'Error' in out


def main(args):
    if args == ['--list']:
        for m in MUTANTS:
            print(m[0])
        return 0
    if args == ['--patterns']:
        bad = []
        for name, f, old, _new in MUTANTS:
            n = open(os.path.join(SRC, f), encoding='utf-8').read().count(old)
            if n != 1:
                bad.append(name)
                print('PATTERN %s: %s (%d matches)' % ('MISSING' if n == 0 else 'NOT UNIQUE', name, n))
        names = [m[0] for m in MUTANTS]
        for n in {n for n in names if names.count(n) > 1}:
            bad.append(n)
            print('NAME USED TWICE:', n)
        print('%d of %d changes match the code exactly once' % (len(MUTANTS) - len(bad), len(MUTANTS)))
        return 1 if bad else 0
    reset()
    base = run()
    if failed(base):
        print('the connector tests do not pass on the untouched code, so a run would prove nothing:\n' + base)
        return 2
    print('the untouched copy passes: %s' % base.strip().splitlines()[-1], flush=True)
    survivors = []
    tally = {'noticed by a test': 0, 'noticed only by the clock': 0, 'noticed only by the memory ceiling': 0, 'not noticed, harmless': 0}
    for name, f, old, new in MUTANTS:
        if args and not any(a in name for a in args):
            continue
        reset()
        p = os.path.join(MUT, f)
        s = open(p, encoding='utf-8').read()
        if s.count(old) != 1:
            print('%-78s PATTERN %s' % (name, 'MISSING' if s.count(old) == 0 else 'NOT UNIQUE'), flush=True)
            survivors.append(name)
            continue
        open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
        out = run()
        if out == CLOCK:
            print('%-78s CAUGHT, ONLY BY THE CLOCK: %s' % (name, out), flush=True)
            tally['noticed only by the clock'] += 1
        elif memory_only(out):
            print('%-78s CAUGHT, ONLY BY THE MEMORY CEILING: %s' % (name, out.strip().splitlines()[-1][:80]), flush=True)
            tally['noticed only by the memory ceiling'] += 1
        elif failed(out):
            line = next((l for l in out.splitlines() if l.startswith(('FAILED', 'ERROR'))), out.strip().splitlines()[-1] if out.strip() else '')
            print('%-78s CAUGHT: %s' % (name, line[:100]), flush=True)
            tally['noticed by a test'] += 1
        elif name in EQUIVALENT:
            print('%-78s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
            tally['not noticed, harmless'] += 1
        else:
            print('%-78s NOT CAUGHT' % name, flush=True)
            survivors.append(name)
    print('\n' + ', '.join('%s: %d' % kv for kv in tally.items()))
    print('%s' % ('every change was noticed' if not survivors else '%d went unnoticed: %s' % (len(survivors), '; '.join(survivors))))
    return 1 if survivors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
