'use strict';
const {workerData,parentPort}=require('node:worker_threads');
const fs=require('node:fs/promises');
const {constants}=require('node:fs');
const api=require('./document.js');
function fail(code,message){throw Object.assign(new Error(message),{code});}
async function readInput(file) {
 const before=await fs.lstat(file);
 if(!before.isFile()||before.isSymbolicLink())fail('INPUT_PATH','Input must be a regular file, not a symlink or special file.');
 if(before.size>api.limits.maxInputBytes)fail('LIMIT','Input exceeds 20 MiB.');
 const handle=await fs.open(file,constants.O_RDONLY|(constants.O_NOFOLLOW||0)|(constants.O_NONBLOCK||0));
 try {
  const stat=await handle.stat();
  if(!stat.isFile()||stat.dev!==before.dev||stat.ino!==before.ino)fail('INPUT_PATH','Input changed while opening.');
  if(stat.size>api.limits.maxInputBytes)fail('LIMIT','Input exceeds 20 MiB.');
  const bytes=Buffer.alloc(stat.size);let offset=0;
  while(offset<bytes.length){const {bytesRead}=await handle.read(bytes,offset,bytes.length-offset,offset);if(!bytesRead)fail('INPUT_CHANGED','Input was truncated while reading.');offset+=bytesRead;}
  const probe=Buffer.alloc(1);if((await handle.read(probe,0,1,offset)).bytesRead)fail('INPUT_CHANGED','Input grew while reading.');
  const after=await handle.stat();if(after.size!==stat.size||after.mtimeMs!==stat.mtimeMs||after.ctimeMs!==stat.ctimeMs)fail('INPUT_CHANGED','Input changed while reading.');
  return new Uint8Array(bytes);
 }finally{await handle.close();}
}
async function run(request) {
 const inputs=[];let total=0;
 for(const file of request.inputs){const bytes=await readInput(file);total+=bytes.length;if(total>api.limits.maxTotalBytes)fail('LIMIT','Total inputs exceed 50 MiB.');inputs.push(bytes);}
 if(request.command==='inspect')return {ok:true,result:await api.inspect(inputs[0])};
 const inspections=[];for(const bytes of inputs)inspections.push(await api.inspect(bytes));
 const plan=[];
 if(request.pages!==undefined){
  if(request.pages.length>1000||!/^\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*$/.test(request.pages))fail('INVALID_PLAN','Pages must be a comma-separated list such as 1,3-5.');
  for(const part of request.pages.split(',')){
   const [first,last=first]=part.split('-').map(Number);
   if(!Number.isSafeInteger(first)||!Number.isSafeInteger(last)||first<1||last<first||last>inspections[0].pageCount||plan.length+last-first+1>100)fail('INVALID_PLAN','Page selection out of range or over 100 pages.');
   for(let page=first;page<=last;page++)plan.push({source:0,page:page-1,rotation:request.rotate});
  }
 }else for(const [source,info] of inspections.entries())for(let page=0;page<info.pageCount;page++)plan.push({source,page,rotation:request.rotate});
 const bytes=await api.transform(inputs,plan,{maxBytes:request.maxBytes});
 return {ok:true,bytes,result:{pageCount:plan.length,pages:plan.map(entry=>{const p=inspections[entry.source].pages[entry.page];return {...p,rotation:((p.rotation+(entry.rotation%360))%360+360)%360};}),byteLength:bytes.length,warnings:['Output reloaded and page geometry verified; not a content or readability guarantee.']}};
}
run(workerData).then(message=>parentPort.postMessage(message,message.bytes?[message.bytes.buffer]:[])).catch(error=>parentPort.postMessage({ok:false,error:{code:error.code||'INVALID_PDF',message:error.message||'PDF operation failed.'}}));
