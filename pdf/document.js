/* Filecraft PDF — original project code under Apache-2.0; upstream parts retain their notices. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./vendor/pdf-lib.min.js'));
  else root.PreparePDF = factory(root.PDFLib);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (PDFLib) {
  'use strict';
  const limits = Object.freeze({maxInputs:10,maxInputBytes:20971520,maxTotalBytes:52428800,maxPages:100,maxOutputBytes:52428800});
  // Install guards before any untrusted parse. The pinned UMD does not export
  // DecodeStream, so discover its actual shared prototype via a tiny local Flate
  // stream. No decoding/allocation of untrusted bytes is involved in discovery.
  const guardKey=Symbol.for('PreparePDF.parserGuards.v1');
  if (!PDFLib[guardKey]) {
    const context=PDFLib.PDFContext.create();
    const probe=PDFLib.decodePDFRawStream(context.stream(new Uint8Array([120,156,3,0,0,0,0,1]),{Filter:'FlateDecode'}));
    let prototype=Object.getPrototypeOf(probe);
    while(prototype&&!Object.hasOwn(prototype,'ensureBuffer'))prototype=Object.getPrototypeOf(prototype);
    if(!prototype)throw new Error('Pinned DecodeStream guard target unavailable.');
    const ensureBuffer=prototype.ensureBuffer;
    const state={active:false,total:0,queue:Promise.resolve()};
    prototype.ensureBuffer=function(requested){
      if(!Number.isSafeInteger(requested)||requested<0||requested>33554432)fail('LIMIT','Decoded stream exceeds 32 MiB.');
      const old=this.buffer.byteLength;
      if(requested>old){
        let capacity=this.minBufferLength;
        if(!Number.isSafeInteger(capacity)||capacity<1||capacity>33554432)fail('LIMIT','Invalid decoder buffer capacity.');
        while(capacity<requested)capacity*=2;
        if(capacity>33554432)fail('LIMIT','Decoded stream exceeds 32 MiB.');
        if(state.active){if(state.total+capacity-old>67108864)fail('LIMIT','Job exceeds 64 MiB cumulative decoded buffers.');state.total+=capacity-old;}
      }
      return ensureBuffer.call(this,requested);
    };
    const factory=PDFLib.PDFXRefStreamParser.forStream;
    PDFLib.PDFXRefStreamParser.forStream=function(stream){
      const dict=stream.dict;
      const number=value=>value instanceof PDFLib.PDFNumber?value.asNumber():NaN;
      const widths=dict.lookup(PDFLib.PDFName.of('W'));
      if(!(widths instanceof PDFLib.PDFArray)||widths.size()!==3)fail('INVALID_PDF','XRef W must contain exactly three widths.');
      const values=widths.asArray().map(v=>number(dict.context.lookup(v)));
      if(values.some(v=>!Number.isSafeInteger(v)||v<0||v>4)||!values.some(v=>v>0))fail('INVALID_PDF','Unsupported XRef widths (0–4 bytes each).');
      const size=number(dict.lookup(PDFLib.PDFName.of('Size')));
      if(!Number.isSafeInteger(size)||size<1||size>100000)fail('LIMIT','XRef object count exceeds limit.');
      const index=dict.lookup(PDFLib.PDFName.of('Index'));let count=0;
      if(index!==undefined){
        if(!(index instanceof PDFLib.PDFArray)||index.size()%2||index.size()>200000)fail('INVALID_PDF','Invalid XRef Index.');
        for(let i=0;i<index.size();i+=2){const first=number(index.lookup(i)),length=number(index.lookup(i+1));if(!Number.isSafeInteger(first)||!Number.isSafeInteger(length)||first<0||length<0||first+length>size)fail('LIMIT','XRef Index exceeds object bounds.');count+=length;if(count>100000)fail('LIMIT','XRef entry count exceeds limit.');}
      }
      return factory.call(this,stream);
    };
    PDFLib[guardKey]=state;
  }
  function job(operation){
    const state=PDFLib[guardKey];
    const run=state.queue.then(async()=>{state.active=true;state.total=0;try{return await operation();}finally{state.active=false;state.total=0;}});
    state.queue=run.catch(()=>{});return run;
  }
  const normalize = n => ((n % 360) + 360) % 360;
  function geometry(doc) {
    const pages = doc.getPages();
    if (!pages.length || pages.length > limits.maxPages) fail('LIMIT','Page count must be 1–100.');
    return pages.map(page => {
      // PDF visible dimensions are CropBox intersected with MediaBox, in
      // physical points. UserUnit is a page entry, not an inheritable key.
      const media=page.getMediaBox(),crop=page.getCropBox();
      const unitObject=page.node.lookup(PDFLib.PDFName.of('UserUnit'));
      const unit=unitObject===undefined?1:unitObject instanceof PDFLib.PDFNumber?unitObject.asNumber():NaN;
      if(!Number.isFinite(unit)||unit<=0||unit>75000||[media,crop].some(b=>!Object.values(b).every(Number.isFinite)||b.width<=0||b.height<=0))fail('INVALID_PDF','Invalid page boxes or UserUnit.');
      const width=(Math.min(media.x+media.width,crop.x+crop.width)-Math.max(media.x,crop.x))*unit;
      const height=(Math.min(media.y+media.height,crop.y+crop.height)-Math.max(media.y,crop.y))*unit;
      const angle=page.getRotation().angle;
      if (!Number.isFinite(width) || !Number.isFinite(height) || width<=0 || height<=0 || !Number.isSafeInteger(angle) || angle%90) fail('INVALID_PDF','Invalid page geometry or rotation.');
      return {width,height,rotation:normalize(angle)};
    });
  }
  function boxes(page) {
    return ['getMediaBox','getCropBox','getTrimBox','getBleedBox','getArtBox'].map(method => page[method]());
  }
  function fail(code, message) { const error = new Error(message); error.code = code; throw error; }
  function ascii(bytes) { return Array.from(bytes, b => String.fromCharCode(b)).join(''); }
  function rejectFeatures(doc) {
    const forbidden = new Set(['AcroForm','XFA','Perms','ByteRange','OpenAction','AA','JS','JavaScript','EmbeddedFiles','AF','Annots','RichMedia','Collection']);
    const actions = new Set(['JavaScript','Launch','GoToR','GoToE','SubmitForm','ImportData','Rendition','Movie','Sound','URI','Hide','SetOCGState','ResetForm','Trans']);
    const stack = doc.context.enumerateIndirectObjects().map(pair => pair[1]);
    const seen = new Set();
    while (stack.length) {
      const object = stack.pop();
      if (!object || seen.has(object)) continue;
      seen.add(object);
      if (object instanceof PDFLib.PDFDict) {
        for (const [key,value] of object.entries()) {
          if (key.decodeText() === 'Annots' && doc.context.lookup(value) instanceof PDFLib.PDFArray && doc.context.lookup(value).size() === 0) continue;
          if (forbidden.has(key.decodeText())) fail('UNSUPPORTED_FEATURE', 'Forms, signatures, annotations, attachments or active features are unsupported.');
          const resolved=doc.context.lookup(value);
          if (resolved instanceof PDFLib.PDFName && ((key.decodeText() === 'S' && actions.has(resolved.decodeText())) || (key.decodeText() === 'Type' && ['Sig','EmbeddedFile','Filespec'].includes(resolved.decodeText())))) fail('UNSUPPORTED_FEATURE','Unsupported active or signed PDF feature.');
          stack.push(value);
        }
      } else if (object instanceof PDFLib.PDFArray) stack.push(...object.asArray());
      else if (object instanceof PDFLib.PDFStream) {
        if (object.dict.has(PDFLib.PDFName.of('F'))) fail('UNSUPPORTED_FEATURE','External file streams are unsupported.');
        stack.push(object.dict);
      }
    }
  }
  async function load(bytes, byteLimit = limits.maxInputBytes) {
    try {
      if (bytes instanceof Uint8Array && bytes.byteLength > byteLimit) fail('LIMIT','PDF exceeds byte limit.');
      if (!(bytes instanceof Uint8Array) || bytes.length < 16 || !/^%PDF-1\.[0-7][\r\n]/.test(ascii(bytes.subarray(0,16)))) fail('INVALID_PDF','Expected a PDF 1.0–1.7 header at byte zero.');
      const tail = ascii(bytes.subarray(Math.max(0,bytes.length-1024)));
      const match = /startxref\s+(\d+)\s+%%EOF[\x00\x09\x0a\x0c\x0d\x20]*$/.exec(tail);
      if (!match || Number(match[1]) >= bytes.length || Number(match[1]) < 8) fail('INVALID_PDF','Missing or invalid final cross-reference / EOF marker.');
      const at = ascii(bytes.subarray(Number(match[1]),Number(match[1])+50));
      if (!/^(xref\b|\d+\s+\d+\s+obj\b)/.test(at)) fail('INVALID_PDF','Cross-reference offset does not point to a table or object.');
      const doc = await PDFLib.PDFDocument.load(bytes, {updateMetadata:false,throwOnInvalidObject:true,capNumbers:false});
      if (doc.isEncrypted || doc.context.trailerInfo.Encrypt) fail('ENCRYPTED','Encrypted PDFs are unsupported.');
      rejectFeatures(doc);
      geometry(doc);
      return doc;
    } catch (error) {
      if (error.code) throw error;
      if (error instanceof PDFLib.EncryptedPDFError || /Input document to .* is encrypted/.test(error.message)) fail('ENCRYPTED','Encrypted PDFs are unsupported.');
      fail('INVALID_PDF','PDF structural parsing failed.');
    }
  }
  async function inspect(bytes) {
    const doc = await load(bytes);
    return {pageCount:doc.getPageCount(),pages:geometry(doc),byteLength:bytes.byteLength,warnings:['Structural parsing is not a content or readability guarantee.']};
  }
  async function transform(inputs, plan, options = {}, detailed = false) {
    if (!Array.isArray(inputs) || !inputs.length || inputs.length > limits.maxInputs) fail('LIMIT','Provide 1–10 inputs.');
    let total=0;
    for (const bytes of inputs) {
      if (!(bytes instanceof Uint8Array)) fail('INVALID_PDF','Inputs must be Uint8Array.');
      total += bytes.byteLength;
      if (bytes.byteLength > limits.maxInputBytes || total > limits.maxTotalBytes) fail('LIMIT','Input byte limit exceeded.');
    }
    if (!Array.isArray(plan) || !plan.length || plan.length > limits.maxPages) fail('INVALID_PLAN','Plan must contain 1–100 entries.');
    for(const entry of plan) {
      if (!entry || typeof entry !== 'object' || Object.keys(entry).some(k=>!['source','page','rotation'].includes(k)) || !Number.isSafeInteger(entry.source) || entry.source<0 || entry.source>=inputs.length || !Number.isSafeInteger(entry.page) || entry.page<0 || !Number.isSafeInteger(entry.rotation) || entry.rotation%90) fail('INVALID_PLAN','Invalid source, page or rotation in plan.');
    }
    if (!options || typeof options !== 'object' || Array.isArray(options) || Object.keys(options).some(k=>k!=='maxBytes')) fail('LIMIT','Unknown output options.');
    const maxBytes=options.maxBytes === undefined ? limits.maxOutputBytes : options.maxBytes;
    if (!Number.isSafeInteger(maxBytes) || maxBytes<=0 || maxBytes>limits.maxOutputBytes) fail('LIMIT','maxBytes must be a positive integer up to 50 MiB.');
    const sources=[];
    for(const bytes of inputs) sources.push(await load(bytes));
    if (sources.reduce((n,d)=>n+d.getPageCount(),0)>limits.maxPages) fail('LIMIT','Total source pages exceed 100.');
    for(const entry of plan) if(entry.page>=sources[entry.source].getPageCount()) fail('INVALID_PLAN','Page index exceeds source page count.');
    const output = await PDFLib.PDFDocument.create({updateMetadata:false});
    const expected = [], expectedBoxes = [];
    for (const entry of plan) {
      const source = sources[entry.source];
      const sourcePage=source.getPage(entry.page);
      const targetRotation=normalize(normalize(sourcePage.getRotation().angle)+normalize(entry.rotation));
      expected.push({...geometry(source)[entry.page],rotation:targetRotation});
      expectedBoxes.push(boxes(sourcePage));
      const [page] = await output.copyPages(source, [entry.page]);
      page.setRotation(PDFLib.degrees(targetRotation));
      output.addPage(page);
    }
    const bytes = await output.save({addDefaultPage:false,updateFieldAppearances:false});
    if (bytes.length > maxBytes) fail('OUTPUT_LIMIT','Output exceeds maxBytes; no output returned.');
    const reloaded = await load(bytes, limits.maxOutputBytes);
    if (JSON.stringify(geometry(reloaded)) !== JSON.stringify(expected) || JSON.stringify(reloaded.getPages().map(boxes)) !== JSON.stringify(expectedBoxes)) fail('OUTPUT_VALIDATION','Output geometry validation failed.');
    return detailed ? {bytes,info:{pageCount:reloaded.getPageCount(),pages:geometry(reloaded),byteLength:bytes.byteLength}} : bytes;
  }
  return Object.freeze({inspect:bytes=>job(()=>inspect(bytes)),transform:(inputs,plan,options)=>job(()=>transform(inputs,plan,options)),transformVerified:(inputs,plan,options)=>job(()=>transform(inputs,plan,options,true)),limits,version:'0.7.0-beta.1'});
});
