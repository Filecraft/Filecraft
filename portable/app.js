'use strict';
(() => {
  const $=id=>document.getElementById(id);
  let pages=[],busy=false,generation=0,urls=[];
  const message=s=>{$('status').textContent=s;};
  function invalidate(){generation++;for(const u of urls)URL.revokeObjectURL(u);urls=[];$('result').hidden=true;$('download').hidden=true;$('download').removeAttribute('href');$('reviewed').checked=false;$('previews').replaceChildren();}
  function render(){
    $('pages').replaceChildren();
    pages.forEach((p,i)=>{const li=document.createElement('li'),name=document.createElement('span');name.textContent=`${i+1}. ${p.file.name}${p.crop?' · '+p.crop:''} · ${p.rotation*90}°`;li.append(name);
      const split=document.createElement('button');split.type='button';split.textContent='Split spread';split.disabled=busy||!!p.crop||pages.length>=20;split.onclick=()=>{if(busy||p.crop||pages.length>=20)return;invalidate();pages.splice(i,1,{...p,crop:'left'},{...p,crop:'right'});render();message('Split source into left and right halves, before rotation.');};li.append(split);
      for(const [label,delta] of [['up',-1],['down',1]]){const button=document.createElement('button');button.type='button';button.textContent=label==='up'?'↑':'↓';button.setAttribute('aria-label',`Move page ${i+1} ${label}`);button.disabled=busy||i+delta<0||i+delta>=pages.length;button.onclick=()=>{if(busy||i+delta<0||i+delta>=pages.length)return;invalidate();[pages[i],pages[i+delta]]=[pages[i+delta],pages[i]];render();};li.append(button);}
      for(const action of ['Duplicate','Rotate','Remove']){const button=document.createElement('button');button.type='button';button.textContent=action;button.setAttribute('aria-label',`${action} page ${i+1}`);button.disabled=busy||(action==='Duplicate'&&pages.length>=20);button.onclick=()=>{if(busy||(action==='Duplicate'&&pages.length>=20))return;invalidate();if(action==='Duplicate')pages.splice(i+1,0,{...p});else if(action==='Rotate')p.rotation=(p.rotation+1)%4;else pages.splice(i,1);render();};li.append(button);}
      $('pages').append(li);
    });
    $('settings').disabled=busy;$('cancel').hidden=!busy;
    for(const id of ['sort','reverse','rotate','clear'])$(id).disabled=busy||!pages.length;
    $('prepare').disabled=busy||!pages.length;
  }
  $('files').onchange=async e=>{
    if(busy)return;const files=Array.from(e.target.files);e.target.value='';
    if(pages.length+files.length>20){message('Maximum 20 pages. No files were added.');return;}
    busy=true;invalidate();render();const token=generation;
    try{let total=pages.reduce((n,p)=>n+p.file.size,0);const added=[];for(const file of files){if(file.size>20_000_000||(total+=file.size)>100_000_000)throw Error('Limit: 20 MB per image and 100 MB selected input');PrepareCore.dimensions(new Uint8Array(await file.arrayBuffer()));if(token!==generation)throw Error('Cancelled');added.push({file,rotation:0,crop:null});}pages.push(...added);message(`${pages.length} pages ready.`);}catch(e){message(e.message);}finally{busy=false;render();}
  };
  for(const id of ['limit','profile','paper','margin','dpi','background'])$(id).oninput=()=>{if(!busy){invalidate();$('preset').value='custom';message('Settings changed. Prepare again.');}};
  $('preset').onchange=()=>{if(busy)return;const preset=$('preset').value;if(preset==='custom')return;invalidate();$('limit').value=preset==='portal'?'0.5':preset==='photo'?'10':'2';$('profile').value=preset==='portal'?'small':'balanced';$('paper').value=preset==='application'?'a4':'original';$('margin').value=preset==='application'?'24':'0';$('dpi').value='0';$('background').value='0';message('Preset applied. Prepare again.');};
  $('rotate').onclick=()=>{if(busy)return;invalidate();pages=pages.map(p=>({...p,rotation:(p.rotation+1)%4}));render();message('Rotated all pages. Prepare again.');};
  $('sort').onclick=()=>{if(busy)return;invalidate();pages.sort((a,b)=>a.file.name.localeCompare(b.file.name,undefined,{numeric:true}));render();};
  $('reverse').onclick=()=>{if(busy)return;invalidate();pages.reverse();render();};
  $('clear').onclick=()=>{if(busy||!confirm('Clear all pages? Original files are not changed.'))return;invalidate();pages=[];render();message('Workspace cleared.');};
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
      $('result').hidden=false;message(`Fits the limit. ${output.length.toLocaleString()} bytes · ${pages.length} pages. Review before saving.`);
    }catch(e){invalidate();message(e.message||'Preparation failed');}finally{busy=false;render();}
  };
  $('reviewed').onchange=()=>{$('download').hidden=!$('reviewed').checked;};
  window.addEventListener('pagehide',invalidate);render();
})();
