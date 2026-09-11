"""Install actual temporary Firefox extension via WebDriver; not a file:// test."""
import json
import os
from pathlib import Path
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
ROOT=Path(__file__).resolve().parents[2]
options=Options();options.add_argument('-headless')
options.binary_location=os.environ.get('PREPARE_FIREFOX_BINARY',str(Path.home()/'Library/Caches/ms-playwright/firefox-1543/firefox/Nightly.app/Contents/MacOS/firefox'))
with tempfile.TemporaryDirectory(prefix='prepare-firefox-') as tmp:
    options.set_preference('browser.download.folderList',2);options.set_preference('browser.download.dir',tmp)
    options.set_preference('browser.helperApps.neverAsk.saveToDisk','application/pdf,application/json')
    options.set_preference('pdfjs.disabled',True)
    from selenium.webdriver.firefox.service import Service
    driver=webdriver.Firefox(options=options,service=Service(service_args=['--allow-system-access']))
    try:
        addon=driver.install_addon(str(ROOT/'build/Filecraft-0.10.0-beta.1-extension-firefox.zip'),temporary=True)
        driver.set_context('chrome')
        mappings=json.loads(driver.execute_script("return Services.prefs.getStringPref('extensions.webextensions.uuids')"))
        driver.set_context('content')
        driver.get('moz-extension://'+mappings[addon]+'/workspace/index.html')
        from reportlab.pdfgen import canvas
        fixture=Path(tmp)/'synthetic.pdf';c=canvas.Canvas(str(fixture),pagesize=(300,400));c.drawString(20,300,'Prepare test');c.save()
        driver.find_element(By.ID,'files').send_keys(str(fixture))
        wait=WebDriverWait(driver,20);wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#pages li'))==1)
        driver.find_element(By.CSS_SELECTOR,'button[aria-label="Rotate page 1"]').click()
        driver.find_element(By.ID,'prepare').click();wait.until(lambda d:'Output parsed' in d.find_element(By.ID,'status').text)
        driver.find_element(By.ID,'reviewed').click();driver.find_element(By.ID,'download').click();driver.find_element(By.ID,'receipt-download').click()
        wait.until(lambda _: (Path(tmp)/'Prepared.pdf').exists() and (Path(tmp)/'Prepared.receipt.json').exists())
        from pypdf import PdfReader
        import hashlib
        out=Path(tmp)/'Prepared.pdf';r=PdfReader(out);assert len(r.pages)==1 and r.pages[0].rotation==90
        receipt=json.loads((Path(tmp)/'Prepared.receipt.json').read_text());assert receipt['output']['sha256']==hashlib.sha256(out.read_bytes()).hexdigest()
        driver.find_element(By.ID,'verify-receipt').send_keys(str(Path(tmp)/'Prepared.receipt.json'));driver.find_element(By.ID,'verify-file').send_keys(str(out))
        wait.until(lambda d:'Bytes match' in d.find_element(By.ID,'verify-status').text)
        driver.set_window_size(1440,1000);evidence=ROOT/'build/extension-evidence';evidence.mkdir(exist_ok=True);driver.save_screenshot(str(evidence/'firefox.png'))
        print(json.dumps({'browser':'firefox','version':driver.capabilities['browserVersion'],'addon':addon,'actualTemporaryInstall':True,'savedOutputParsed':True,'receiptHashMatch':True}))
    finally:driver.quit()
