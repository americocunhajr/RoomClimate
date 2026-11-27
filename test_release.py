from pathlib import Path
from playwright.sync_api import sync_playwright
import json
root=Path(__file__).parent
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content((root/'index.html').read_text())
 page.wait_for_function("document.querySelector('#results').children.length===6",timeout=60000)
 assert page.locator('#recommend').inner_text()=='18.000 BTU/h'
 assert page.locator('#resultStory').inner_text().startswith('Neste dia')
 page.screenshot(path=str(root/'preview.png'),full_page=False)
 assert page.locator('#mode').input_value()=='geometry'
 page.locator('#roofPreset').select_option('.8');page.locator('#run').click();page.wait_for_function("document.querySelector('#results').children.length===6")
 page.locator('#reset').click();page.locator('#run').click();page.wait_for_function("document.querySelector('#results').children.length===6")
 page.locator('#mcN').select_option('16');page.locator('#mcRun').click();page.wait_for_function("document.querySelector('#mcStatus').textContent.startsWith('Concluído')",timeout=120000)
 print(page.locator('#mcResults').inner_text())
 assert page.locator('#mcCSV').is_enabled()
 page.locator('#mcN').select_option('32');assert page.locator('#mcCSV').is_disabled()
 page.locator('#mode').select_option('historical');page.locator('#weatherFile').set_input_files(str(root/'fixtures/synthetic_weather.json'));page.wait_for_function("document.querySelector('#weatherStatus').textContent.includes('não ERA5')");page.locator('#run').click();page.wait_for_function("document.querySelector('#results').children.length===6")
 with page.expect_download() as d:page.locator('#exportConfig').click()
 assert json.loads(Path(d.value.path()).read_text())['mode']=='historical'
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250);assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2');page.screenshot(path=str(root/'preview_mobile.png'),full_page=False)
 assert not errors,errors
 print('Release UI: default, roof, reset, Monte Carlo, historical import, JSON, mobile and JS errors: OK')
 b.close()
