/* Shared local document model. No I/O, pixel decoder, or institutional certification. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DocumentEngine = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const LIMITS = Object.freeze({ jsonBytes:1048576, pages:256, history:32, steps:128, filename:255, dimension:1000000 });
  const formats = ['png','jpeg','pdf','unknown'];
  function error(code, message, params) { const e=new Error(message); e.code=code; e.params=params||{}; return e; }
  function reject(code, condition, message) { if (!condition) throw error(code,message); }
  function object(v, keys, code) {
    reject(code, v!==null && typeof v==='object' && !Array.isArray(v) && (Object.getPrototypeOf(v)===Object.prototype || Object.getPrototypeOf(v)===null), 'Expected plain object');
    reject(code, Object.keys(v).every(k=>keys.includes(k)), 'Unknown property');
  }
  function int(v,min,max) { return Number.isSafeInteger(v)&&v>=min&&v<=max; }
  function text(v,max) { return typeof v==='string'&&v.length>0&&v.length<=max&&!/[\u0000-\u001f\u007f]/.test(v); }
  function freeze(v) { if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.values(v).forEach(freeze);Object.freeze(v);}return v; }
  function parseJSON(s) {
    reject('INPUT_LIMIT',typeof s==='string'&&s.length<=LIMITS.jsonBytes,'JSON input too large');
    const bytes=typeof TextEncoder!=='undefined'?new TextEncoder().encode(s).length:unescape(encodeURIComponent(s)).length;
    reject('INPUT_LIMIT',bytes<=LIMITS.jsonBytes,'JSON input too large');
    try { return JSON.parse(s); } catch (_) { throw error('INVALID_JSON','Malformed JSON'); }
  }
  function validateProfile(p) {
    const c='INVALID_PROFILE'; object(p,['version','id','description','constraints'],c);
    reject(c,p.version===1&&typeof p.id==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$/.test(p.id),'Invalid version or profile id');
    if(p.description!==undefined) reject(c,text(p.description,1000),'Invalid description');
    const v=p.constraints; object(v,['bytes','pageCount','formats','dimensions','orientation','filename'],c);
    for(const key of ['bytes','pageCount']) if(v[key]!==undefined){
      const r=v[key]; object(r,['min','max'],c); reject(c,Object.keys(r).length>0,'Empty range');
      for(const k of Object.keys(r)) reject(c,int(r[k],key==='bytes'?0:1,Number.MAX_SAFE_INTEGER),'Invalid range');
      reject(c,r.min===undefined||r.max===undefined||r.min<=r.max,'Inverted range');
    }
    if(v.formats!==undefined) reject(c,Array.isArray(v.formats)&&v.formats.length>0&&v.formats.length<=3&&new Set(v.formats).size===v.formats.length&&v.formats.every(f=>['png','jpeg','pdf'].includes(f)),'Invalid formats');
    if(v.orientation!==undefined) reject(c,['portrait','landscape','square'].includes(v.orientation),'Invalid orientation');
    if(v.dimensions!==undefined){
      const d=v.dimensions;object(d,['unit','minWidth','maxWidth','minHeight','maxHeight'],c);
      reject(c,['px','pt'].includes(d.unit)&&Object.keys(d).length>1,'Invalid dimensions');
      for(const k of Object.keys(d).filter(k=>k!=='unit')) reject(c,int(d[k],1,LIMITS.dimension),'Invalid dimension range');
      for(const axis of ['Width','Height']) reject(c,d['min'+axis]===undefined||d['max'+axis]===undefined||d['min'+axis]<=d['max'+axis],'Inverted dimensions');
    }
    if(v.filename!==undefined){
      const n=v.filename;object(n,['extensions','maxLength','asciiOnly'],c);reject(c,Object.keys(n).length>0,'Empty filename rule');
      if(n.extensions!==undefined) reject(c,Array.isArray(n.extensions)&&n.extensions.length>0&&n.extensions.length<=16&&new Set(n.extensions).size===n.extensions.length&&n.extensions.every(x=>typeof x==='string'&&/^[a-z0-9]{1,10}$/.test(x)),'Invalid extensions');
      if(n.maxLength!==undefined) reject(c,int(n.maxLength,1,LIMITS.filename),'Invalid filename length');
      if(n.asciiOnly!==undefined) reject(c,typeof n.asciiOnly==='boolean','Invalid ASCII rule');
    }
    function canonical(value){
      if(Array.isArray(value))return value.map(canonical);
      if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
      return value;
    }
    return freeze(canonical(p));
  }
  function createDocument(d) {
    const c='INVALID_DOCUMENT';object(d,['format','bytes','filename','pageCount','structuralValidation','pages'],c);
    reject(c,formats.includes(d.format),'Invalid format');
    reject(c,d.bytes===null||int(d.bytes,0,Number.MAX_SAFE_INTEGER),'Invalid bytes');
    reject(c,d.filename===null||text(d.filename,LIMITS.filename)&&!/[\\/]/.test(d.filename),'Invalid filename');
    reject(c,d.pageCount===null||int(d.pageCount,0,Number.MAX_SAFE_INTEGER),'Invalid page count');
    reject(c,['pass','fail','unknown'].includes(d.structuralValidation),'Invalid structural evidence');
    reject(c,Array.isArray(d.pages)&&d.pages.length<=LIMITS.pages,'Page limit exceeded');
    reject(c,d.pageCount===null||d.pages.length<=d.pageCount,'Page count mismatch');
    const ids=new Set(); const pages=d.pages.map(p=>{
      object(p,['id','sourceId','width','height','unit','rotation'],c);
      reject(c,text(p.id,100)&&!ids.has(p.id),'Invalid or duplicate page id');ids.add(p.id);
      if(p.sourceId!==undefined)reject(c,text(p.sourceId,100),'Invalid source id');
      for(const k of ['width','height']) reject(c,p[k]===null||typeof p[k]==='number'&&Number.isFinite(p[k])&&p[k]>0&&p[k]<=LIMITS.dimension,'Invalid page dimension');
      reject(c,['px','pt',null].includes(p.unit),'Invalid dimension unit');
      reject(c,[0,90,180,270].includes(p.rotation),'Invalid rotation');
      return {...p};
    });
    return freeze({...d,pages});
  }
  function evaluate(document,profile) {
    const d=createDocument(document),p=validateProfile(profile),v=p.constraints,checks=[];
    function check(code,state,params,remediation){checks.push({code,state,params:params||{},remediation:state==='pass'?[]:remediation});}
    function range(value,r){return value===null?'unknown':((r.min===undefined||value>=r.min)&&(r.max===undefined||value<=r.max)?'pass':'fail');}
    check('STRUCTURE',d.structuralValidation,{format:d.format},['VERIFY_WITH_FORMAT_ADAPTER']);
    if(v.formats)check('FORMAT',d.format==='unknown'?'unknown':v.formats.includes(d.format)?'pass':'fail',{actual:d.format,allowed:v.formats},['CONVERT_FORMAT']);
    for(const [key,code,fix] of [['bytes','BYTES','ADJUST_FILE_SIZE'],['pageCount','PAGE_COUNT','ADJUST_PAGES']])if(v[key])check(code,range(d[key],v[key]),{actual:d[key],...v[key]},[fix]);
    if(v.filename){
      const n=v.filename,name=d.filename,ext=name===null?'':name.includes('.')?name.slice(name.lastIndexOf('.')+1).toLowerCase():'';
      const ok=name!==null&&(n.maxLength===undefined||Array.from(name).length<=n.maxLength)&&(!n.asciiOnly||/^[\x20-\x7e]+$/.test(name))&&(!n.extensions||n.extensions.includes(ext));
      check('FILENAME',name===null?'unknown':ok?'pass':'fail',{actual:name,...n},['RENAME_FILE']);
    }
    for(const kind of ['dimensions','orientation']) if(v[kind]) {
      const states=[];
      for(const page of d.pages){
        let w=page.width,h=page.height;if(page.rotation%180!==0)[w,h]=[h,w];
        let state='unknown';
        if(w!==null&&h!==null&&page.unit!==null){
          if(kind==='orientation')state=(w===h?'square':w>h?'landscape':'portrait')===v.orientation?'pass':'fail';
          else if(page.unit===v.dimensions.unit){const r=v.dimensions;state=[range(w,{min:r.minWidth,max:r.maxWidth}),range(h,{min:r.minHeight,max:r.maxHeight})].includes('fail')?'fail':'pass';}
        }
        states.push(state);
        check(kind==='dimensions'?'PAGE_DIMENSIONS':'PAGE_ORIENTATION',state,{pageId:page.id,width:w,height:h,unit:page.unit,expected:v[kind]},[kind==='dimensions'?'RESIZE_OR_VERIFY_PAGE':'ROTATE_OR_VERIFY_PAGE']);
      }
      if(d.pageCount===null||d.pages.length!==d.pageCount||!states.length)check(kind==='dimensions'?'PAGE_DIMENSIONS':'PAGE_ORIENTATION','unknown',{reason:'INCOMPLETE_PAGE_EVIDENCE'},['VERIFY_WITH_FORMAT_ADAPTER']);
    }
    return freeze({version:1,profileId:p.id,status:checks.some(c=>c.state==='fail')?'NOT_READY':checks.some(c=>c.state==='unknown')?'UNKNOWN':'READY',checks});
  }
  const histories=new WeakSet();
  function history(past,present,future){const h=freeze({past,present,future});histories.add(h);return h;}
  function createHistory(d){return history([],createDocument(d),[]);}
  function validHistory(h){reject('INVALID_HISTORY',histories.has(h),'Use createHistory to start a history');}
  function validateAction(a,code){
    const c=code||'INVALID_ACTION';object(a,['op','pageIds','degrees'],c);
    reject(c,['duplicate','delete','reorder','rotate','extract'].includes(a.op),'Unknown operation');
    reject(c,Array.isArray(a.pageIds)&&a.pageIds.length>0&&a.pageIds.length<=LIMITS.pages&&a.pageIds.every(id=>text(id,100))&&new Set(a.pageIds).size===a.pageIds.length,'Invalid page selection');
    reject(c,a.op==='rotate'?[90,180,270,-90,-180,-270].includes(a.degrees):a.degrees===undefined,'Invalid degrees');
    return freeze({op:a.op,pageIds:a.pageIds.slice(),...(a.op==='rotate'?{degrees:a.degrees}:{})});
  }
  function applyAction(h,action){
    validHistory(h);const a=validateAction(action),d=h.present;
    reject('INCOMPLETE_DOCUMENT',d.pageCount!==null&&d.pages.length===d.pageCount,'Full page model required');
    const selected=new Set(a.pageIds),byId=new Map(d.pages.map(p=>[p.id,p]));
    reject('INVALID_ACTION',a.pageIds.every(id=>byId.has(id)),'Unknown page id');
    let pages;
    if(a.op==='reorder'||a.op==='extract'){
      reject('INVALID_ACTION',a.op!=='reorder'||a.pageIds.length===d.pages.length,'Reorder must contain every page exactly once');pages=a.pageIds.map(id=>byId.get(id));
    }else if(a.op==='delete')pages=d.pages.filter(p=>!selected.has(p.id));
    else if(a.op==='rotate')pages=d.pages.map(p=>selected.has(p.id)?{...p,rotation:(p.rotation+a.degrees+360)%360}:p);
    else {
      reject('PAGE_LIMIT',d.pages.length+a.pageIds.length<=LIMITS.pages,'Page limit exceeded');
      let serial=1;const ids=new Set(byId.keys());pages=[];
      for(const p of d.pages){pages.push(p);if(selected.has(p.id)){let id;do{id='copy-'+serial++;}while(ids.has(id));ids.add(id);pages.push({...p,id,sourceId:p.sourceId||p.id});}}
    }
    reject('INVALID_ACTION',pages.length>0,'Cannot create empty document');
    const next=createDocument({...d,pages,pageCount:pages.length,bytes:null,structuralValidation:'unknown'});
    return history([...h.past,d].slice(-LIMITS.history),next,[]);
  }
  function undo(h){validHistory(h);return h.past.length?history(h.past.slice(0,-1),h.past[h.past.length-1],[h.present,...h.future].slice(0,LIMITS.history)):h;}
  function redo(h){validHistory(h);return h.future.length?history([...h.past,h.present].slice(-LIMITS.history),h.future[0],h.future.slice(1)):h;}
  function validateWorkflow(w){
    const c='INVALID_WORKFLOW';object(w,['version','steps'],c);reject(c,w.version===1&&Array.isArray(w.steps)&&w.steps.length<=LIMITS.steps,'Invalid workflow version or step count');
    return freeze({version:1,steps:w.steps.map(a=>validateAction(a,c))});
  }
  async function runWorkflow(document,workflow,options){
    const w=validateWorkflow(workflow),opts=options||{};let h=createHistory(document),completed=0;
    const cancelled=()=>{if(opts.signal&&opts.signal.aborted)throw error('CANCELLED','Workflow cancelled',{stepsCompleted:completed});};
    cancelled();
    for(const step of w.steps){
      await (opts.yieldControl?opts.yieldControl():new Promise(resolve=>setTimeout(resolve,0)));
      cancelled();h=applyAction(h,step);completed++;cancelled();
    }
    return freeze({version:1,dryRun:true,stepsCompleted:completed,document:h.present,history:h});
  }
  return Object.freeze({LIMITS,parseJSON,validateProfile,createDocument,evaluate,validateAction,createHistory,applyAction,undo,redo,validateWorkflow,runWorkflow});
}));
