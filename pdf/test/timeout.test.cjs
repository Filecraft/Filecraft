'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');const {spawnSync}=require('node:child_process');
test('CLI really terminates a nonresponsive worker at its 30 second deadline',{timeout:35000},async t=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'prepare-pdf-timeout-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));
 await fs.copyFile(path.resolve(__dirname,'../cli.cjs'),path.join(dir,'cli.cjs'));
 await fs.writeFile(path.join(dir,'worker.cjs'),'while(true) {}');
 const started=Date.now();const r=spawnSync(process.execPath,[path.join(dir,'cli.cjs'),'inspect','unused.pdf'],{encoding:'utf8',timeout:34000});
 assert.equal(r.status,5,r.stdout+r.stderr);assert.equal(JSON.parse(r.stdout).error.code,'TIMEOUT');assert.ok(Date.now()-started>=29000);assert.ok(Date.now()-started<34000);
});
