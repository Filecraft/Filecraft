'use strict';
(() => {
  const $ = id => document.getElementById(id), E = DocumentEngine;
  let files = [], sources = new Map(), history = null, serial = 0;
  let busy = false, pending = null, outputURL = null, evidence = null, custom = null, receiptURL = null;
  const hash = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  const status = text => { $('status').textContent = text; };
  const rows = () => history ? history.present.pages : [];
  function requirement() {
    return custom || E.validateProfile({version:1,id:'my-pdf-requirements',constraints:{formats:['pdf'],bytes:{max:Math.round(Number($('limit').value)*1000000)},pageCount:{min:1,max:Number($('max-pages').value)}}});
  }
  function documentModel(pages, bytes=null) {
    return E.createDocument({filename:'Prepared.pdf',format:'pdf',bytes,pageCount:pages.length,pages,structuralValidation:'unknown'});
  }
  function invalidate() {
    if (receiptURL) URL.revokeObjectURL(receiptURL);
    receiptURL=null; $('receipt-download').hidden=true; $('receipt-download').removeAttribute('href');
    if (outputURL) URL.revokeObjectURL(outputURL);
    outputURL = null; evidence = null; $('result').hidden = true; $('download').hidden = true;
    $('download').removeAttribute('href'); $('reviewed').checked = false; $('save-hint').hidden = false;
  }
  function checks() {
    try { ReadinessUI.render($('checks'), E.evaluate(evidence || documentModel(rows()), requirement())); }
    catch(e) { $('checks').textContent = 'Check output requirements: ' + e.message; }
  }
  function run(op, data) {
    return new Promise((resolve,reject) => {
      const url = typeof PREPARE_STATIC_WORKER !== 'undefined' ? PREPARE_STATIC_WORKER : URL.createObjectURL(new Blob([PREPARE_WORKER_SOURCE],{type:'text/javascript'}));
      let worker;
      try { worker = new Worker(url); } catch(e) { URL.revokeObjectURL(url); reject(e); return; }
      let finished = false;
      const end = (error,value) => {
        if (finished) return; finished = true; clearTimeout(timer); worker.terminate(); URL.revokeObjectURL(url);
        pending = null; error ? reject(error) : resolve(value);
      };
      const timer = setTimeout(() => end(Error('Operation exceeded 30 seconds. Use a smaller document.')),30000);
      pending = () => end(Error('Cancelled. Original files and prior page order are unchanged.'));
      worker.onmessage = event => event.data.error ? end(Error(event.data.error)) : end(null,event.data.value);
      worker.onerror = () => end(Error('PDF worker failed. The document may be unsupported or too complex.'));
      worker.postMessage({op,...data});
    });
  }
  function edit(action) {
    if(busy || !history) return;
    try { history = E.applyAction(history,action); invalidate(); render(); status('Page order changed. Create a new PDF copy.'); }
    catch(e) { status(e.message); }
  }
  function render(focusLabel) {
    $('pages').replaceChildren();
    rows().forEach((page,index) => {
      const source = sources.get(page.sourceId || page.id), li = document.createElement('li');
      const text = document.createElement('span'); text.className='page-label';
      text.textContent = `${index+1}. ${files[source.source].name} · source page ${source.page+1} · ${page.width} × ${page.height} pt · ${page.rotation}°`;
      li.append(text); const controls = document.createElement('div'); controls.className='page-controls';
      for(const name of ['Up','Down','Duplicate','Rotate','Remove']) {
        const button = document.createElement('button'); button.type='button'; button.textContent=name;
        const label=`${name} page ${index+1}`; button.setAttribute('aria-label',label);
        button.disabled = busy || (name==='Up'&&index===0) || (name==='Down'&&index===rows().length-1) || (name==='Duplicate'&&rows().length>=100) || (name==='Remove'&&rows().length===1);
        button.onclick=()=>{
          if(name==='Up'||name==='Down') { const ids=rows().map(p=>p.id),other=index+(name==='Up'?-1:1);[ids[index],ids[other]]=[ids[other],ids[index]];edit({op:'reorder',pageIds:ids}); }
          else edit({op:name==='Remove'?'delete':name.toLowerCase(),pageIds:[page.id],...(name==='Rotate'?{degrees:90}:{})});
          const target=[...$('pages').querySelectorAll('button')].find(b=>b.getAttribute('aria-label')===label&&!b.disabled);if(target)target.focus();
        }; controls.append(button);
      }
      li.append(controls); $('pages').append(li);
    });
    for(const id of ['files','limit','max-pages','profile-file','profile-export','profile-reset']) $(id).disabled=busy;
    for(const id of ['prepare','reverse','clear']) $(id).disabled=busy||!rows().length;
    $('undo').disabled=busy||!history||!history.past.length; $('redo').disabled=busy||!history||!history.future.length;
    $('cancel').hidden=!busy; $('empty').hidden=!!rows().length; checks();
  }
  function samplePDF() {
    const content='BT /F1 18 Tf 30 330 Td (PREPARE - synthetic sample) Tj ET\n';
    const objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>','<< /Length '+content.length+' >>\nstream\n'+content+'endstream','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'];
    let text='%PDF-1.4\n',offsets=[0];objects.forEach((object,i)=>{offsets.push(text.length);text+=(i+1)+' 0 obj\n'+object+'\nendobj\n';});
    const start=text.length;text+='xref\n0 6\n0000000000 65535 f \n'+offsets.slice(1).map(n=>String(n).padStart(10,'0')+' 00000 n \n').join('')+'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+start+'\n%%EOF\n';
    return new File([text],'Prepare-synthetic-sample.pdf',{type:'application/pdf'});
  }
  $('sample').addEventListener('click',()=>add([samplePDF()]));
  async function add(incoming) {
    if(busy||!incoming.length)return;
    if(files.length+incoming.length>10){status('Maximum 10 source files. Nothing added.');return;}
    let total=files.reduce((n,f)=>n+f.bytes.length,0);
    for(const f of incoming) if(!f.size||f.size>20000000||(total+=f.size)>50000000){status('Files not added: 20 MB per file, 50 MB total.');return;}
    busy=true;invalidate();render();status('Reading PDFs locally…');
    const added=[]; let cancelled=false; const cancelRead=()=>{cancelled=true; if(pending)pending();};
    $('cancel').onclick=cancelRead;
    try {
      for(const file of incoming){const bytes=new Uint8Array(await file.arrayBuffer());if(cancelled)throw Error('Cancelled');const info=await run('inspect',{bytes});if(cancelled)throw Error('Cancelled');added.push({name:file.name,bytes,info});}
      if(rows().length+added.reduce((n,f)=>n+f.info.pageCount,0)>100)throw Error('Maximum 100 output pages.');
      if([...files,...added].reduce((n,f)=>n+f.info.pageCount,0)>100)throw Error('Maximum 100 source pages, including removed pages. Clear the workspace to release old sources.');
      const next=rows().map(p=>({...p}));
      // Flatten source lineage when resetting history so duplicated sources stay resolvable.
      const registry=new Map(next.map(p=>[p.id,sources.get(p.sourceId||p.id)]));
      for(const p of next)delete p.sourceId;
      const nextFiles=files.slice();
      for(const file of added){const index=nextFiles.length;nextFiles.push(file);file.info.pages.forEach((p,i)=>{const id='pdf-'+(++serial);registry.set(id,{source:index,page:i,rotation:p.rotation||0});next.push({id,width:p.width,height:p.height,unit:'pt',rotation:p.rotation||0});});}
      const nextHistory=E.createHistory(documentModel(next));
      files=nextFiles;sources=registry;history=nextHistory;status(`${next.length} pages imported. Import resets undo history.`);
    } catch(e) { status('Files not added: '+e.message); }
    finally { busy=false;render(); }
  }
  $('files').onchange=e=>{const incoming=Array.from(e.target.files);e.target.value='';add(incoming);};
  document.addEventListener('dragover',e=>{e.preventDefault();document.body.classList.add('dragging');});
  document.addEventListener('dragleave',e=>{if(!e.relatedTarget)document.body.classList.remove('dragging');});
  document.addEventListener('drop',e=>{e.preventDefault();document.body.classList.remove('dragging');add(Array.from(e.dataTransfer.files));});
  $('undo').onclick=()=>{if(!busy&&history){history=E.undo(history);invalidate();render();}};
  $('redo').onclick=()=>{if(!busy&&history){history=E.redo(history);invalidate();render();}};
  $('reverse').onclick=()=>edit({op:'reorder',pageIds:rows().map(p=>p.id).reverse()});
  $('clear').onclick=()=>{if(!busy&&confirm('Clear this workspace? Originals are not changed.')){history=null;sources.clear();files=[];invalidate();render();status('Workspace cleared.');}};
  for(const id of ['limit','max-pages'])$(id).oninput=()=>{if(!busy){invalidate();checks();}};
  $('prepare').onclick=async()=>{
    if(busy||!history)return;invalidate();let profile;
    try{if(!$('limit').checkValidity()||!$('max-pages').checkValidity())throw Error('Use valid size and page limits.');profile=requirement();}catch(e){status(e.message);return;}
    if(rows().length>Number($('max-pages').value)){status('Page count exceeds the maximum pages setting. Remove pages or raise that limit.');return;}
    const initial=E.evaluate(documentModel(rows()),profile);
    if(initial.checks.some(c=>c.state==='fail'&&['PAGE_COUNT','FORMAT','FILENAME'].includes(c.code))){status('Requirements fail. Adjust pages or requirements before exporting.');checks();return;}
    busy=true;render();status('Copying pages and checking output…');$('cancel').onclick=()=>{if(pending)pending();};
    try{
      const plan=rows().map(p=>{const src=sources.get(p.sourceId||p.id);return {source:src.source,page:src.page,rotation:(p.rotation-src.rotation+360)%360};});
      const maxBytes=Math.min(Math.round(Number($('limit').value)*1000000),profile.constraints.bytes?.max??50000000);
      const result=await run('transform',{inputs:files.map(f=>f.bytes),plan,options:{maxBytes}});
      const bytes=new Uint8Array(result.bytes);const info=result.info;
      evidence=documentModel(info.pages.map((p,i)=>({id:'result-'+i,width:p.width,height:p.height,unit:'pt',rotation:p.rotation||0})),bytes.length);
      checks();const evaluated=E.evaluate(evidence,profile);
      if(evaluated.status==='NOT_READY'){status('Output does not satisfy your profile. No download retained.');return;}
      const receipt={schema:'prepare-receipt',version:1,engineVersion:'0.10.0-beta.1',inputs:await Promise.all(files.map(async f=>({sha256:await hash(f.bytes),bytes:f.bytes.length}))),output:{sha256:await hash(bytes),bytes:bytes.length,pageCount:info.pageCount,format:'pdf'},profile,readiness:{status:evaluated.status,checks:evaluated.checks.map(c=>({code:c.code,state:c.state}))},visualReviewVerified:false,authenticityVerified:false};
      receiptURL=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)+'\n'],{type:'application/json'}));$('receipt-download').href=receiptURL;
      outputURL=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));$('download').href=outputURL;$('result').hidden=false;
      status(`Output parsed · ${bytes.length.toLocaleString()} bytes · ${info.pageCount} pages. Review in a PDF reader before submission.`);
    }catch(e){invalidate();status(e.message);}finally{busy=false;render();}
  };
  $('reviewed').onchange=()=>{$('receipt-download').hidden=!$('reviewed').checked||!receiptURL;$('download').hidden=!$('reviewed').checked||!outputURL;$('save-hint').hidden=$('reviewed').checked&&!!outputURL;};
  $('profile-file').onchange=async e=>{if(busy)return;const file=e.target.files[0];e.target.value='';if(!file)return;busy=true;render();try{if(file.size>E.LIMITS.jsonBytes)throw Error('Profile exceeds 1 MiB');const p=E.validateProfile(E.parseJSON(await file.text()));custom=p;invalidate();$('profile-status').textContent='Imported '+p.id+'. Size ceiling still applies.';}catch(e){$('profile-status').textContent='Not imported: '+e.message;}finally{busy=false;render();}};
  $('profile-reset').onclick=()=>{if(!busy){custom=null;invalidate();render();$('profile-status').textContent='Using current limits.';}};
  $('profile-export').onclick=()=>{try{const p=requirement(),url=URL.createObjectURL(new Blob([JSON.stringify(p,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=p.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){status(e.message);}};
  let verifyGeneration=0;
  async function verifySelected(){
    const generation=++verifyGeneration,r=$('verify-receipt').files[0],f=$('verify-file').files[0];
    $('verify-status').textContent='Choose a receipt and the saved copy. Byte identity only; receipts are editable and unsigned.';
    if(!r||!f)return;
    try{
      if(r.size>65536||!f.size||f.size>100000000)throw Error('Use a receipt up to 64 KiB and a file up to 100 MB.');
      const receipt=E.parseJSON(await r.text()),o=receipt.output;
      if(receipt.schema!=='prepare-receipt'||receipt.version!==1||!o||!/^[0-9a-f]{64}$/.test(o.sha256)||!Number.isSafeInteger(o.bytes)||o.bytes<1||o.bytes>100000000)throw Error('Invalid receipt fingerprint.');
      const same=f.size===o.bytes&&await hash(await f.arrayBuffer())===o.sha256;
      if(generation===verifyGeneration)$('verify-status').textContent=same?'Bytes match the receipt. This is not proof of authenticity, safety or portal acceptance.':'Bytes DO NOT match. This is a different or changed copy.';
    }catch(e){if(generation===verifyGeneration)$('verify-status').textContent=e.message;}
  }
  $('verify-receipt').onchange=verifySelected;$('verify-file').onchange=verifySelected;
  window.addEventListener('pagehide',()=>{if(pending)pending();invalidate();});render();
})();
