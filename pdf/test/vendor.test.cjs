'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const {createHash}=require('node:crypto');
test('vendored dependency and all retained license hashes match provenance',()=>{
 const dir=path.resolve(__dirname,'../vendor');const manifest=JSON.parse(fs.readFileSync(path.join(dir,'PROVENANCE.json')));
 assert.equal(manifest.packages[0].version,'1.17.1');
 for(const pkg of manifest.packages)for(const [file,digest]of Object.entries(pkg.files))assert.equal(createHash('sha256').update(fs.readFileSync(path.join(dir,file))).digest('hex'),digest,file);
});
