package com.prepare.app;

import android.content.ContentResolver;
import android.graphics.*;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import java.io.*;
import java.util.List;

/** Serial, raster-only conversion. Never modifies an input or writes to a public path. */
public final class Engine {
    public interface Progress { void page(int completed,int total,int edge); }
    private final ContentResolver resolver;
    private final File cache;
    public Engine(ContentResolver resolver,File cache) { this.resolver=resolver; this.cache=cache; }
    public File prepare(List<Uri> inputs,Geometry.Layout layout,int margin,long limit,
                        Policy.Token token,Progress progress) throws IOException {
        if(inputs==null || inputs.isEmpty() || inputs.size()>Policy.MAX_PAGES || limit<1 || limit>100000000)
            throw new IllegalArgumentException("Choose 1–20 JPEG/PNG images and a limit up to 100 MB.");
        Geometry.fit(1,1,layout,margin);
        token.check();
        int budgetEdge=(int)Math.sqrt(8000000.0/inputs.size());
        for(int requested:new int[]{1600,1200,800,500,320}) {
            int edge=Math.min(requested,budgetEdge);
            File output=File.createTempFile("prepare-",".pdf",cache);
            boolean accepted=false;
            PdfDocument document=new PdfDocument();
            try {
                for(int i=0;i<inputs.size();i++) {
                    token.check();
                    Uri uri=inputs.get(i);
                    BitmapFactory.Options bounds=new BitmapFactory.Options(); bounds.inJustDecodeBounds=true;
                    try(InputStream in=resolver.openInputStream(uri)) {
                        if(in==null) throw new IOException("Image cannot be opened.");
                        BitmapFactory.decodeStream(in,null,bounds);
                    }
                    if(!"image/jpeg".equals(bounds.outMimeType) && !"image/png".equals(bounds.outMimeType))
                        throw new IOException("Only valid JPEG and PNG images are supported.");
                    if(bounds.outWidth<1 || bounds.outHeight<1 || bounds.outWidth>65535 || bounds.outHeight>65535
                       || (long)bounds.outWidth*bounds.outHeight>100000000L)
                        throw new IOException("Image exceeds the 100 megapixel input safety limit.");
                    token.check();
                    final int[] original=new int[2];
                    Bitmap bitmap=ImageDecoder.decodeBitmap(ImageDecoder.createSource(resolver,uri),(decoder,info,source)-> {
                        int w=info.getSize().getWidth(),h=info.getSize().getHeight();
                        if(w<1 || h<1 || w>65535 || h>65535 || (long)w*h>100000000L)
                            throw new IllegalArgumentException("Invalid or oversized image dimensions.");
                        original[0]=w; original[1]=h;
                        double scale=Math.min(1.0,(double)edge/Math.max(w,h));
                        decoder.setTargetSize(Math.max(1,(int)(w*scale)),Math.max(1,(int)(h*scale)));
                        decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
                    });
                    try {
                        token.check();
                        if(bitmap.getWidth()>edge || bitmap.getHeight()>edge) throw new IOException("Decoder exceeded safety bound.");
                        Geometry g=Geometry.fit(original[0],original[1],layout,margin);
                        PdfDocument.Page page=document.startPage(new PdfDocument.PageInfo.Builder(g.pageWidth,g.pageHeight,i+1).create());
                        try {
                            Canvas canvas=page.getCanvas(); canvas.drawColor(Color.WHITE);
                            Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
                            canvas.drawBitmap(bitmap,null,new RectF(g.left,g.top,g.left+g.width,g.top+g.height),paint);
                        } finally { document.finishPage(page); }
                    } finally { bitmap.recycle(); }
                    if(progress!=null) progress.page(i+1,inputs.size(),edge);
                }
                token.check();
                try(Policy.LimitedOutput out=new Policy.LimitedOutput(new FileOutputStream(output),limit,token)) {
                    try { document.writeTo(out); }
                    finally { out.checkFailure(); } // Native may swallow or wrap the callback IOException.
                }
                token.check();
                if(output.length()==0) throw new IOException("PDF writer produced no output.");
                if(output.length()>limit) throw new Policy.TooLarge();
                accepted=true; return output;
            } catch(Policy.TooLarge tooLarge) {
                token.check(); // Try a smaller raster, never return an oversized file.
            } finally { document.close(); if(!accepted) output.delete(); }
        }
        throw new Policy.TooLarge();
    }
}
