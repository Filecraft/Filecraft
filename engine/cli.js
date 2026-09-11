#!/usr/bin/env node
'use strict';
const fs=require('node:fs/promises');
const E=require('./document-engine.js'),{inspectFile}=require('./inspect.js');
const controller=new AbortController();
process.on('SIGINT',()=>controller.abort());
function failure(code,message){const e=new Error(message);e.code=code;return e;}
async function readJSON(filename){
 const stat=await fs.stat(filename);if(!stat.isFile())throw failure('NOT_REGULAR_FILE','Expected regular JSON file');
 if(stat.size>E.LIMITS.jsonBytes)throw failure('INPUT_LIMIT','JSON input too large');
 const h=await fs.open(filename,'r');
 try{
  const b=Buffer.alloc(E.LIMITS.jsonBytes+1);let n=0;
  while(n<b.length){if(controller.signal.aborted)throw failure('CANCELLED','Read cancelled');const r=await h.read(b,n,b.length-n,null);if(!r.bytesRead)break;n+=r.bytesRead;}
  if(n>E.LIMITS.jsonBytes)throw failure('INPUT_LIMIT','JSON input too large');
  let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(b.subarray(0,n));}catch(_){throw failure('INVALID_JSON','JSON must be valid UTF-8');}
  return E.parseJSON(text);
 }finally{await h.close();}
}
const HELP={version:1,prerequisite:'Node.js 22 or later; no npm install needed',commands:['node engine/cli.js inspect <file>','node engine/cli.js validate <file> <profile.json>','node engine/cli.js profile validate|import|export <profile.json>','node engine/cli.js workflow <document-model.json> <workflow.json>'],notes:['All output is JSON on stdout. Paths are positional; quote paths containing spaces.','Profile operations validate and emit canonical JSON to stdout; no registry or implicit file writes.','Workflow always performs a dry-run on a document model. No file transformations or command execution.','Inspect verifies headers and hashes, not pixel decoding or full document structure. PDF page counts remain unknown.'],exitCodes:{0:'Inspection/transfer/dry-run succeeded, or readiness READY',2:'Readiness NOT_READY',3:'Readiness UNKNOWN',4:'Invalid command, JSON, profile, model, workflow, or bounded input',5:'Filesystem/I/O error',130:'Cancelled'}};
async function main(args){
 const [command,a,b]=args;
 if((command==='--help'||command==='help')&&args.length===1||args.length===0)return HELP;
 if(command==='inspect'&&args.length===2)return inspectFile(a,{signal:controller.signal});
 if(command==='validate'&&args.length===3){
  const profile=E.validateProfile(await readJSON(b));
  const inspection=await inspectFile(a,{signal:controller.signal});
  const readiness=E.evaluate(inspection.document,profile);process.exitCode={READY:0,NOT_READY:2,UNKNOWN:3}[readiness.status];
  return {...inspection,readiness};
 }
 if(command==='profile'&&args.length===3&&['validate','import','export'].includes(a))return E.validateProfile(await readJSON(b));
 if(command==='workflow'&&args.length===3){
  const document=E.createDocument(await readJSON(a)),workflow=E.validateWorkflow(await readJSON(b));
  const result=await E.runWorkflow(document,workflow,{signal:controller.signal});
  return {version:1,dryRun:true,stepsCompleted:result.stepsCompleted,document:result.document,diagnostics:[{code:'MODEL_ONLY','state':'unknown',params:{},remediation:['EXPORT_AND_REINSPECT_WITH_ADAPTER']}]};
 }
 throw failure('USAGE','Unknown command or incorrect argument count; use --help');
}
main(process.argv.slice(2)).then(result=>process.stdout.write(JSON.stringify(result,null,2)+'\n')).catch(e=>{
 const code=e.code||'INTERNAL_ERROR';
 process.exitCode=code==='CANCELLED'?130:/^(E[A-Z]+|NOT_REGULAR_FILE|FILE_CHANGED|INTERNAL_ERROR)$/.test(code)?5:4;
 process.stdout.write(JSON.stringify({version:1,error:{code,message:e.message,params:e.params||{}}},null,2)+'\n');
});
