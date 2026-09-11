const {test,expect}=require('@playwright/test');const {pathToFileURL}=require('node:url');const path=require('node:path');const fs=require('node:fs');
async function start(page){await page.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);}
async function fixture(page){return Buffer.from(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=600;c.height=400;const x=c.getContext('2d');x.fillStyle='#f00';x.fillRect(0,0,300,400);x.fillStyle='#00f';x.fillRect(300,0,300,400);return c.toDataURL('image/png').split(',')[1];}),'base64');}
test('offline file workflow creates bounded PDF and invalidates edits',async({page,context},info)=>{
 const network=[];page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});await context.setOffline(true);await start(page);
 const png=await fixture(page);await page.locator('#files').setInputFiles({name:'spread.png',mimeType:'image/png',buffer:png});
 await expect(page.locator('#pages li')).toHaveCount(1);await page.getByRole('button',{name:'Split spread'}).click();await expect(page.locator('#pages li')).toHaveCount(2);
 await page.getByRole('button',{name:'Move page 2 up',exact:true}).click();await expect(page.locator('#pages li').first()).toContainText('right');await page.getByRole('button',{name:'Move page 1 down',exact:true}).click();
 await page.locator('#paper').selectOption('a4');await page.locator('#dpi').fill('150');await page.getByRole('button',{name:'Filecraft PDF',exact:true}).click();await expect(page.locator('#status')).toContainText('Fits');
 await expect(page.locator('#download')).toBeHidden();await page.locator('#reviewed').check();const download=page.waitForEvent('download');await page.locator('#download').click();const d=await download;const dest=info.outputPath('prepared.pdf');await d.saveAs(dest);
 const bytes=fs.readFileSync(dest);expect(bytes.length).toBeLessThan(2_000_000);expect(bytes.subarray(0,8).toString()).toBe('%PDF-1.4');expect(bytes.toString()).toContain('/Count 2');
 fs.mkdirSync(path.resolve(__dirname,'../../build/portable-evidence'),{recursive:true});fs.copyFileSync(dest,path.resolve(__dirname,`../../build/portable-evidence/${info.project.name}-split.pdf`));
 await page.getByRole('button',{name:'Rotate all',exact:true}).click();await expect(page.locator('#download')).toBeHidden();expect(network).toEqual([]);
});

test('cancel discards late encode; grayscale pixels and padding are real',async({page},info)=>{
 await start(page);const png=await fixture(page);await page.locator('#files').setInputFiles({name:'colors.png',mimeType:'image/png',buffer:png});await expect(page.locator('#pages li')).toHaveCount(1);
 await page.evaluate(()=>{const original=HTMLCanvasElement.prototype.toBlob;HTMLCanvasElement.prototype.toBlob=function(cb,...args){return original.call(this,b=>setTimeout(()=>cb(b),200),...args);};});
 await page.getByRole('button',{name:'Filecraft PDF',exact:true}).click();await page.getByRole('button',{name:'Cancel processing',exact:true}).click();await expect(page.locator('#status')).toContainText('Cancelled');await expect(page.locator('#result')).toBeHidden();await expect(page.locator('#prepare')).toBeEnabled();
 await page.locator('#profile').selectOption('gray');await page.locator('#paper').selectOption('letter');await page.locator('#margin').fill('24');await page.locator('#dpi').fill('96');await page.getByRole('button',{name:'Filecraft PDF',exact:true}).click();await expect(page.locator('#status')).toContainText('Fits');
 const channels=await page.locator('#previews img').evaluate(async img=>{await img.decode();const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;const x=c.getContext('2d');x.drawImage(img,0,0);return Array.from(x.getImageData(20,20,1,1).data);});expect(Math.abs(channels[0]-channels[1])).toBeLessThan(3);expect(Math.abs(channels[1]-channels[2])).toBeLessThan(3);
 await page.locator('#reviewed').check();const promise=page.waitForEvent('download');await page.locator('#download').click();const d=await promise;await d.saveAs(path.resolve(__dirname,`../../build/portable-evidence/${info.project.name}-gray.pdf`));
});
test('rejects unsupported and oversized headers, cap, clear and impossible budget',async({page})=>{
 await start(page);await page.locator('#files').setInputFiles({name:'not.png',mimeType:'image/png',buffer:Buffer.from('<svg/>')});await expect(page.locator('#status')).toContainText('Choose JPEG or PNG');await expect(page.locator('#pages li')).toHaveCount(0);
 const png=await fixture(page),wide=Buffer.from(png);wide.writeUInt32BE(100000,16);await page.locator('#files').setInputFiles({name:'huge.png',mimeType:'image/png',buffer:wide});await expect(page.locator('#status')).toContainText('24 megapixels');
 await page.locator('#files').setInputFiles(Array.from({length:21},(_,i)=>({name:`${i}.png`,mimeType:'image/png',buffer:png})));await expect(page.locator('#status')).toContainText('Maximum 20 pages');await expect(page.locator('#pages li')).toHaveCount(0);
 await page.locator('#files').setInputFiles(Array.from({length:20},(_,i)=>({name:`${i}.png`,mimeType:'image/png',buffer:png})));await expect(page.locator('#pages li')).toHaveCount(20);await expect(page.getByRole('button',{name:'Split spread'}).first()).toBeDisabled();
 await page.locator('#limit').fill('0.01');await page.getByRole('button',{name:'Filecraft PDF',exact:true}).click();await expect(page.locator('#status')).toContainText('Cannot fit');await expect(page.locator('#download')).toBeHidden();
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'Clear pages',exact:true}).click();await expect(page.locator('#pages li')).toHaveCount(20);page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Clear pages',exact:true}).click();await expect(page.locator('#pages li')).toHaveCount(0);
});
test('responsive keyboard interface and no persistent workspace',async({page})=>{
 await start(page);for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 await page.keyboard.press('Tab');await expect(page.locator('header a')).toBeFocused();
 const png=await fixture(page);await page.locator('#files').setInputFiles({name:'private.png',mimeType:'image/png',buffer:png});await expect(page.locator('#pages li')).toHaveCount(1);await page.reload();await expect(page.locator('#pages li')).toHaveCount(0);
});
