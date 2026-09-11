const {test,expect}=require('@playwright/test');const {pathToFileURL}=require('node:url');const path=require('node:path');
test('custom DPI background cleanup and per-page actions invalidate result',async({page})=>{
 await page.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);
 const buffer=Buffer.from(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=600;c.height=400;const x=c.getContext('2d');x.fillStyle='#eeebea';x.fillRect(0,0,600,400);x.fillStyle='#141414';x.fillRect(300,0,300,400);return c.toDataURL().split(',')[1];}),'base64');
 await page.locator('#files').setInputFiles({name:'scan.png',mimeType:'image/png',buffer});await expect(page.locator('#pages li')).toHaveCount(1);
 await page.locator('#dpi').fill('175');await page.locator('#background').selectOption('225');await page.locator('#prepare').click();await expect(page.locator('#status')).toContainText('Fits');
 const pixel=await page.locator('#previews img').evaluate(async im=>{await im.decode();const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const x=c.getContext('2d');x.drawImage(im,0,0);return [...x.getImageData(30,30,1,1).data];});expect(pixel[0]).toBeGreaterThan(250);
 await page.getByRole('button',{name:'Duplicate page 1',exact:true}).click();await expect(page.locator('#pages li')).toHaveCount(2);await expect(page.locator('#result')).toBeHidden();await page.getByRole('button',{name:'Rotate page 2',exact:true}).click();await expect(page.locator('#pages li').nth(1)).toContainText('90°');await page.getByRole('button',{name:'Remove page 1',exact:true}).click();await expect(page.locator('#pages li')).toHaveCount(1);await expect(page.locator('#pages li')).toContainText('90°');
});
test('serial repeated batches stay within page and output budgets',async({page})=>{
 await page.goto(pathToFileURL(path.resolve(__dirname,'../index.html')).href);
 const buffer=Buffer.from(await page.evaluate(()=>{const c=document.createElement('canvas');c.width=1200;c.height=1600;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,c.width,c.height);x.fillStyle='black';x.font='40px sans-serif';x.fillText('Synthetic regression',30,100);return c.toDataURL().split(',')[1];}),'base64');
 await page.locator('#files').setInputFiles(Array.from({length:20},(_,i)=>({name:`${i}.png`,mimeType:'image/png',buffer})));await expect(page.locator('#pages li')).toHaveCount(20);
 for(const profile of ['balanced','small','gray']){await page.locator('#profile').selectOption(profile);await page.locator('#prepare').click();await expect(page.locator('#status')).toContainText('Fits',{timeout:60000});await expect(page.locator('#previews img')).toHaveCount(20);}
 await expect(page.getByRole('button',{name:'Duplicate page 1',exact:true})).toBeDisabled();
});
