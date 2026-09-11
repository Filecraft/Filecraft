#!/usr/bin/env node
'use strict';
const fs=require('node:fs/promises');
const path=require('node:path');
const {Worker}=require('node:worker_threads');
function fail(code,message){throw Object.assign(new Error(message),{code});}
function parse(args) {
 const command=args.shift();
 if(!['inspect','transform'].includes(command)) fail('USAGE','Expected inspect or transform.');
 const request={command,inputs:[],rotate:0,maxBytes:52428800}; const seen=new Set(); let literal=false;
 for(let i=0;i<args.length;i++) {
  const arg=args[i];
  if(arg==='--'&&!literal){literal=true;continue;}
  if(!literal&&arg.startsWith('-')) {
   if(!['--output','--pages','--rotate','--max-bytes'].includes(arg)||command==='inspect'||seen.has(arg)||i+1>=args.length) fail('USAGE','Unknown, duplicate or incomplete option.');
   seen.add(arg);const value=args[++i];
   if(arg==='--output') request.output=value;
   if(arg==='--pages') request.pages=value;
   if(arg==='--rotate') {if(!/^-?\d+$/.test(value)||!Number.isSafeInteger(Number(value))||Number(value)%90)fail('USAGE','Rotation must be an integer multiple of 90.');request.rotate=Number(value);}
   if(arg==='--max-bytes') {if(!/^\d+$/.test(value)||!Number.isSafeInteger(Number(value))||Number(value)<1||Number(value)>52428800)fail('USAGE','max-bytes must be 1–52428800.');request.maxBytes=Number(value);}
  }else request.inputs.push(arg);
 }
 if(!request.inputs.length||request.inputs.length>10||(command==='inspect'&&request.inputs.length!==1)||(command==='transform'&&!request.output)||(request.pages!==undefined&&request.inputs.length!==1)) fail('USAGE','Invalid input count, missing output, or --pages used with multiple inputs.');
 return request;
}
function isolated(request) {
 return new Promise((resolve,reject)=>{
  const worker=new Worker(path.join(__dirname,'worker.cjs'),{workerData:request,resourceLimits:{maxOldGenerationSizeMb:256,maxYoungGenerationSizeMb:32,stackSizeMb:4},stdout:true,stderr:true});
  // Drain parser diagnostics; the CLI protocol is exactly one JSON object.
  worker.stdout.resume();worker.stderr.resume();let done=false;
  const finish=(error,result)=>{if(done)return;done=true;clearTimeout(timer);void worker.terminate();error?reject(error):resolve(result);};
  const timer=setTimeout(()=>finish(Object.assign(new Error('PDF operation exceeded 30 seconds.'),{code:'TIMEOUT'})),30000);
  worker.on('message',message=>message.ok?finish(null,message):finish(Object.assign(new Error(message.error.message),{code:message.error.code})));
  worker.on('error',()=>finish(Object.assign(new Error('PDF worker failed or exceeded its memory limit.'),{code:'RESOURCE_LIMIT'})));
  worker.on('exit',()=>{if(!done)finish(Object.assign(new Error('PDF worker exited without a result.'),{code:'WORKER_FAILED'}));});
 });
}
async function main(args) {
 if(Number(process.versions.node.split('.')[0])<22)fail('USAGE','Node 22 or newer is required.');
 if(args.length===1&&args[0]==='--version')return {ok:true,version:'0.7.0-beta.1',pdfLib:'1.17.1',nodeMinimum:22};
 if(args.length===1&&args[0]==='--help')return {ok:true,usage:['node pdf/cli.cjs inspect FILE','node pdf/cli.cjs transform --output FILE [--pages 1,3-5] [--rotate 90] [--max-bytes N] INPUT...'],notes:['Output must not exist. Sources are never written.','Pages are 1-based, order and duplicates preserved; --pages requires one input.','Use -- before input paths beginning with a dash.','Local only; 30 second worker timeout; 256 MiB V8 old-generation limit (not total RSS).','Structural parsing is not a content/readability/safety guarantee.'],exitCodes:{0:'success',2:'usage',3:'filesystem',4:'PDF/plan/limits',5:'worker/timeout'}};
 const request=parse(args);
 if(request.output){try{await fs.lstat(request.output);fail('OUTPUT_EXISTS','Output already exists; choose a new path.');}catch(error){if(error.code!=='ENOENT')throw error;}}
 const response=await isolated(request);
 if(request.output){
  let handle;
  try {handle=await fs.open(request.output,'wx',0o600);await handle.writeFile(response.bytes);await handle.sync();}
  catch(error){if(error.code==='EEXIST')fail('OUTPUT_EXISTS','Output already exists; choose a new path.');throw error;}
  finally {if(handle)await handle.close();}
  return {ok:true,command:request.command,output:path.resolve(request.output),result:response.result};
 }
 return {ok:true,command:request.command,result:response.result};
}
main(process.argv.slice(2)).then(result=>console.log(JSON.stringify(result))).catch(error=>{
 const code=error.code||'IO_ERROR';
 console.log(JSON.stringify({ok:false,error:{code,message:error.message||'Operation failed.'}}));
 process.exitCode=code==='USAGE'?2:['OUTPUT_EXISTS','ENOENT','EACCES','EPERM','EISDIR','ENOTDIR','ENOSPC','EROFS','EMFILE','ENFILE','EIO','ENAMETOOLONG','ELOOP','IO_ERROR','INPUT_PATH','INPUT_CHANGED'].includes(code)?3:['TIMEOUT','RESOURCE_LIMIT','WORKER_FAILED'].includes(code)?5:4;
});
