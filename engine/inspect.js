 'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const E=require('./document-engine.js');
const HEADER_LIMIT=262144, MAX_FILE_BYTES=536870912, CHUNK_BYTES=65536;
function fail(code,message){const e=new Error(message);e.code=code;return e;}
function crc32(b){let c=0xffffffff;for(const n of b){c^=n;for(let j=0;j<8;j++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function parseHeader(input,limited=false){
 const b=Buffer.isBuffer(input)?input:Buffer.from(input);
 if(b.length>HEADER_LIMIT)throw fail('INPUT_LIMIT','Header limit exceeded');
 const r={format:'unknown',width:null,height:null,pageCount:null,structuralValidation:'unknown',diagnostics:[]};
 const note=(code,state,params,remediation)=>r.diagnostics.push({code,state,params:params||{},remediation:remediation||['VERIFY_WITH_FORMAT_ADAPTER']});
 function bad(reason){r.structuralValidation='fail';note('MALFORMED_HEADER','fail',{reason});return r;}
 function incomplete(){if(limited){note('HEADER_LIMIT','unknown',{limit:HEADER_LIMIT});return r;}return bad('TRUNCATED_HEADER');}
 if(b.length>=8&&b.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))){
  r.format='png';
  if(b.length<33)return incomplete();
  if(b.readUInt32BE(8)!==13||b.toString('ascii',12,16)!=='IHDR')return bad('INVALID_IHDR');
  if(crc32(b.subarray(12,29))!==b.readUInt32BE(29))return bad('IHDR_CRC');
  const w=b.readUInt32BE(16),h=b.readUInt32BE(20),depth=b[24],color=b[25];
  const depths={0:[1,2,4,8,16],2:[8,16],3:[1,2,4,8],4:[8,16],6:[8,16]};
  if(!w||!h||w>0x7fffffff||h>0x7fffffff||!depths[color]||!depths[color].includes(depth)||b[26]!==0||b[27]!==0||b[28]>1)return bad('INVALID_IHDR_FIELDS');
  if(w>E.LIMITS.dimension||h>E.LIMITS.dimension){note('DIMENSION_LIMIT','unknown',{width:w,height:h});return r;}
  r.width=w;r.height=h;r.pageCount=1;
  note('PIXELS_NOT_DECODED','unknown');note('PNG_PRIMARY_CANVAS_ONLY','unknown',{},['CHECK_ANIMATION_WITH_ADAPTER']);return r;
 }
 if(b.length>=2&&b[0]===255&&b[1]===216){
  r.format='jpeg';let pos=2;
  const sof=new Set([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf]);
  while(pos<b.length){
   if(b[pos++]!==255)return bad('EXPECTED_MARKER');
   while(pos<b.length&&b[pos]===255)pos++;
   if(pos>=b.length)return incomplete();const marker=b[pos++];
   if(marker===0||marker===0xd8)return bad('INVALID_MARKER');
   if(marker===0xd9||marker===0xda)return bad('MISSING_SOF');
   if(marker===1||(marker>=0xd0&&marker<=0xd7))continue;
   if(pos+2>b.length)return incomplete();const len=b.readUInt16BE(pos);
   if(len<2)return bad('INVALID_SEGMENT_LENGTH');
   if(pos+len>b.length)return incomplete();
   if(sof.has(marker)){
    if(len<8)return bad('INVALID_SOF');const h=b.readUInt16BE(pos+3),w=b.readUInt16BE(pos+5),components=b[pos+7];
    if(!w||!h||!components||len!==8+3*components||![8,12,16].includes(b[pos+2]))return bad('INVALID_SOF_FIELDS');
    r.width=w;r.height=h;r.pageCount=1;note('PIXELS_NOT_DECODED','unknown');note('JPEG_RAW_DIMENSIONS','unknown',{},['APPLY_EXIF_ORIENTATION_WITH_ADAPTER']);return r;
   }
   pos+=len;
  }
  return incomplete();
 }
 if(b.length>=5&&b.toString('ascii',0,5)==='%PDF-'){
  r.format='pdf';note('PDF_NOT_PARSED','unknown',{},['VERIFY_PDF_WITH_ADAPTER']);return r;
 }
 note('UNRECOGNIZED_FORMAT','unknown');return r;
}
async function inspectFile(filename,options={}){
 const maxBytes=options.maxBytes===undefined?MAX_FILE_BYTES:options.maxBytes;
 if(!Number.isSafeInteger(maxBytes)||maxBytes<1||maxBytes>MAX_FILE_BYTES)throw fail('INVALID_OPTIONS','Invalid byte limit');
 const cancelled=()=>{if(options.signal&&options.signal.aborted)throw fail('CANCELLED','Inspection cancelled');};
 cancelled();
 const before=await fs.stat(filename);if(!before.isFile())throw fail('NOT_REGULAR_FILE','Expected regular file');
 if(before.size>maxBytes)throw fail('FILE_LIMIT','File exceeds inspection limit');
 const handle=await fs.open(filename,'r');
 try{
  const stat=await handle.stat();if(!stat.isFile())throw fail('NOT_REGULAR_FILE','Expected regular file');
  if(stat.size>maxBytes)throw fail('FILE_LIMIT','File exceeds inspection limit');
  const hash=crypto.createHash('sha256'),chunk=Buffer.alloc(CHUNK_BYTES),header=Buffer.alloc(Math.min(stat.size,HEADER_LIMIT));
  let total=0,captured=0;
  while(true){
   cancelled();const {bytesRead}=await handle.read(chunk,0,chunk.length,null);if(!bytesRead)break;
   total+=bytesRead;if(total>maxBytes)throw fail('FILE_LIMIT','File exceeds inspection limit');
   const part=chunk.subarray(0,bytesRead);hash.update(part);
   const copy=Math.min(bytesRead,header.length-captured);if(copy>0){part.copy(header,captured,0,copy);captured+=copy;}
  }
  cancelled();const after=await handle.stat();
  if(total!==stat.size||after.size!==stat.size||after.mtimeMs!==stat.mtimeMs||after.ctimeMs!==stat.ctimeMs)throw fail('FILE_CHANGED','File changed during inspection');
  const parsed=parseHeader(header.subarray(0,captured),total>HEADER_LIMIT);
  const pages=parsed.width===null?[]:[{id:'page-1',width:parsed.width,height:parsed.height,unit:'px',rotation:0}];
  const document=E.createDocument({format:parsed.format,bytes:total,filename:path.basename(filename),pageCount:parsed.pageCount,structuralValidation:parsed.structuralValidation,pages});
  return {version:1,document,sha256:hash.digest('hex'),headerBytes:captured,diagnostics:parsed.diagnostics};
 }finally{await handle.close();}
}
module.exports={HEADER_LIMIT,MAX_FILE_BYTES,parseHeader,inspectFile};
