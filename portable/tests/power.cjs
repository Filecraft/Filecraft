const assert=require('node:assert/strict');const p=require('../core.js');
assert.deepEqual(p.layout(2400,3200,{paper:'a4',dpi:175}).pixels,[1446,1929]);
assert.throws(()=>p.layout(10,10,{dpi:601}));assert.throws(()=>p.layout(10,10,{dpi:NaN}));
const a=new Uint8ClampedArray([240,235,230,255,20,40,60,255]);p.flattenBackground(a,225);assert.deepEqual([...a],[255,255,255,255,20,40,60,255]);
assert.throws(()=>p.flattenBackground(a,256));
console.log('PASS custom DPI and deterministic near-white flattening');
