'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {spawnSync}=require('node:child_process');
const {createHash}=require('node:crypto');
const lib=require('../vendor/pdf-lib.min.js');
const cli=path.resolve(__dirname,'../cli.cjs');
const run=(...args)=>spawnSync(process.execPath,[cli,...args],{encoding:'utf8',timeout:35000});
async function setup(t) {
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'prepare-pdf-test-')); t.after(()=>fs.rm(dir,{recursive:true,force:true}));
 const doc=await lib.PDFDocument.create(); for(const size of [[123,456],[789,321]]) doc.addPage(size).drawText('visible text');
 const input=path.join(dir,'source with spaces.pdf'); await fs.writeFile(input,await doc.save()); return {dir,input};
}
test('CLI inspects and exclusively writes a reordered rotation while originals remain unchanged',async t=>{
 const {dir,input}=await setup(t), output=path.join(dir,'output.pdf');
 const before=createHash('sha256').update(await fs.readFile(input)).digest('hex');
 let r=run('inspect',input); assert.equal(r.status,0,r.stderr+r.stdout); assert.equal(JSON.parse(r.stdout).result.pageCount,2);
 r=run('transform','--output',output,'--pages','2,1,2','--rotate','90',input);
 assert.equal(r.status,0,r.stderr+r.stdout); const result=JSON.parse(r.stdout); assert.equal(result.ok,true); assert.equal(result.result.pageCount,3);
 const out=await lib.PDFDocument.load(await fs.readFile(output)); assert.deepEqual(out.getPages().map(p=>[p.getWidth(),p.getHeight(),p.getRotation().angle]),[[789,321,90],[123,456,90],[789,321,90]]);
 const outputBytes=await fs.readFile(output);
 for(const target of [input,output]) {r=run('transform','--output',target,input);assert.equal(r.status,3);assert.equal(JSON.parse(r.stdout).error.code,'OUTPUT_EXISTS');}
 assert.deepEqual(await fs.readFile(output),outputBytes);
 assert.equal(createHash('sha256').update(await fs.readFile(input)).digest('hex'),before);
 const merged=path.join(dir,'merged.pdf');r=run('transform','--output',merged,input,input);assert.equal(r.status,0,r.stdout+r.stderr);assert.equal(JSON.parse(r.stdout).result.pageCount,4);
});
