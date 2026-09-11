'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const lib=require('../vendor/pdf-lib.min.js');const api=require('../document.js');
test('browser UMD exports shared operations without CommonJS',async()=>{
 const context=vm.createContext({setTimeout,clearTimeout,Uint8Array,ArrayBuffer});
 for(const file of ['vendor/pdf-lib.min.js','document.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'..',file),'utf8'),context);
 assert.equal(typeof context.PreparePDF.inspect,'function');
 const result=await vm.runInContext('(async()=>{const d=await PDFLib.PDFDocument.create();d.addPage([111,222]);const a=await d.save();return PreparePDF.inspect(await PreparePDF.transform([a],[{source:0,page:0,rotation:90}],{maxBytes:10000}));})()',context);
 assert.equal(result.pageCount,1);assert.equal(result.pages[0].rotation,90);assert.equal(result.pages[0].width,111);
});
test('preserves shifted page boxes and text/vector streams',async()=>{
 const doc=await lib.PDFDocument.create();const page=doc.addPage([250,500]);page.setMediaBox(-10,12,250,500);page.setCropBox(5,25,190,400);page.setTrimBox(9,30,175,390);page.drawText('Actual embedded text');page.drawRectangle({x:25,y:75,width:32,height:57});
 const original=await doc.save();const bytes=await api.transform([original],[{source:0,page:0,rotation:90}],{maxBytes:10000});const output=await lib.PDFDocument.load(bytes);const p=output.getPage(0);
 assert.deepEqual(p.getMediaBox(),page.getMediaBox());assert.deepEqual(p.getCropBox(),page.getCropBox());assert.deepEqual(p.getTrimBox(),page.getTrimBox());
 function contents(d,p){const a=p.node.Contents();return a.asArray().map(ref=>Buffer.from(lib.decodePDFRawStream(d.context.lookup(ref)).decode()).toString()).join('');}
 const reloaded=await lib.PDFDocument.load(original);assert.equal(contents(output,p),contents(reloaded,reloaded.getPage(0)));assert.match(contents(output,p),/ Tj/);assert.match(contents(output,p),/ re| l/);
});
test('inherited geometry and rotation survive selected-page copying',async()=>{
 const d=await lib.PDFDocument.create();const p=d.addPage([240,360]);p.drawText('inherit');const parent=d.context.lookup(p.node.get(lib.PDFName.of('Parent')));
 parent.set(lib.PDFName.of('Rotate'),lib.PDFNumber.of(90));p.node.delete(lib.PDFName.of('Rotate'));
 const b=await d.save();const out=await api.transform([b],[{source:0,page:0,rotation:90}]);const read=await api.inspect(out);assert.equal(read.pages[0].rotation,180);
});
test('reload validation supports outputs above the per-input bound',async()=>{
 const d=await lib.PDFDocument.create();const p=d.addPage([200,400]);p.node.set(lib.PDFName.of('Contents'),d.context.register(d.context.stream(new Uint8Array(11*1024*1024).fill(32))));
 const input=await d.save({useObjectStreams:false});const output=await api.transform([input],[{source:0,page:0,rotation:0},{source:0,page:0,rotation:90}]);assert.ok(output.length>api.limits.maxInputBytes);assert.equal((await lib.PDFDocument.load(output)).getPageCount(),2);
});
