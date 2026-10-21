"""Exercise draft download/restore on a built workspace with at least one comparison.
Run: python3 tools/review/check_browser.py APP --out-dir QA_DIR
Needs Playwright and Chromium. QA files contain the workspace text.
"""
import argparse, json, sys, shutil, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "tools/gui_checks"))
from serve import serving
from playwright.sync_api import sync_playwright
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=Path)
parser.add_argument("--out-dir", type=Path, required=True)
a = parser.parse_args()
work = tempfile.TemporaryDirectory(prefix="reqin-review-browser-")
app = Path(work.name) / "app"
shutil.copytree(a.app, app)
a.out_dir.mkdir(parents=True, exist_ok=True)
data = json.loads((app / "review-input.json").read_text())
count = len(data["clusters"]) + len(data["pairs"])
assert count, "Use a workspace containing comparisons to check note download/restore."
with serving(app) as base, sync_playwright() as p:
 b=p.chromium.launch(args=['--no-sandbox']); pg=b.new_page(viewport={'width':1440,'height':1000})
 errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
 pg.goto(base);pg.locator('#review-open').click();pg.locator('#review-work').wait_for(state='visible')
 pg.locator('#ready').wait_for(state='visible')
 assert pg.locator('.review-item').count()==min(count,25)
 card=pg.locator('.review-item').first
 card.locator('select').select_option('agree');card.locator('textarea').fill('The wording and quantities support this classification.')
 with pg.expect_download() as dl:pg.locator('#review-save').click()
 file=a.out_dir / 'review-export.json';dl.value.save_as(file)
 saved=json.loads(file.read_text());assert saved['status']=='draft' and len(saved['decisions'])==1 and len(saved['requirements'])==len(data['requirements'])
 pg.reload();pg.locator('#review-panel').wait_for(state='visible');pg.locator('#review-load').set_input_files(str(file));pg.wait_for_function("document.querySelector('#review-status').textContent.includes('restored')")
 assert pg.locator('.review-item').first.locator('select').input_value()=='agree'
 saved['binding']='changed';bad=a.out_dir / 'review-invalid.json';bad.write_text(json.dumps(saved))
 pg.locator('#review-load').set_input_files(str(bad));pg.wait_for_function("document.querySelector('#review-status').textContent.includes('refused')")
 assert pg.locator('.review-item').first.locator('select').input_value()=='agree'
 pg.screenshot(path=str(a.out_dir / 'review-desktop.png'),full_page=False)
 pg.set_viewport_size({'width':390,'height':844});assert pg.evaluate('document.documentElement.scrollWidth<=innerWidth')
 pg.screenshot(path=str(a.out_dir / 'review-mobile.png'),full_page=False)
 pg.locator('#files').set_input_files([str(app/'data/source-1'/n) for n in ['dataset.json','requirements.jsonl','links.jsonl','rejected.jsonl','report.json']]);assert pg.locator('#review-panel').is_hidden()
 pg.goto(base);pg.locator('#review-open').click();pg.locator('#review-work').wait_for(state='visible')
 with (app / 'data/source-1/requirements.jsonl').open('a') as damaged: damaged.write('\n')
 pg.reload();pg.wait_for_function("document.querySelector('#review-status').textContent.includes('refused')")
 assert pg.locator('#review-save').is_disabled()
 assert not errors,errors
 print('PASS: source-bound comparison cards; draft download/restore; invalid binding refused without losing work; mobile layout; changed-dataset controls hidden; damaged source refused; no page errors.')
 b.close()
