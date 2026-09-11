'use strict';
(() => {
  const $=id=>document.getElementById(id);
  let pages=[],busy=false,generation=0,urls=[];
  let history=null,sources=new Map(),serial=0,importedProfile=null,outputEvidence=null;
  function model(){return DocumentEngine.createDocument({format:'pdf',bytes:null,filename:'Prepared.pdf',pageCount:pages.length,structuralValidation:'unknown',pages:pages.map(p=>({id:p.id,width:null,height:null,unit:null,rotation:p.rotation*90}))});}
  function resetHistory(){sources=new Map(pages.map(p=>[p.id,{...p}]));history=pages.length?DocumentEngine.createHistory(model()):null;}
  function syncHistory(){pages=history.present.pages.map(p=>({...sources.get(p.sourceId||p.id),id:p.id,rotation:p.rotation/90}));invalidate();render();}
  function pageAction(action){if(busy||!history)return;try{history=DocumentEngine.applyAction(history,action);syncHistory();}catch(e){message(e.message);}}
  function activeProfile(){const max=Math.round(Number($('limit').value)*1000000);return importedProfile||{version:1,id:'submission-basic',constraints:{formats:['pdf'],bytes:{max:Number.isSafeInteger(max)&&max>=0?max:2000000},pageCount:{min:1,max:20}}};}
  function renderReadiness(){const d=outputEvidence?{...model(),bytes:outputEvidence.bytes,pages:outputEvidence.pages}:model();ReadinessUI.render($('readiness'),DocumentEngine.evaluate(d,activeProfile()));$('rule-name').textContent=activeProfile().id;}
  $('undo').onclick=()=>{if(!busy&&history){history=DocumentEngine.undo(history);syncHistory();}};
  $('redo').onclick=()=>{if(!busy&&history){history=DocumentEngine.redo(history);syncHistory();}};
  $('rule-file').onchange=async e=>{if(busy)return;const file=e.target.files[0];e.target.value='';if(!file)return;busy=true;render();try{if(file.size>DocumentEngine.LIMITS.jsonBytes)throw Error('Profile exceeds 1 MiB');const profile=DocumentEngine.validateProfile(DocumentEngine.parseJSON(await file.text()));importedProfile=profile;invalidate();$('profile-status').textContent='Profile imported locally. Settings are not changed automatically.';}catch(e){$('profile-status').textContent='Profile not imported. '+e.message;}finally{busy=false;render();}};
  $('rule-reset').onclick=()=>{if(busy)return;importedProfile=null;invalidate();render();$('profile-status').textContent='Using current output size and page limits.';};
  $('rule-export').onclick=()=>{if(busy)return;const profile=DocumentEngine.validateProfile(activeProfile());const url=URL.createObjectURL(new Blob([JSON.stringify(profile,null,2)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=profile.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  const message=s=>{$('status').textContent=s;};
  function invalidate(){outputEvidence=null;generation++;for(const u of urls)URL.revokeObjectURL(u);urls=[];$('result').hidden=true;$('download').hidden=true;$('download').removeAttribute('href');$('reviewed').checked=false;$('previews').replaceChildren();renderReadiness();}
  function render(){
    $('undo').disabled=busy||!history||!history.past.length;$('redo').disabled=busy||!history||!history.future.length;
    renderReadiness();$('pages').replaceChildren();
    pages.forEach((p,i)=>{const li=document.createElement('li'),name=document.createElement('span');name.textContent=`${i+1}. ${p.file.name}${p.crop?' · '+p.crop:''} · ${p.rotation*90}°`;li.append(name);
      const split=document.createElement('button');split.type='button';split.textContent='Split spread';split.disabled=busy||!!p.crop||pages.length>=20;split.onclick=()=>{if(busy||p.crop||pages.length>=20)return;invalidate();pages.splice(i,1,{...p,id:'asset-'+(++serial),crop:'left'},{...p,id:'asset-'+(++serial),crop:'right'});resetHistory();render();message('Split source into left and right halves, before rotation. Page undo history reset.');};li.append(split);
      for(const [label,delta] of [['up',-1],['down',1]]){const button=document.createElement('button');button.type='button';button.textContent=label==='up'?'↑':'↓';button.setAttribute('aria-label',`Move page ${i+1} ${label}`);button.disabled=busy||i+delta<0||i+delta>=pages.length;button.onclick=()=>{if(busy||i+delta<0||i+delta>=pages.length)return;const order=pages.map(p=>p.id);[order[i],order[i+delta]]=[order[i+delta],order[i]];pageAction({op:'reorder',pageIds:order});};li.append(button);}
      for(const action of ['Duplicate','Rotate','Remove']){const button=document.createElement('button');button.type='button';button.textContent=action;button.setAttribute('aria-label',`${action} page ${i+1}`);button.disabled=busy||(action==='Duplicate'&&pages.length>=20);button.onclick=()=>{if(busy||(action==='Duplicate'&&pages.length>=20))return;if(action==='Remove'&&pages.length===1){pages=[];resetHistory();invalidate();render();return;}pageAction({op:action==='Remove'?'delete':action.toLowerCase(),pageIds:[p.id],...(action==='Rotate'?{degrees:90}:{})});};li.append(button);}
      $('pages').append(li);
    });
    for(const id of ['rule-file','rule-export','rule-reset'])$(id).disabled=busy;
    $('settings').disabled=busy;$('cancel').hidden=!busy;
    for(const id of ['sort','reverse','rotate','clear'])$(id).disabled=busy||!pages.length;
    $('prepare').disabled=busy||!pages.length;
  }
  $('files').onchange=async e=>{
    if(busy)return;const files=Array.from(e.target.files);e.target.value='';
    if(pages.length+files.length>20){message('Maximum 20 pages. No files were added.');return;}
    busy=true;invalidate();render();const token=generation;
    try{let total=pages.reduce((n,p)=>n+p.file.size,0);const added=[];for(const file of files){if(file.size>20_000_000||(total+=file.size)>100_000_000)throw Error('Limit: 20 MB per image and 100 MB selected input');PrepareCore.dimensions(new Uint8Array(await file.arrayBuffer()));if(token!==generation)throw Error('Cancelled');added.push({id:'asset-'+(++serial),file,rotation:0,crop:null});}pages.push(...added);resetHistory();message(`${pages.length} pages ready.`);}catch(e){message(e.message);}finally{busy=false;render();}
  };
  for(const id of ['limit','profile','paper','margin','dpi','background'])$(id).oninput=()=>{if(!busy){invalidate();$('preset').value='custom';message('Settings changed. Prepare again.');}};
  $('preset').onchange=()=>{if(busy)return;const preset=$('preset').value;if(preset==='custom')return;invalidate();$('limit').value=preset==='portal'?'0.5':preset==='photo'?'10':'2';$('profile').value=preset==='portal'?'small':'balanced';$('paper').value=preset==='application'?'a4':'original';$('margin').value=preset==='application'?'24':'0';$('dpi').value='0';$('background').value='0';renderReadiness();message('Preset applied. Prepare again.');};
  $('rotate').onclick=()=>{if(busy)return;pageAction({op:'rotate',pageIds:pages.map(p=>p.id),degrees:90});message('Rotated all pages. Prepare again.');};
  $('sort').onclick=()=>{if(busy)return;pageAction({op:'reorder',pageIds:[...pages].sort((a,b)=>a.file.name.localeCompare(b.file.name,undefined,{numeric:true})).map(p=>p.id)});};
  $('reverse').onclick=()=>{if(busy)return;pageAction({op:'reorder',pageIds:pages.map(p=>p.id).reverse()});};
  $('clear').onclick=()=>{if(busy||!confirm('Clear all pages? Original files are not changed.'))return;pages=[];resetHistory();invalidate();render();message('Workspace cleared.');};
  $('cancel').onclick=()=>{if(!busy)return;invalidate();message('Cancelling after the current image operation…');};
  const check=token=>{if(token!==generation)throw Error('Cancelled. No PDF retained.');};
  const blobOf=c=>new Promise((resolve,reject)=>c.toBlob(b=>b?resolve(b):reject(Error('Browser JPEG encoding failed')),'image/jpeg',c.quality));
  async function encode(p,settings,edge,quality,token){
    const bitmap=await createImageBitmap(p.file,{imageOrientation:'from-image'});checkOrClose();
    function checkOrClose(){if(token!==generation){bitmap.close();check(token);}}
    let canvas;
    try{
      const half=Math.floor(bitmap.width/2),sx=p.crop==='right'?half:0,sw=p.crop?(p.crop==='left'?half:bitmap.width-half):bitmap.width;
      if(sw<1)throw Error('Image is too narrow to split');
      const sh=bitmap.height,odd=p.rotation%2,w=odd?sh:sw,h=odd?sw:sh;
      const layout=PrepareCore.layout(w,h,{...settings,edge});canvas=document.createElement('canvas');[canvas.width,canvas.height]=layout.pixels;
      const ctx=canvas.getContext('2d',{willReadFrequently:settings.profile==='gray'});if(!ctx)throw Error('Canvas is unavailable');
      ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.save();ctx.translate(canvas.width/2,canvas.height/2);ctx.rotate(p.rotation*Math.PI/2);
      const dw=odd?canvas.height:canvas.width,dh=odd?canvas.width:canvas.height;ctx.drawImage(bitmap,sx,0,sw,sh,-dw/2,-dh/2,dw,dh);ctx.restore();bitmap.close();
      if(settings.background){const data=ctx.getImageData(0,0,canvas.width,canvas.height);PrepareCore.flattenBackground(data.data,settings.background);ctx.putImageData(data,0,0);}
      if(settings.profile==='gray'){const data=ctx.getImageData(0,0,canvas.width,canvas.height);for(let i=0;i<data.data.length;i+=4){const gray=Math.round(.2126*data.data[i]+.7152*data.data[i+1]+.0722*data.data[i+2]);data.data[i]=data.data[i+1]=data.data[i+2]=gray;}ctx.putImageData(data,0,0);}
      canvas.quality=quality;const blob=await blobOf(canvas);check(token);return {jpeg:new Uint8Array(await blob.arrayBuffer()),width:canvas.width,height:canvas.height,layout};
    }finally{bitmap.close();if(canvas){canvas.width=1;canvas.height=1;}}
  }
  $('prepare').onclick=async()=>{
    if(busy||!pages.length)return;invalidate();
    const settings={paper:$('paper').value,margin:Number($('margin').value),dpi:Number($('dpi').value),profile:$('profile').value,background:Number($('background').value)},limit=Number($('limit').value)*1_000_000;
    if(!Number.isFinite(limit)||limit<10_000||limit>50_000_000||!$('margin').checkValidity()){message('Use a size limit from 0.01 to 50 MB and margins from 0 to 72 pt.');return;}
    busy=true;render();const token=generation,attempts=settings.profile==='small'?[[1600,.65],[1200,.55],[960,.45]]:[[2400,.82],[1800,.72],[1200,.62]];
    try{let output,encoded;
      for(let attempt=0;attempt<attempts.length;attempt++){encoded=[];const [edge,quality]=attempts[attempt];for(let i=0;i<pages.length;i++){check(token);message(`Attempt ${attempt+1}/3 · page ${i+1}/${pages.length}`);encoded.push(await encode(pages[i],settings,edge,quality,token));check(token);}output=PrepareCore.pdf(encoded);if(output.length<=limit)break;}
      check(token);if(output.length>limit){message(`Cannot fit: ${output.length.toLocaleString()} bytes exceeds your limit. No download. Use fewer pages or a higher limit.`);return;}
      const url=URL.createObjectURL(new Blob([output],{type:'application/pdf'}));urls.push(url);$('download').href=url;
      for(let i=0;i<encoded.length;i++){const p=encoded[i],figure=document.createElement('figure'),caption=document.createElement('figcaption'),sheet=document.createElement('div'),img=document.createElement('img');caption.textContent=`Page ${i+1} · ${p.width} × ${p.height} pixels`;sheet.className='sheet';const [w,h]=p.layout.page,[x,y,dw,dh]=p.layout.rect;sheet.style.aspectRatio=`${w}/${h}`;img.alt=`Prepared page ${i+1}`;img.style.cssText=`left:${x/w*100}%;top:${y/h*100}%;width:${dw/w*100}%;height:${dh/h*100}%`;img.src=URL.createObjectURL(new Blob([p.jpeg],{type:'image/jpeg'}));urls.push(img.src);sheet.append(img);figure.append(caption,sheet);$('previews').append(figure);}
      outputEvidence={bytes:output.length,pages:encoded.map((p,i)=>({id:'output-'+i,width:p.layout.page[0],height:p.layout.page[1],unit:'pt',rotation:0}))};renderReadiness();
      $('result').hidden=false;message(`Fits the limit. ${output.length.toLocaleString()} bytes · ${pages.length} ${pages.length===1?'page':'pages'}. Review before saving.`);
    }catch(e){invalidate();message(e.message||'Preparation failed');}finally{busy=false;render();}
  };
  $('reviewed').onchange=()=>{$('download').hidden=!$('reviewed').checked;};
  window.addEventListener('pagehide',invalidate);render();
})();
