/* English presentation catalog: engine codes stay locale-independent. */
'use strict';
window.ReadinessUI=Object.freeze({
 labels:{STRUCTURE:'Structure',FORMAT:'Format',BYTES:'Bytes',PAGE_COUNT:'Pages',FILENAME:'Filename',PAGE_DIMENSIONS:'Page dimensions',PAGE_ORIENTATION:'Orientation'},
 advice:{VERIFY_WITH_FORMAT_ADAPTER:'Open the saved copy in a PDF reader; full PDF structural validation is not available here.',CONVERT_FORMAT:'Choose a supported output format.',ADJUST_FILE_SIZE:'Change compression or size settings.',ADJUST_PAGES:'Adjust the page selection.',RENAME_FILE:'Choose a compliant output filename.',RESIZE_OR_VERIFY_PAGE:'Check paper size and dimensions.',ROTATE_OR_VERIFY_PAGE:'Rotate pages or check their orientation.'},
 render(host,result){
  host.replaceChildren();const heading=document.createElement('h3');heading.textContent='Readiness · '+result.status.replaceAll('_',' ')+' · '+result.profileId;host.append(heading);
  const note=document.createElement('p');note.textContent='Checks apply only to the selected rules. Unknown is not a pass. Output dimensions and bytes are measured after preparation; structure remains unverified.';host.append(note);
  const list=document.createElement('ul');for(const check of result.checks){const li=document.createElement('li');const label=this.labels[check.code]||check.code;let value=check.code==='FORMAT'?' · generated '+check.params.actual+' / allowed '+check.params.allowed.join(', '):'';if(check.code==='BYTES'||check.code==='PAGE_COUNT')value=` · ${check.params.actual===null?'not measured':check.params.actual}${check.params.max!==undefined?' / max '+check.params.max:''}`;li.textContent=`${check.state.toUpperCase()} · ${label}${value}`;if(check.state!=='pass'){const small=document.createElement('small');small.textContent=check.remediation.map(x=>this.advice[x]||x).join(' ');li.append(small);}list.append(li);}host.append(list);
 }
});
