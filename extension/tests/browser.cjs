const {chromium}=require('../../portable/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const PDF=require('../../pdf/vendor/pdf-lib.min.js');
(async()=>{
 const folder=path.resolve(__dirname,'../../build/extension/chromium'),profile=fs.mkdtempSync(path.join(os.tmpdir(),'prepare-ext-'));
 const errors=[],network=[];let context;
 try{
  const edge=process.env.PREPARE_TEST_EDGE==='1';
  context=await chromium.launchPersistentContext(profile,{headless:true,channel:edge?'msedge':'chromium',args:[`--disable-extensions-except=${folder}`,`--load-extension=${folder}`]});
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker',{timeout:15000});
  const base=worker.url().split('/').slice(0,3).join('/');
  const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
  await page.goto(base+'/workspace/index.html');
  const d=await PDF.PDFDocument.create();d.addPage([300,400]);d.addPage([400,300]);
  await page.locator('#files').setInputFiles({name:'synthetic.pdf',mimeType:'application/pdf',buffer:Buffer.from(await d.save())});
  await page.waitForFunction(()=>document.querySelectorAll('#pages li').length===2);
  await page.getByRole('button',{name:'Rotate page 1',exact:true}).click();
  await page.locator('#prepare').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Output parsed'));
  await page.locator('#reviewed').check();
  const event=page.waitForEvent('download');await page.locator('#download').click();const result=fs.readFileSync(await(await event).path());
  const parsed=await PDF.PDFDocument.load(result);assert.equal(parsed.getPageCount(),2);assert.equal(parsed.getPage(0).getRotation().angle,90);
  const re=page.waitForEvent('download');await page.locator('#receipt-download').click();const receipt=JSON.parse(fs.readFileSync(await(await re).path(),'utf8'));
  assert.equal(receipt.output.sha256,crypto.createHash('sha256').update(result).digest('hex'));
  await page.locator('#limit').fill('0.001');assert.equal(await page.locator('#result').isHidden(),true);
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  const out=path.resolve(__dirname,'../../build/extension-evidence');fs.mkdirSync(out,{recursive:true});
  await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(out,(edge?'edge':'chromium')+'.png'),fullPage:true});
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  console.log(JSON.stringify({browser:edge?'edge':'chromium',version:context.browser()?.version(),extension:base,workflow:'installed extension → import → rotate → export → parse → receipt hash → stale-output invalidation',httpRequests:network.length,errors,bytes:result.length}));
 }finally{if(context)await context.close();fs.rmSync(profile,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
