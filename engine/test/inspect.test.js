 'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const I=require('../inspect.js');
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8V8AAAAASUVORK5CYII=','base64');
test('bounded PNG headers and streaming SHA256 on Unicode paths',async()=>{
 const dir=await fs.mkdtemp(path.join(os.tmpdir(),'document-engine-'));
 try{const file=path.join(dir,'履歴 résumé.png');await fs.writeFile(file,png);const r=await I.inspectFile(file);
 assert.equal(r.document.format,'png');assert.equal(r.document.pages[0].width,1);assert.equal(r.document.structuralValidation,'unknown');assert.equal(r.sha256,crypto.createHash('sha256').update(png).digest('hex'));
 assert.ok(r.diagnostics.some(d=>d.code==='PIXELS_NOT_DECODED'));assert.ok(r.headerBytes<=I.HEADER_LIMIT);
 await assert.rejects(I.inspectFile(file,{maxBytes:10}),e=>e.code==='FILE_LIMIT');
 await assert.rejects(I.inspectFile(dir),e=>e.code==='NOT_REGULAR_FILE');
 await assert.rejects(I.inspectFile(path.join(dir,'missing')),e=>e.code==='ENOENT');
 const ac=new AbortController();ac.abort();await assert.rejects(I.inspectFile(file,{signal:ac.signal}),e=>e.code==='CANCELLED');
 }finally{await fs.rm(dir,{recursive:true,force:true});}
});
test('header parsing rejects malformed dimensions/segments without claiming pixel validation',()=>{
 const bad=Buffer.from(png);bad.writeUInt32BE(0,16);assert.equal(I.parseHeader(bad).structuralValidation,'fail');
 assert.equal(I.parseHeader(png.subarray(0,12)).structuralValidation,'fail');
 const crc=Buffer.from(png);crc[32]^=1;assert.equal(I.parseHeader(crc).structuralValidation,'fail');
 const jpeg=Buffer.from([255,216,255,192,0,11,8,0,20,0,10,1,1,17,0,255,217]);
 const j=I.parseHeader(jpeg);assert.equal(j.format,'jpeg');assert.equal(j.width,10);assert.equal(j.height,20);assert.equal(j.structuralValidation,'unknown');
 assert.equal(I.parseHeader(Buffer.from([255,216,255,224,0,1])).structuralValidation,'fail');
 assert.equal(I.parseHeader(Buffer.from([255,216,255,224,0,255]),true).structuralValidation,'unknown');
 assert.equal(I.parseHeader(Buffer.from('not an image')).format,'unknown');
 const pdf=I.parseHeader(Buffer.from('%PDF-1.7\n/Type /Page /Count 42'));
 assert.equal(pdf.format,'pdf');assert.equal(pdf.pageCount,null);assert.equal(pdf.structuralValidation,'unknown');assert.ok(pdf.diagnostics.some(x=>x.code==='PDF_NOT_PARSED'));
});
module.exports={png};
