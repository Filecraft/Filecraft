 'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),E=require('../document-engine.js');
test('browser UMD works without Node globals',async()=>{
 const c=vm.createContext({setTimeout,TextEncoder});vm.runInContext(fs.readFileSync(path.join(__dirname,'../document-engine.js'),'utf8'),c);
 const r=vm.runInContext(`DocumentEngine.evaluate(DocumentEngine.createDocument({format:'pdf',bytes:1,filename:'a.pdf',pageCount:null,structuralValidation:'unknown',pages:[]}),{version:1,id:'browser',constraints:{pageCount:{max:2}}})`,c);
 assert.equal(r.status,'UNKNOWN');assert.equal(typeof c.DocumentEngine.runWorkflow,'function');
});
test('prototype keys, non-finite constraints, oversized UTF-8 and page evidence fail closed',()=>{
 for(const v of [NaN,Infinity,-1,1.5,'1'])assert.throws(()=>E.validateProfile({version:1,id:'x',constraints:{bytes:{max:v}}}));
 assert.throws(()=>E.validateProfile({version:1,id:'x',constraints:JSON.parse('{"__proto__":{"max":3}}')}));
 assert.throws(()=>E.parseJSON('é'.repeat(E.LIMITS.jsonBytes)),e=>e.code==='INPUT_LIMIT');
 const d={format:'png',filename:'x.png',bytes:1,pageCount:2,structuralValidation:'pass',pages:[{id:'a',width:10,height:20,unit:'px',rotation:90}]};
 assert.equal(E.evaluate(d,{version:1,id:'x',constraints:{orientation:'landscape'}}).status,'UNKNOWN');
 assert.equal(E.evaluate({...d,pageCount:1},{version:1,id:'x',constraints:{dimensions:{unit:'pt',minWidth:1}}}).status,'UNKNOWN');
 assert.throws(()=>E.createDocument({...d,pages:[d.pages[0],d.pages[0]]}));
 assert.throws(()=>E.validateProfile({version:1,id:'x',constraints:{dimensions:{unit:'px',minWidth:30,maxWidth:10}}}));
});
test('zero-step workflows honor cancellation, and output never shares mutable input',async()=>{
 const original={format:'png',filename:'x.png',bytes:1,pageCount:1,structuralValidation:'pass',pages:[{id:'a',width:10,height:20,unit:'px',rotation:0}]};
 const result=await E.runWorkflow(original,{version:1,steps:[]});original.pages[0].width=50;assert.equal(result.document.pages[0].width,10);
 await assert.rejects(E.runWorkflow(original,{version:1,steps:[]},{signal:{aborted:true}}),e=>e.code==='CANCELLED');
 assert.throws(()=>E.undo({past:[],present:original,future:[]}));
});
test('profile export is deterministic regardless of imported key order',()=>{
 const a={version:1,id:'stable',constraints:{bytes:{min:0,max:20},formats:['png']}};
 const b={constraints:{formats:['png'],bytes:{max:20,min:0}},id:'stable',version:1};
 assert.equal(JSON.stringify(E.validateProfile(a)),JSON.stringify(E.validateProfile(b)));
});
