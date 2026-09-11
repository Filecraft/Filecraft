/* English presentation catalog: engine codes stay locale-independent. */
'use strict';
window.ReadinessUI=Object.freeze({
 labels:{STRUCTURE:'Structure',FORMAT:'Format',BYTES:'Bytes',PAGE_COUNT:'Pages',FILENAME:'Filename',PAGE_DIMENSIONS:'Page dimensions',PAGE_ORIENTATION:'Orientation'},
 advice:{VERIFY_WITH_FORMAT_ADAPTER:'Open the saved copy in a PDF reader; full PDF structural validation is not available here.',CONVERT_FORMAT:'Choose a supported output format.',ADJUST_FILE_SIZE:'Reduce pages, adjust supported compression settings or change the size requirement.',ADJUST_PAGES:'Adjust the page selection.',RENAME_FILE:'Choose a compliant output filename.',RESIZE_OR_VERIFY_PAGE:'Check paper size and dimensions.',ROTATE_OR_VERIFY_PAGE:'Rotate pages or check their orientation.'},
 describe(check){
  const p=check.params;
  if(check.code==='FORMAT')return ` · actual ${p.actual} / allowed ${p.allowed.join(', ')}`;
  if(check.code==='BYTES'||check.code==='PAGE_COUNT')return ` · actual ${p.actual===null?'not measured':p.actual}${p.min!==undefined?' / min '+p.min:''}${p.max!==undefined?' / max '+p.max:''}`;
  if(check.code==='FILENAME')return ` · actual ${p.actual===null?'unknown':p.actual}${p.maxLength!==undefined?' / max '+p.maxLength+' characters':''}${p.asciiOnly?' / ASCII only':''}${p.extensions?' / extensions '+p.extensions.join(', '):''}`;
  if(check.code==='PAGE_DIMENSIONS'||check.code==='PAGE_ORIENTATION'){
   if(!p.pageId)return ' · incomplete page evidence';
   const measured=p.width===null||p.height===null?'not measured':`${p.width} × ${p.height} ${p.unit||'unknown unit'}`;
   if(check.code==='PAGE_ORIENTATION')return ` · ${p.pageId}: ${measured} / expected ${p.expected}`;
   const d=p.expected,range=(min,max)=>min===undefined?`≤ ${max}`:max===undefined?`≥ ${min}`:`${min}–${max}`;
   return ` · ${p.pageId}: ${measured} / expected ${d.minWidth!==undefined||d.maxWidth!==undefined?'width '+range(d.minWidth,d.maxWidth)+' ':''}${d.minHeight!==undefined||d.maxHeight!==undefined?'height '+range(d.minHeight,d.maxHeight)+' ':''}${d.unit}`;
  }
  return '';
 },
 render(host,result){
  host.replaceChildren();const heading=document.createElement('h3');heading.textContent='Readiness · '+result.status.replaceAll('_',' ')+' · '+result.profileId;host.append(heading);
  const note=document.createElement('p');note.textContent='Checks apply only to the selected rules. Unknown is not a pass. Output dimensions and bytes are measured after preparation; full structure remains unverified.';host.append(note);
  const list=document.createElement('ul');for(const check of result.checks){const li=document.createElement('li');const label=this.labels[check.code]||check.code;li.textContent=`${check.state.toUpperCase()} · ${label}${this.describe(check)}`;if(check.state!=='pass'){const small=document.createElement('small');small.textContent=check.remediation.map(x=>this.advice[x]||x).join(' ');li.append(small);}list.append(li);}host.append(list);
 }
});
