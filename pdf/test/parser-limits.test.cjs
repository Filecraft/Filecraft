'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const zlib=require('node:zlib');const L=require('../vendor/pdf-lib.min.js');const api=require('../document.js');
async function objectStreams(sizes){const d=await L.PDFDocument.create();d.addPage([100,200]);for(const [i,size]of sizes.entries()){const decoded=Buffer.alloc(size,32);decoded.write(`${123+i} 0 <<>>`);d.context.register(d.context.stream(zlib.deflateSync(decoded),{Type:'ObjStm',N:1,First:6,Filter:'FlateDecode'}));}return d.save({useObjectStreams:false});}
test('decoder preallocation gate refuses invalid/oversized requests without growing buffer',()=>{
 const context=L.PDFContext.create();const stream=L.decodePDFRawStream(context.stream(new Uint8Array([120,156,3,0,0,0,0,1]),{Filter:'FlateDecode'}));
 for(const amount of [-1,NaN,Infinity,1.5,33554433]){assert.throws(()=>stream.ensureBuffer(amount),e=>e.code==='LIMIT');assert.equal(stream.buffer.byteLength,0);}
});
test('compressed object stream over 32 MiB is rejected before huge allocation',async()=>{await assert.rejects(api.inspect(await objectStreams([33*1024*1024])),e=>['LIMIT','INVALID_PDF'].includes(e.code));});
test('cumulative decompression is bounded and resets after a rejected job',async()=>{await assert.rejects(api.inspect(await objectStreams([25*1024*1024,25*1024*1024,25*1024*1024])),e=>['LIMIT','INVALID_PDF'].includes(e.code));const d=await L.PDFDocument.create();d.addPage();assert.equal((await api.inspect(await d.save())).pageCount,1);});
test('xref widths/counts are checked before decoding its stream',async()=>{
 for(const extra of [{W:[1,999999999,2]},{W:[1,-1,2]},{W:[1,2,3,4]},{W:[0,0,0]},{W:[1,2,2],Size:1000000000},{W:[1,2,2],Index:[0,1000000000]}]){
  const d=await L.PDFDocument.create();d.addPage();d.context.register(d.context.stream(new Uint8Array(),{Type:'XRef',Size:1,W:[1,2,2],...extra}));await assert.rejects(api.inspect(await d.save({useObjectStreams:false})),e=>['LIMIT','INVALID_PDF'].includes(e.code));
 }
});
