const assert=require('node:assert/strict'),p=require('../core.js');
const png=new Uint8Array(33);png.set([137,80,78,71,13,10,26,10]);png.set([0,0,0,13,73,72,68,82],8);const v=new DataView(png.buffer);v.setUint32(16,1200);v.setUint32(20,1600);
assert.deepEqual(p.dimensions(png),{width:1200,height:1600,type:'png'});
v.setUint32(16,100000);assert.throws(()=>p.dimensions(png),/megapixel/);
assert.throws(()=>p.dimensions(new TextEncoder().encode('<svg/>')),/JPEG or PNG/);
assert.throws(()=>p.dimensions(new Uint8Array([255,216,255])),/Invalid/);
console.log('PASS header validation, predecode dimension limit and unsupported input');
