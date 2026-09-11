'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const L=require('../vendor/pdf-lib.min.js');const P=require('../document.js');
test('physical geometry uses visible crop intersection and UserUnit',async()=>{
 const d=await L.PDFDocument.create();const a=d.addPage([100,200]);a.node.set(L.PDFName.of('UserUnit'),L.PDFNumber.of(2));const b=d.addPage([300,400]);b.setCropBox(0,0,300,100);const c=d.addPage([300,400]);c.setCropBox(-20,-30,120,130);
 const bytes=await d.save();const info=await P.inspect(bytes);assert.deepEqual(info.pages,[{width:200,height:400,rotation:0},{width:300,height:100,rotation:0},{width:100,height:100,rotation:0}]);
 const result=await P.transformVerified([bytes],[{source:0,page:0,rotation:90},{source:0,page:1,rotation:0}]);assert.deepEqual(result.info.pages,[{width:200,height:400,rotation:90},{width:300,height:100,rotation:0}]);
});
test('invalid UserUnit and empty visible crop are rejected',async()=>{for(const value of [0,-1,75001]){const d=await L.PDFDocument.create();d.addPage([100,200]).node.set(L.PDFName.of('UserUnit'),L.PDFNumber.of(value));await assert.rejects(P.inspect(await d.save()),{code:'INVALID_PDF'});}const d=await L.PDFDocument.create();d.addPage([100,200]).setCropBox(300,300,10,10);await assert.rejects(P.inspect(await d.save()),{code:'INVALID_PDF'});});
