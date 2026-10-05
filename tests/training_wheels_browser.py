"""Private headless UI regression; never connects to the owner's browser profile.
Run: python tests/training_wheels_browser.py --url http://localhost:59880/
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument('--url', default='http://localhost:59880/')
args = p.parse_args()
out = Path('_tools_simplification_work')
out.mkdir(exist_ok=True)
with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width':1920,'height':1000})
    page = context.new_page()
    page.goto(args.url, wait_until='domcontentloaded')
    choice = page.locator('#spbTrainingChoice')
    choice.wait_for(state='visible', timeout=30000)
    page.screenshot(path=str(out/'training-wheels-invitation.png'))
    print(json.dumps({'stage':'invitation','visible':choice.is_visible()}), flush=True)
    before = page.locator('#canvasViewport').bounding_box()
    choice.get_by_role('button',name='Turn on',exact=True).click()
    panel = page.locator('#spbGuidePanel')
    panel.wait_for(state='visible',timeout=10000)
    after = page.locator('#canvasViewport').bounding_box()
    assert before == after, (before,after)
    box = panel.bounding_box()
    assert box['width'] <= 330 and box['x'] >= 1550 and box['y'] > 500, box
    assert page.locator('#centerPanel > #spbGuidePanel, #centerPanel > #spbQuestChip').count() == 0
    page.screenshot(path=str(out/'training-wheels-corner.png'))
    panel.get_by_role('button',name='Close Training Wheels',exact=True).click()
    assert not panel.is_visible()
    page.reload(wait_until='domcontentloaded')
    page.locator('#spbGuideToggle').wait_for(timeout=30000)
    page.wait_for_function("document.getElementById('spbQuestChip') !== null")
    assert not page.locator('#spbTrainingChoice').is_visible()
    assert not page.locator('#spbGuidePanel').is_visible()
    page.locator('#spbGuideToggle').click()
    page.locator('#spbGuidePanel').wait_for(state='visible')
    page.reload(wait_until='domcontentloaded')
    page.locator('#spbGuidePanel').wait_for(state='visible')
    assert not page.locator('#spbTrainingChoice').is_visible()
    declined = browser.new_context(viewport={'width':1920,'height':1000})
    other = declined.new_page()
    other.goto(args.url, wait_until='domcontentloaded')
    other.locator('#spbTrainingChoice').get_by_role('button',name='No thanks',exact=True).click()
    other.reload(wait_until='domcontentloaded')
    other.wait_for_function("document.getElementById('spbQuestChip') !== null")
    assert not other.locator('#spbTrainingChoice').is_visible()
    assert not other.locator('#spbGuidePanel').is_visible()
    report={'passed':True,'scope':'fresh opt-in and decline; corner geometry; unchanged canvas area; X opt-out persists; Tutorial re-enables in Easy; opt-in persists','canvasBefore':before,'canvasAfter':after,'panel':box,'desktopFocusUsed':False}
    (out/'training-wheels-browser.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    browser.close()
