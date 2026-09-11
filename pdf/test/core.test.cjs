'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const lib = require('../vendor/pdf-lib.min.js');
let api; try { api = require('../document.js'); } catch (e) { if (e.code !== 'MODULE_NOT_FOUND') throw e; }
async function fixture(sizes = [[240,360],[510,220]]) {
  const doc = await lib.PDFDocument.create();
  for (const [i,size] of sizes.entries()) {
    const page = doc.addPage(size);
    page.drawText(`PAGE ${i+1}`, {x:17,y:31,size:16});
    page.drawRectangle({x:15,y:62,width:47,height:91,color:lib.rgb(0.8,0.1,0.3)});
  }
  return doc.save();
}
test('inspect reads actual asymmetric page geometry', async () => {
  assert.equal(typeof api?.inspect, 'function');
  const bytes = await fixture();
  const result = await api.inspect(bytes);
  assert.equal(result.pageCount, 2);
  assert.equal(result.byteLength, bytes.length);
  assert.deepEqual(result.pages, [{width:240,height:360,rotation:0},{width:510,height:220,rotation:0}]);
});
test('transform merges ordered duplicate pages and adds rotation without mutating sources', async () => {
  assert.equal(typeof api?.transform, 'function');
  const a = await fixture(), b = await fixture([[333,777]]);
  const bd = await lib.PDFDocument.load(b); bd.getPage(0).setRotation(lib.degrees(270));
  const rotated = await bd.save(); const original = a.slice();
  const out = await api.transform([a,rotated], [{source:1,page:0,rotation:180},{source:0,page:1,rotation:90},{source:0,page:1,rotation:-90}], {maxBytes:100000});
  assert.ok(out instanceof Uint8Array); assert.deepEqual(a, original);
  const doc = await lib.PDFDocument.load(out); // independently examine output via vendor, not API
  assert.equal(doc.getPageCount(),3);
  assert.deepEqual(doc.getPages().map(p => [p.getWidth(),p.getHeight(),p.getRotation().angle]), [[333,777,90],[510,220,90],[510,220,270]]);
  assert.notEqual(doc.getPage(1).ref.toString(),doc.getPage(2).ref.toString());
  assert.ok(doc.getPage(0).node.Contents());
});
test('rejects malformed, truncated, encrypted, form and active PDFs with typed errors', async () => {
  const good = await fixture();
  for (const bytes of [new Uint8Array(), new TextEncoder().encode('not pdf'),good.slice(0,-10)]) {
    await assert.rejects(api.inspect(bytes), e => e.code === 'INVALID_PDF');
  }
  for (const kind of ['encrypt','form','signature','action','annotations','embedded']) {
    const doc = await lib.PDFDocument.load(good);
    if(kind==='encrypt') doc.context.trailerInfo.Encrypt = doc.context.register(doc.context.obj({Filter:'Standard',V:1,R:2,O:lib.PDFString.of('x'),U:lib.PDFString.of('x'),P:-4}));
    if(kind==='form') doc.getForm().createTextField('secret').addToPage(doc.getPage(0));
    if(kind==='signature') doc.catalog.set(lib.PDFName.of('Perms'),doc.context.obj({DocMDP:doc.context.obj({Type:'Sig',ByteRange:[0,1,2,3]})}));
    if(kind==='action') doc.catalog.set(lib.PDFName.of('OpenAction'),doc.context.obj({S:'JavaScript',JS:lib.PDFString.of('app.alert(1)')}));
    if(kind==='annotations') doc.getPage(0).node.set(lib.PDFName.of('Annots'),doc.context.obj([{Subtype:'Link'}]));
    if(kind==='embedded') await doc.attach(new Uint8Array([1,2,3]),'hidden.bin');
    const bytes = await doc.save();
    await assert.rejects(api.inspect(bytes), e => ['ENCRYPTED','UNSUPPORTED_FEATURE'].includes(e.code),kind);
    await assert.rejects(api.transform([bytes],[{source:0,page:0,rotation:0}]), undefined,kind);
  }
});
test('enforces byte, source, page, geometry and plan bounds', async () => {
  const good = await fixture(); const entry = {source:0,page:0,rotation:0};
  for(const plan of [[],null,[{...entry,page:-1}],[{...entry,source:1}],[{...entry,page:2}],[{...entry,rotation:45}],[{...entry,rotation:NaN}],[{...entry,page:'0'}],Array(101).fill(entry),[{...entry,extra:true}]]) {
    await assert.rejects(api.transform([good],plan), e => e.code === 'INVALID_PLAN');
  }
  for(const inputs of [[],Array(11).fill(good),[new Uint8Array(20971521)],Array(3).fill(new Uint8Array(18000000))]) {
    await assert.rejects(api.transform(inputs,[entry]), e => e.code === 'LIMIT');
  }
  await assert.rejects(api.inspect(new Uint8Array(20971521)),e => e.code==='LIMIT');
  const large = await fixture(Array.from({length:101},()=>[20,30]));
  await assert.rejects(api.inspect(large),e => e.code==='LIMIT');
  for(const maxBytes of [0,-1,1.5,'100',NaN,Infinity]) await assert.rejects(api.transform([good],[entry],{maxBytes}),e=>e.code==='LIMIT');
  await assert.rejects(api.transform([good],[entry],{maxBytes:50}), e => e.code==='OUTPUT_LIMIT');
  const invalid = await lib.PDFDocument.load(good); invalid.getPage(0).node.set(lib.PDFName.of('MediaBox'),invalid.context.obj([0,0,0,0]));
  await assert.rejects(api.inspect(await invalid.save()),e=>e.code==='INVALID_PDF');
});
test('rejects indirect active action names and external file streams',async()=>{
 for(const feature of ['indirect-action','external-stream']){
  const doc=await lib.PDFDocument.load(await fixture());
  if(feature==='indirect-action')doc.context.register(doc.context.obj({S:doc.context.register(lib.PDFName.of('Launch'))}));
  else doc.getPage(0).node.set(lib.PDFName.of('Contents'),doc.context.register(doc.context.stream(new Uint8Array(),{F:lib.PDFString.of('outside.dat')})));
  await assert.rejects(api.inspect(await doc.save()),e=>e.code==='UNSUPPORTED_FEATURE');
 }
});
module.exports = {fixture};
