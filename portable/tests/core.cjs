const assert = require('node:assert/strict');
const p = require('../core.js');
assert.deepEqual(p.layout(1200,1600,{paper:'a4',margin:24}).page,[595.28,841.89]);
assert.throws(()=>p.layout(20,30,{paper:'original',margin:400}));
assert.throws(()=>p.layout(0,20,{}));
const a=p.layout(1200,1600,{paper:'a4',margin:24,dpi:150});
assert.ok(a.pixels[0]<=Math.ceil(a.rect[2]*150/72));
assert.ok(a.pixels[1]<=1600);
console.log('PASS geometry, invalid sizes, DPI ceiling, no upscaling');
