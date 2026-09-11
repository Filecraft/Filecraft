 'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),{spawn}=require('node:child_process');
const I=require('../inspect.js');
test('multi-chunk stream hashes all bytes while header allocation is bounded',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'engine-stream-'));
 try{
  const p=path.join(dir,'large.bin'),data=Buffer.alloc(I.HEADER_LIMIT*3,0x51);await fs.writeFile(p,data);
  const r=await I.inspectFile(p);assert.equal(r.document.bytes,data.length);assert.equal(r.headerBytes,I.HEADER_LIMIT);assert.equal(r.sha256,crypto.createHash('sha256').update(data).digest('hex'));
  let reads=0;await assert.rejects(I.inspectFile(p,{signal:{get aborted(){return ++reads>3;}}}),e=>e.code==='CANCELLED');
  await assert.rejects(I.inspectFile(p,{maxBytes:Infinity}),e=>e.code==='INVALID_OPTIONS');
  const sparse=await fs.open(p,'w');await sparse.truncate(I.MAX_FILE_BYTES+1);await sparse.close();await assert.rejects(I.inspectFile(p),e=>e.code==='FILE_LIMIT');
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
test('bounded deterministic malformed-header corpus never crashes',()=>{
 let seed=19;for(let size=0;size<500;size++){
  const bytes=Buffer.alloc(size);for(let i=0;i<size;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;bytes[i]=seed&255;}
  if(size>2){bytes[0]=255;bytes[1]=216;}
  const result=I.parseHeader(bytes);assert.ok(['unknown','fail'].includes(result.structuralValidation));
 }
 assert.throws(()=>I.parseHeader(Buffer.alloc(I.HEADER_LIMIT+1)),e=>e.code==='INPUT_LIMIT');
});
test('filesystem permissions errors are preserved', {skip:process.platform==='win32'||typeof process.getuid==='function'&&process.getuid()===0},async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'engine-perm-'));const p=path.join(dir,'locked');
 try{await fs.writeFile(p,'x');await fs.chmod(p,0);await assert.rejects(I.inspectFile(p),e=>e.code==='EACCES');}
 finally{await fs.chmod(p,0o600);await fs.rm(dir,{recursive:true,force:true});}
});
test('SIGINT cancels an active CLI workflow with JSON exit 130',{skip:process.platform==='win32'},async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'engine-cancel-'));
 try{
  await fs.writeFile(path.join(dir,'w.json'),JSON.stringify({version:1,steps:Array.from({length:128},()=>({op:'rotate',pageIds:['page-1'],degrees:90}))}));
  const script="process.argv=[process.execPath,...process.argv.slice(1)];require(process.argv[1]);process.send('ready');";
  const child=spawn(process.execPath,['-e',script,path.join(__dirname,'../cli.js'),'workflow',path.join(__dirname,'../examples/document.json'),path.join(dir,'w.json')],{stdio:['ignore','pipe','pipe','ipc']});
  let stdout='',stderr='';child.stdout.on('data',c=>stdout+=c);child.stderr.on('data',c=>stderr+=c);
  // IPC proves the CLI installed its signal handler; no timing-based startup guess.
  child.once('message',()=>{child.kill('SIGINT');child.disconnect();});
  const [code]=await Promise.all([new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',resolve);}),new Promise(resolve=>child.stdout.once('end',resolve)),new Promise(resolve=>child.stderr.once('end',resolve))]);
  assert.equal(stderr,'');assert.equal(code,130);assert.equal(JSON.parse(stdout).error.code,'CANCELLED');
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
