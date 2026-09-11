'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');
const {spawnSync}=require('node:child_process');const lib=require('../vendor/pdf-lib.min.js');
const run=(...args)=>spawnSync(process.execPath,[path.resolve(__dirname,'../cli.cjs'),...args],{encoding:'utf8',timeout:35000});
test('help and version are JSON and exit zero',()=>{
 for(const flag of ['--help','--version']){const r=run(flag);assert.equal(r.status,0,r.stdout+r.stderr);assert.equal(JSON.parse(r.stdout).ok,true);}
});
test('CLI rejects bad paths, bounds and invalid selections without outputs',async t=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'prepare-pdf-boundaries-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));
 const input=path.join(dir,'good.pdf'),output=path.join(dir,'new.pdf'),link=path.join(dir,'link.pdf');
 const doc=await lib.PDFDocument.create();doc.addPage([200,400]);await fs.writeFile(input,await doc.save());await fs.symlink(input,link);
 const big=path.join(dir,'huge.pdf');const fd=await fs.open(big,'w');await fd.truncate(20971521);await fd.close();
 for(const [file,code] of [[dir,'INPUT_PATH'],[link,'INPUT_PATH'],[path.join(dir,'missing.pdf'),'ENOENT'],[big,'LIMIT'],...(process.platform==='win32'?[]:[['/dev/null','INPUT_PATH']])]){
  const r=run('inspect',file);assert.notEqual(r.status,0);assert.equal(JSON.parse(r.stdout).error.code,code,r.stdout);
 }
 for(const pages of ['0','2','2-1','1-9999999999999999','1,','1.0','-1','1,,1']){
  const r=run('transform','--output',output,'--pages',pages,input);assert.notEqual(r.status,0,r.stdout);await assert.rejects(fs.stat(output),{code:'ENOENT'});
 }
 for(const args of [[],['inspect'],['transform','--output',output,'--bogus','x',input],['transform','--output',output,'--rotate','45',input],['transform','--output',output,'--max-bytes','1.5',input],['transform','--output',output,'--pages','1',input,input]]){
  const r=run(...args);assert.equal(r.status,2,r.stdout);assert.equal(JSON.parse(r.stdout).error.code,'USAGE');
 }
 const r=run('transform','--output',output,'--max-bytes','10',input);assert.equal(r.status,4,r.stdout);assert.equal(JSON.parse(r.stdout).error.code,'OUTPUT_LIMIT');await assert.rejects(fs.stat(output),{code:'ENOENT'});
 const broken=path.join(dir,'bad.pdf');await fs.writeFile(broken,'%PDF-1.7\nmissing rest');assert.equal(run('inspect',broken).status,4);
 const symlinkOutput=path.join(dir,'out-link.pdf');await fs.symlink(path.join(dir,'nonexistent'),symlinkOutput);assert.equal(run('transform','--output',symlinkOutput,input).status,3);
 const dash=path.join(dir,'-document.pdf');await fs.copyFile(input,dash);assert.equal(run('inspect','--',dash).status,0);
});
