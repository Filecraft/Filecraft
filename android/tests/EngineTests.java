package com.prepare.app;

import android.app.Instrumentation;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import java.io.*;
import java.util.*;

/** Framework-only instrumentation: synthetic pixels, no personal documents. */
public final class EngineTests extends Instrumentation {
    private int passed;
    private void check(boolean value,String message) { if(!value) throw new AssertionError(message); }
    private void pass(String name) { passed++; Bundle b=new Bundle(); b.putString("stream","PASS "+name+"\n"); sendStatus(0,b); }
    private void partialPrefixCaps(Engine engine,File dir) throws IOException {
        Bitmap noise=Bitmap.createBitmap(320,320,Bitmap.Config.ARGB_8888);
        Random random=new Random(42);
        for(int y=0;y<320;y++) for(int x=0;x<320;x++) noise.setPixel(x,y,0xff000000|random.nextInt(0x1000000));
        File input=new File(dir,"noise.png");
        try(OutputStream out=new FileOutputStream(input)) { noise.compress(Bitmap.CompressFormat.PNG,100,out); }
        // Exercise the real native callback, including a nonempty prefix before failure.
        android.graphics.pdf.PdfDocument document=new android.graphics.pdf.PdfDocument();
        try {
            android.graphics.pdf.PdfDocument.Page page=document.startPage(new android.graphics.pdf.PdfDocument.PageInfo.Builder(320,320,1).create());
            page.getCanvas().drawBitmap(noise,0,0,null); document.finishPage(page);
            ByteArrayOutputStream complete=new ByteArrayOutputStream(); document.writeTo(complete);
            long cap=complete.size()/2;
            ByteArrayOutputStream prefix=new ByteArrayOutputStream();
            Policy.LimitedOutput limited=new Policy.LimitedOutput(prefix,cap,new Policy.Token());
            try { document.writeTo(limited); } catch(IOException nativeError) { /* checked independently below */ }
            check(prefix.size()>0 && prefix.size()<=cap,"native partial-prefix fixture did not hit cap");
            try { limited.checkFailure(); throw new AssertionError("native prefix accepted as complete"); }
            catch(Policy.TooLarge expected) { }
            pass("real PdfDocument partial prefix remains under cap but is rejected");
        } finally { document.close(); noise.recycle(); }
        List<Uri> inputs=Collections.singletonList(Uri.fromFile(input));
        File full=engine.prepare(inputs,Geometry.Layout.A4,18,1000000,new Policy.Token(),null);
        long size=full.length(); renderAll(full,1); full.delete();
        // The 320px input is never downsampled: none of the retry sizes can fit.
        for(long cap:new long[]{size/2,size-1}) {
            int[] attempts={0};
            try {
                File truncated=engine.prepare(inputs,Geometry.Layout.A4,18,cap,new Policy.Token(),
                    (n,total,edge)->attempts[0]++);
                truncated.delete(); throw new AssertionError("Engine accepted partial PDF under cap "+cap);
            } catch(Policy.TooLarge expected) { }
            check(attempts[0]==5,"TooLarge must exhaust all five resolution attempts");
            for(File file:dir.listFiles()) check(!file.getName().endsWith(".pdf"),"cap failure leaked prefix");
        }
        for(long cap:new long[]{size,size+1}) {
            File accepted=engine.prepare(inputs,Geometry.Layout.A4,18,cap,new Policy.Token(),null);
            check(accepted.length()>0 && accepted.length()<=cap,"accepted size exceeds exact cap");
            renderAll(accepted,1); accepted.delete();
        }
        pass("partial-prefix caps rejected and cleaned; exact/above-cap accepted PDFs render");
    }
    private Object field(MainActivity activity,String name) {
        try {
            java.lang.reflect.Field field=MainActivity.class.getDeclaredField(name);
            field.setAccessible(true); return field.get(activity);
        } catch(ReflectiveOperationException e) { throw new AssertionError(e); }
    }
    private void renderAll(File pdf,int pages) throws IOException {
        try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(pdf,ParcelFileDescriptor.MODE_READ_ONLY);
            PdfRenderer renderer=new PdfRenderer(fd)) {
            check(renderer.getPageCount()==pages,"accepted PDF page count");
            for(int i=0;i<pages;i++) try(PdfRenderer.Page page=renderer.openPage(i)) {
                Bitmap pixels=Bitmap.createBitmap(page.getWidth(),page.getHeight(),Bitmap.Config.ARGB_8888);
                try { page.render(pixels,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY); }
                finally { pixels.recycle(); }
            }
        }
    }
    private File prepareInUi(MainActivity activity) throws Exception {
        runOnMainSync(()->check(activity.findViewById(MainActivity.PREPARE_ID).performClick(),"prepare click"));
        long deadline=android.os.SystemClock.uptimeMillis()+20000;
        boolean[] busy={true};
        do {
            waitForIdleSync();
            runOnMainSync(()->busy[0]=(Boolean)field(activity,"busy"));
            if(busy[0]) Thread.sleep(20);
        } while(busy[0] && android.os.SystemClock.uptimeMillis()<deadline);
        check(!busy[0],"UI prepare timeout");
        File[] result={null};
        runOnMainSync(()-> {
            result[0]=(File)field(activity,"prepared");
            check(result[0]!=null && result[0].exists(),"UI produced a private PDF");
            check(((android.widget.Button)field(activity,"save")).isEnabled(),"save enabled after preparation");
        });
        renderAll(result[0],1); return result[0];
    }
    @SuppressWarnings("unchecked")
    private void settingInvalidation(File png,String setting) throws Exception {
        MainActivity activity=(MainActivity)startActivitySync(new android.content.Intent(getTargetContext(),MainActivity.class)
            .addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));
        try {
            waitForIdleSync();
            runOnMainSync(()-> {
                ((List<Uri>)field(activity,"images")).add(Uri.fromFile(png));
                activity.findViewById(MainActivity.PREPARE_ID).setEnabled(true);
            });
            File previous=prepareInUi(activity);
            runOnMainSync(()-> {
                if(setting.equals("limit")) ((android.widget.EditText)field(activity,"limit")).setText("1");
                else {
                    android.widget.Spinner spinner=(android.widget.Spinner)field(activity,setting);
                    spinner.setSelection(spinner.getSelectedItemPosition()+1);
                }
            });
            waitForIdleSync();
            runOnMainSync(()-> {
                check(field(activity,"prepared")==null,setting+" retained stale result");
                check(!previous.exists(),setting+" left previous private PDF");
                check(!((android.widget.Button)field(activity,"save")).isEnabled(),setting+" allows stale save");
                check(!((android.widget.TextView)field(activity,"status")).getText().toString().startsWith("Ready:"),setting+" stale status");
            });
            File replacement=prepareInUi(activity);
            check(!previous.equals(replacement),setting+" reused old file");
            pass("UI "+setting+" change deletes result, disables save, requires fresh renderable PDF");
        } finally { runOnMainSync(activity::finish); waitForIdleSync(); }
    }
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        Bundle result=new Bundle();
        try {
            File dir=new File(getTargetContext().getCacheDir(),"synthetic-tests"); dir.mkdirs();
            Bitmap bitmap=Bitmap.createBitmap(80,40,Bitmap.Config.ARGB_8888);
            bitmap.eraseColor(Color.WHITE);
            for(int y=0;y<40;y++) for(int x=0;x<40;x++) bitmap.setPixel(x,y,Color.RED);
            File png=new File(dir,"fixture.png");
            try(OutputStream out=new FileOutputStream(png)) { bitmap.compress(Bitmap.CompressFormat.PNG,100,out); }
            File jpg=new File(dir,"fixture.jpg");
            try(OutputStream out=new FileOutputStream(jpg)) { bitmap.compress(Bitmap.CompressFormat.JPEG,90,out); }
            bitmap.recycle();
            Engine engine=new Engine(getTargetContext().getContentResolver(),dir);
            List<Uri> inputs=Arrays.asList(Uri.fromFile(png),Uri.fromFile(jpg));
            File pdf=engine.prepare(inputs,Geometry.Layout.A4,18,1000000,new Policy.Token(),null);
            check(pdf.length()>0 && pdf.length()<=1000000,"PDF byte cap");
            try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(pdf,ParcelFileDescriptor.MODE_READ_ONLY);
                PdfRenderer renderer=new PdfRenderer(fd)) {
                check(renderer.getPageCount()==2,"page order/count");
                for(int i=0;i<2;i++) try(PdfRenderer.Page page=renderer.openPage(i)) {
                    check(page.getWidth()==595 && page.getHeight()==842,"A4 dimensions");
                    Bitmap rendered=Bitmap.createBitmap(595,842,Bitmap.Config.ARGB_8888);
                    page.render(rendered,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                    int red=rendered.getPixel(100,421);
                    check(Color.red(red)>200 && Color.green(red)<70,"left red pixels");
                    check(rendered.getPixel(490,421)==Color.WHITE,"right white pixels");
                    check(rendered.getPixel(5,5)==Color.WHITE,"white margins");
                    rendered.recycle();
                }
            }
            pass("JPEG/PNG PDF render, page count, aspect-fit and pixels");
            check(png.exists() && jpg.exists(),"sources preserved"); pdf.delete();
            for(Geometry.Layout layout:new Geometry.Layout[]{Geometry.Layout.LETTER,Geometry.Layout.ORIGINAL}) {
                File other=engine.prepare(Collections.singletonList(Uri.fromFile(png)),layout,18,1000000,new Policy.Token(),null);
                try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(other,ParcelFileDescriptor.MODE_READ_ONLY);
                    PdfRenderer renderer=new PdfRenderer(fd); PdfRenderer.Page page=renderer.openPage(0)) {
                    check(page.getWidth()==(layout==Geometry.Layout.LETTER?612:116),"layout width");
                    check(page.getHeight()==(layout==Geometry.Layout.LETTER?792:76),"layout height");
                }
                renderAll(other,1); other.delete();
            }
            pass("native Letter and original page dimensions");
            android.media.ExifInterface exif=new android.media.ExifInterface(jpg.getAbsolutePath());
            exif.setAttribute(android.media.ExifInterface.TAG_ORIENTATION,"6"); exif.saveAttributes();
            File oriented=engine.prepare(Collections.singletonList(Uri.fromFile(jpg)),Geometry.Layout.ORIGINAL,0,1000000,new Policy.Token(),null);
            try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(oriented,ParcelFileDescriptor.MODE_READ_ONLY);
                PdfRenderer renderer=new PdfRenderer(fd); PdfRenderer.Page page=renderer.openPage(0)) {
                check(page.getWidth()==40 && page.getHeight()==80,"EXIF rotated dimensions");
                Bitmap render=Bitmap.createBitmap(40,80,Bitmap.Config.ARGB_8888);
                page.render(render,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                check(Color.green(render.getPixel(20,10))<70,"EXIF rotated red top");
                check(Color.green(render.getPixel(20,70))>200,"EXIF rotated white bottom"); render.recycle();
            }
            oriented.delete(); pass("EXIF orientation applied to raster and geometry");
            try { engine.prepare(inputs,Geometry.Layout.A4,0,1,new Policy.Token(),null); throw new AssertionError("oversize accepted"); }
            catch(Policy.TooLarge expected) { } pass("cannot fit exact byte cap");
            partialPrefixCaps(engine,dir);
            int[] ioAttempts={0};
            try {
                engine.prepare(inputs,Geometry.Layout.A4,0,1000000,new Policy.Token(),(n,total,edge)-> {
                    if(n==1) ioAttempts[0]++;
                    if(n==total) for(File output:dir.listFiles()) if(output.getName().startsWith("prepare-")) {
                        check(output.delete() && output.mkdir(),"output I/O failure fixture");
                    }
                });
                throw new AssertionError("output I/O failure accepted");
            } catch(Policy.TooLarge wrong) { throw new AssertionError("I/O failure reclassified as cap",wrong); }
            catch(IOException expected) { }
            check(ioAttempts[0]==1,"non-cap I/O failure was retried");
            pass("non-cap output I/O rejected without retry");
            Policy.Token cancelled=new Policy.Token(); cancelled.cancel();
            try { engine.prepare(inputs,Geometry.Layout.A4,0,1000000,cancelled,null); throw new AssertionError("cancel ignored"); }
            catch(Policy.Cancelled expected) { } pass("pre-cancellation");
            Policy.Token mid=new Policy.Token();
            try { engine.prepare(inputs,Geometry.Layout.A4,0,1000000,mid,(n,total,edge)->mid.cancel()); throw new AssertionError("mid cancel ignored"); }
            catch(Policy.Cancelled expected) { } pass("mid-page cancellation cleanup");
            File bad=new File(dir,"invalid.png");
            try(OutputStream out=new FileOutputStream(bad)) { out.write(new byte[]{1,2,3}); }
            try { engine.prepare(Collections.singletonList(Uri.fromFile(bad)),Geometry.Layout.A4,0,1000000,new Policy.Token(),null); throw new AssertionError("invalid accepted"); }
            catch(IOException expected) { } pass("invalid image rejected");
            try { engine.prepare(Collections.emptyList(),Geometry.Layout.A4,0,1000000,new Policy.Token(),null); throw new AssertionError("empty accepted"); }
            catch(IllegalArgumentException expected) { } pass("empty input rejected");
            for(File f:dir.listFiles()) check(!f.getName().endsWith(".pdf"),"temporary PDF leaked");
            pass("failure/cancellation temporary cleanup");
            android.content.Intent pick=MainActivity.pickIntent();
            check(android.content.Intent.ACTION_OPEN_DOCUMENT.equals(pick.getAction()),"SAF selection");
            check(pick.getBooleanExtra(android.content.Intent.EXTRA_LOCAL_ONLY,false),"local picker");
            check(pick.getBooleanExtra(android.content.Intent.EXTRA_ALLOW_MULTIPLE,false),"multiple picker");
            android.content.Intent save=MainActivity.saveIntent();
            check(android.content.Intent.ACTION_CREATE_DOCUMENT.equals(save.getAction()),"save copy not overwrite");
            check("application/pdf".equals(save.getType()),"PDF MIME");
            pass("SAF intent contracts");
            MainActivity activity=(MainActivity)startActivitySync(new android.content.Intent(getTargetContext(),MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));
            runOnMainSync(()-> {
                check(activity.findViewById(MainActivity.PREPARE_ID)!=null,"Prepare action");
                check(!activity.findViewById(MainActivity.PREPARE_ID).isEnabled(),"empty workspace cannot prepare");
                check(activity.findViewById(MainActivity.CLEAR_ID).performClick(),"clear action");
                activity.finish();
            });
            pass("native UI empty state and clear");
            waitForIdleSync();
            for(String setting:new String[]{"limit","layout","margin"}) settingInvalidation(png,setting);
            for(File f:dir.listFiles()) f.delete(); dir.delete();
            result.putString("stream","OK ("+passed+" tests)\n"); finish(-1,result);
        } catch(Throwable error) {
            StringWriter trace=new StringWriter(); error.printStackTrace(new PrintWriter(trace));
            result.putString("stream","FAIL after "+passed+" tests\n"+trace); finish(0,result);
        }
    }
}
