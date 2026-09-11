const {test,expect}=require('@playwright/test');
const path=require('node:path'),fs=require('node:fs'),{pathToFileURL}=require('node:url');
const PDF=require('../../pdf/vendor/pdf-lib.min.js');
test('offline bundle starts disconnected and still exports a real PDF',async({page,context})=>{
 const network=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
 await context.setOffline(true);
 await page.goto(pathToFileURL(path.resolve(__dirname,'../../workbench/index.html')).href);
 await expect(page).toHaveTitle(/Filecraft/);
 await page.locator('#sample').click();
 await expect(page.locator('#pages li')).toHaveCount(1);
 await page.locator('#prepare').click();await expect(page.locator('#status')).toContainText('Output parsed');
 await page.locator('#reviewed').check();const saved=page.waitForEvent('download');await page.locator('#download').click();
 const bytes=fs.readFileSync(await(await saved).path());expect((await PDF.PDFDocument.load(bytes)).getPageCount()).toBe(1);
 expect(network).toEqual([]);
});
