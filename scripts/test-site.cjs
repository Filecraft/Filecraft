// Dependency-free behavioral tests for the website's illustrative preset demo.
const assert = require('node:assert/strict');
const { presetFor } = require('../docs/site.js');
assert.deepEqual(presetFor('portal'), {name:'Portal', limit:'500 KB', paper:'Original', margin:'0 pt', profile:'Small File', note:'A tighter starting point for upload portals.'});
assert.equal(presetFor('application').paper, 'A4');
assert.equal(presetFor('application').limit, '2 MB');
assert.equal(presetFor('photo').profile, 'Balanced');
assert.equal(presetFor('unknown'), null);
assert.equal(presetFor('__proto__'), null);
const changed = presetFor('portal'); changed.limit = 'broken';
assert.equal(presetFor('portal').limit, '500 KB');
console.log('PASS: demo presets, invalid input and isolated state');
