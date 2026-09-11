 'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),{spawnSync}=require('node:child_process'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const cli=path.resolve(__dirname,'../cli.js');
function run(args){const p=spawnSync(process.execPath,[cli,...args],{encoding:'utf8'});assert.equal(p.stderr,'');return {code:p.status,data:JSON.parse(p.stdout)};}
test('CLI inspect, validate, canonical profile transfer and dry-run use real files',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'engine-cli-'));const file=n=>path.join(dir,n);
 try{
  fs.writeFileSync(file('résumé.pdf'),'%PDF-1.7\n/Type /Page /Count 99');
  fs.writeFileSync(file('profile.json'),JSON.stringify({version:1,id:'local',constraints:{formats:['pdf'],pageCount:{max:2}}}));
  const inspect=run(['inspect',file('résumé.pdf')]);assert.equal(inspect.code,0);assert.equal(inspect.data.document.pageCount,null);assert.equal(inspect.data.sha256.length,64);
  const validation=run(['validate',file('résumé.pdf'),file('profile.json')]);assert.equal(validation.code,3);assert.equal(validation.data.readiness.status,'UNKNOWN');
  fs.writeFileSync(file('profile.json'),JSON.stringify({version:1,id:'local',constraints:{bytes:{max:1}}}));
  assert.equal(run(['validate',file('résumé.pdf'),file('profile.json')]).code,2);
  for(const verb of ['validate','import','export']){const r=run(['profile',verb,file('profile.json')]);assert.equal(r.code,0);assert.equal(r.data.id,'local');}
  fs.writeFileSync(file('model.json'),JSON.stringify({format:'png',bytes:10,filename:'x.png',pageCount:1,structuralValidation:'unknown',pages:[{id:'page-1',width:10,height:20,unit:'px',rotation:0}]}));
  fs.writeFileSync(file('workflow.json'),JSON.stringify({version:1,steps:[{op:'rotate',pageIds:['page-1'],degrees:90}]}));
  const result=run(['workflow',file('model.json'),file('workflow.json')]);assert.equal(result.code,0);assert.equal(result.data.dryRun,true);assert.equal(result.data.document.pages[0].rotation,90);assert.equal(JSON.parse(fs.readFileSync(file('model.json'))).pages[0].rotation,0);
  assert.equal(run(['inspect',file('missing')]).code,5);assert.equal(run(['inspect',dir]).code,5);
  assert.equal(run(['unknown']).code,4);assert.equal(run(['--help']).code,0);
  fs.writeFileSync(file('profile.json'),'{');assert.equal(run(['profile','import',file('profile.json')]).code,4);
  fs.writeFileSync(file('profile.json'),' '.repeat(1048577));assert.equal(run(['profile','import',file('profile.json')]).data.error.code,'INPUT_LIMIT');
  fs.writeFileSync(file('workflow.json'),JSON.stringify({version:1,steps:[{op:'exec',path:file('should-not-exist')}]}));
  assert.equal(run(['workflow',file('model.json'),file('workflow.json')]).code,4);assert.equal(fs.existsSync(file('should-not-exist')),false);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
