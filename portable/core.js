'use strict';
const PrepareCore = (() => {
  function layout(w,h,{paper='original',margin=0,dpi=0,edge=2400}={}) {
    if (![w,h,margin,dpi,edge].every(Number.isFinite) || w<=0 || h<=0 || margin<0 || margin>72 || ![0,96,150,200,300].includes(dpi) || edge<1) throw Error('Invalid layout');
    if (!['original','a4','letter'].includes(paper)) throw Error('Invalid paper');
    const page=paper==='a4'?[595.28,841.89]:paper==='letter'?[612,792]:[w*720/Math.max(w,h),h*720/Math.max(w,h)];
    const scale=Math.min((page[0]-2*margin)/w,(page[1]-2*margin)/h);
    if(scale<=0) throw Error('Margins consume the page');
    const dw=w*scale,dh=h*scale;
    const resize=Math.min(1,edge/Math.max(w,h),dpi?dw*dpi/72/w:1);
    return {page,rect:[(page[0]-dw)/2,(page[1]-dh)/2,dw,dh],pixels:[Math.max(1,Math.floor(w*resize)),Math.max(1,Math.floor(h*resize))]};
  }
  function pdf(pages) {
    if(!pages.length || pages.length>20) throw Error('Use 1–20 pages');
    const enc=new TextEncoder(),chunks=[],offsets=[0];let size=0;
    const add=x=>{const b=typeof x==='string'?enc.encode(x):x;chunks.push(b);size+=b.length;};
    const object=(id,body)=>{offsets[id]=size;add(`${id} 0 obj\n`);body();add('\nendobj\n');};
    const stream=(dict,bytes)=>{add(`<< ${dict} /Length ${bytes.length} >>\nstream\n`);add(bytes);add('\nendstream');};
    add('%PDF-1.4\n%Prepare\n');
    object(1,()=>add('<< /Type /Catalog /Pages 2 0 R >>'));
    object(2,()=>add(`<< /Type /Pages /Count ${pages.length} /Kids [${pages.map((_,i)=>`${3+i*3} 0 R`).join(' ')}] >>`));
    pages.forEach((p,i)=>{
      const id=3+i*3,[w,h]=p.layout.page,[x,y,dw,dh]=p.layout.rect;
      object(id,()=>add(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${w} ${h}] /Resources << /XObject << /Im ${id+1} 0 R >> >> /Contents ${id+2} 0 R >>`));
      object(id+1,()=>stream(`/Type /XObject /Subtype /Image /Width ${p.width} /Height ${p.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode`,p.jpeg));
      object(id+2,()=>stream('',enc.encode(`q ${dw} 0 0 ${dh} ${x} ${y} cm /Im Do Q`)));
    });
    const start=size;add(`xref\n0 ${offsets.length}\n0000000000 65535 f \n`);
    for(const n of offsets.slice(1))add(`${String(n).padStart(10,'0')} 00000 n \n`);
    add(`trailer\n<< /Size ${offsets.length} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`);
    const out=new Uint8Array(size);let pos=0;for(const b of chunks){out.set(b,pos);pos+=b.length;}return out;
  }
  function dimensions(b) {
    const view=new DataView(b.buffer,b.byteOffset,b.byteLength);
    const valid=(width,height,type)=>{if(!width||!height||width*height>24_000_000)throw Error('Images must be at most 24 megapixels');return {width,height,type};};
    if(b.length>=33 && [137,80,78,71,13,10,26,10].every((n,i)=>b[i]===n)) {
      if(view.getUint32(8)!==13 || view.getUint32(12)!==0x49484452)throw Error('Invalid PNG');
      let pos=8;while(pos+12<=b.length){const n=view.getUint32(pos),tag=view.getUint32(pos+4);if(tag===0x6163544c)throw Error('Animated PNG is not supported');if(n>b.length-pos-12)throw Error('Invalid PNG chunk');pos+=n+12;}
      return valid(view.getUint32(16),view.getUint32(20),'png');
    }
    if(b[0]===255 && b[1]===216) {
      let pos=2;while(pos+4<=b.length){if(b[pos++]!==255)throw Error('Invalid JPEG');while(b[pos]===255)pos++;const tag=b[pos++];if(tag===0xd9||tag===0xda)break;if(tag===0x01 || (tag>=0xd0&&tag<=0xd7))continue;const n=view.getUint16(pos);if(n<2||pos+n>b.length)throw Error('Invalid JPEG');if([0xc0,0xc1,0xc2].includes(tag)){if(n<8)throw Error('Invalid JPEG');return valid(view.getUint16(pos+5),view.getUint16(pos+3),'jpeg');}pos+=n;}
      throw Error('Invalid or unsupported JPEG');
    }
    throw Error('Choose JPEG or PNG images; HEIC needs conversion or the Mac app. PDF input is not supported');
  }
  return {layout,pdf,dimensions};
})();
if(typeof module!=='undefined') module.exports=PrepareCore;
