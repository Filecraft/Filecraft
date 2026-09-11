package com.prepare.app;

import android.app.Activity;
import android.content.*;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import android.text.InputType;
import android.view.View;
import android.widget.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** One workspace, system pickers, no storage or network permission. */
public final class MainActivity extends Activity {
    public static final int PREPARE_ID=1001, CLEAR_ID=1002;
    private static final int PICK=10,SAVE=11;
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final ArrayList<Uri> images=new ArrayList<>();
    private TextView status,selection;
    private Spinner layout,margin;
    private EditText limit;
    private Button pick,prepare,save,cancel,clear;
    private volatile Policy.Token token;
    private boolean busy,pickerOpen;
    private File prepared,cache;
    private static boolean cacheInitialized;
    private static void deleteTree(File root) {
        File[] children=root.listFiles();
        if(children!=null) for(File f:children) deleteTree(f);
        root.delete();
    }
    private static synchronized File newWorkspace(File root) {
        if(!cacheInitialized) { deleteTree(root); cacheInitialized=true; }
        File session=new File(root,UUID.randomUUID().toString());
        session.mkdirs(); return session;
    }

    public static Intent pickIntent() {
        return new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*")
            .addCategory(Intent.CATEGORY_OPENABLE)
            .putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"image/jpeg","image/png"})
            .putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true).putExtra(Intent.EXTRA_LOCAL_ONLY,true);
    }
    public static Intent saveIntent() {
        return new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/pdf")
            .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_LOCAL_ONLY,true)
            .putExtra(Intent.EXTRA_TITLE,"Prepared.pdf");
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        if(android.os.Build.VERSION.SDK_INT>=30) getWindow().setDecorFitsSystemWindows(false);
        cache=newWorkspace(new File(getCacheDir(),"prepared"));
        ScrollView scroll=new ScrollView(this);
        LinearLayout body=new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL);
        int pad=(int)(20*getResources().getDisplayMetrics().density);
        body.setPadding(pad,pad,pad,pad); scroll.addView(body); setContentView(scroll);
        body.setOnApplyWindowInsetsListener((v,insets)-> {
            v.setPadding(pad+insets.getSystemWindowInsetLeft(),pad+insets.getSystemWindowInsetTop(),
                pad+insets.getSystemWindowInsetRight(),pad+insets.getSystemWindowInsetBottom()); return insets;
        });
        body.requestApplyInsets();
        TextView title=label(body,"Prepare · experimental"); title.setTextSize(26); title.setAccessibilityHeading(true);
        label(body,"JPEG / PNG → PDF. On-device only. Choose local files; system providers may have their own cloud services. Originals stay unchanged.");
        pick=button(body,"Choose images (up to 20)",v->openPicker());
        selection=label(body,"No images selected.");
        layout=spinner(body,"Page layout",new String[]{"A4 (595 × 842 pt)","Original aspect (1 px = 1 pt, longest edge ≤ 2000 pt)","Letter (612 × 792 pt)"});
        margin=spinner(body,"Margins",new String[]{"None","18 pt (¼ inch)","36 pt (½ inch)","72 pt (1 inch)"}); margin.setSelection(1);
        TextView limitLabel=label(body,"Maximum PDF size (MB; 1 MB = 1,000,000 bytes)");
        limit=new EditText(this); limit.setId(View.generateViewId()); limitLabel.setLabelFor(limit.getId());
        limit.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(16)});
        limit.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL); limit.setSingleLine(true); limit.setText("5"); body.addView(limit);
        label(body,"Images are flattened onto white pages; embedded image metadata is not copied. EXIF orientation is applied. Resolution may be reduced to fit. No OCR, PDF input or password support.");
        prepare=button(body,"Prepare PDF",v->prepare()); prepare.setId(PREPARE_ID);
        save=button(body,"Save a copy…",v->openSave());
        cancel=button(body,"Cancel current operation",v->{ if(token!=null) token.cancel(); status.setText("Cancelling… waiting for the current native decode or provider operation."); });
        clear=button(body,"Clear images and prepared copy",v->{ clearPrepared(); images.clear(); selection.setText("No images selected."); status.setText("Workspace cleared. Saved copies and originals are unchanged."); update(); }); clear.setId(CLEAR_ID);
        status=label(body,state==null?"Choose images to begin.":"Workspace reset after recreation; originals and saved copies are unchanged.");
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        update();
    }
    private TextView label(LinearLayout body,String text) {
        TextView view=new TextView(this); view.setText(text); view.setTextSize(16); view.setPadding(0,12,0,12); body.addView(view); return view;
    }
    private Button button(LinearLayout body,String text,View.OnClickListener click) {
        Button b=new Button(this); b.setText(text); b.setMinHeight((int)(48*getResources().getDisplayMetrics().density)); b.setOnClickListener(click); body.addView(b); return b;
    }
    private Spinner spinner(LinearLayout body,String name,String[] items) {
        TextView label=label(body,name); Spinner s=new Spinner(this); s.setId(View.generateViewId());
        label.setLabelFor(s.getId()); s.setContentDescription(name); s.setMinimumHeight((int)(48*getResources().getDisplayMetrics().density));
        ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,items);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item); s.setAdapter(adapter); body.addView(s); return s;
    }
    private void update() {
        boolean idle=!busy&&!pickerOpen;
        pick.setEnabled(idle); prepare.setEnabled(idle&&!images.isEmpty()); save.setEnabled(idle&&prepared!=null);
        clear.setEnabled(idle); cancel.setEnabled(busy); layout.setEnabled(idle); margin.setEnabled(idle); limit.setEnabled(idle);
    }
    private void clearPrepared() { if(prepared!=null) prepared.delete(); prepared=null; }
    private void openPicker() {
        try { pickerOpen=true; update(); startActivityForResult(pickIntent(),PICK); }
        catch(ActivityNotFoundException e) { pickerOpen=false; update(); status.setText("No system document picker is available."); }
    }
    private void openSave() {
        try { pickerOpen=true; update(); startActivityForResult(saveIntent(),SAVE); }
        catch(ActivityNotFoundException e) { pickerOpen=false; update(); status.setText("No system save picker is available."); }
    }
    @Override public void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data); pickerOpen=false; update();
        if(result!=RESULT_OK || data==null) { status.setText("Picker cancelled. Workspace unchanged."); return; }
        if(request==PICK) {
            LinkedHashSet<Uri> chosen=new LinkedHashSet<>();
            ClipData clips=data.getClipData();
            if(clips!=null) for(int i=0;i<clips.getItemCount();i++) chosen.add(clips.getItemAt(i).getUri());
            else if(data.getData()!=null) chosen.add(data.getData());
            if(chosen.isEmpty() || chosen.size()>Policy.MAX_PAGES) { status.setText("Choose between 1 and 20 images; workspace unchanged."); return; }
            for(Uri uri:chosen) if(uri==null || !"content".equals(uri.getScheme())) { status.setText("Choose images using a system document provider."); return; }
            clearPrepared(); images.clear(); images.addAll(chosen);
            selection.setText(images.size()+" image(s), in picker-returned order. Choose again to replace the selection.");
            status.setText("Ready. Prepare to validate images and create a private PDF."); update();
        } else if(request==SAVE && data.getData()!=null) {
            Uri destination=data.getData();
            if(prepared==null) { status.setText("Prepared copy is no longer available. Remove the empty destination and prepare again."); return; }
            if(!"content".equals(destination.getScheme()) || images.contains(destination)) { status.setText("Unsafe destination rejected; originals were not changed."); return; }
            saveCopy(destination);
        }
    }
    private void prepare() {
        final long cap;
        try { cap=Policy.limitBytes(limit.getText().toString()); }
        catch(IllegalArgumentException e) { limit.setError("Enter more than 0 and at most 100 MB (up to 6 decimals)."); return; }
        clearPrepared(); busy=true; token=new Policy.Token(); final Policy.Token job=token;
        final ArrayList<Uri> inputs=new ArrayList<>(images);
        final Geometry.Layout page=Geometry.Layout.values()[layout.getSelectedItemPosition()];
        final int points=new int[]{0,18,36,72}[margin.getSelectedItemPosition()];
        status.setText("Preparing locally…"); update();
        worker.execute(()-> {
            File result=null; String message;
            try {
                result=new Engine(getContentResolver(),cache).prepare(inputs,page,points,cap,job,(n,total,edge)->runOnUiThread(()-> {
                    if(!isDestroyed()) status.setText("Prepared page "+n+" / "+total+" · raster edge ≤ "+edge+" px. Checking byte limit…");
                }));
                message="Ready: "+result.length()+" bytes, within "+cap+" bytes. Review the saved PDF before submitting it. Save a copy to keep it.";
            } catch(Exception e) { message=errorMessage(e); }
            catch(OutOfMemoryError e) { message="Not enough memory. Try fewer or smaller images."; }
            final File file=result; final String text=message;
            runOnUiThread(()-> {
                if(isDestroyed()) { if(file!=null) file.delete(); return; }
                busy=false;
                try { job.check(); prepared=file; status.setText(text); }
                catch(Policy.Cancelled e) { if(file!=null) file.delete(); status.setText(e.getMessage()); }
                update();
            });
        });
    }
    private String errorMessage(Exception e) {
        if(e instanceof Policy.Cancelled || e instanceof Policy.TooLarge) return e.getMessage();
        if(e instanceof SecurityException) return "File permission expired. Choose the images again.";
        return "Could not complete this operation. Check the file format, local provider and free storage, then try again.";
    }
    private void saveCopy(Uri destination) {
        busy=true; token=new Policy.Token(); final Policy.Token job=token; final File source=prepared;
        status.setText("Saving and verifying the new copy…"); update();
        worker.execute(()-> {
            String message;
            try {
                byte[] expected; long count=source.length();
                job.check();
                try(InputStream in=new FileInputStream(source); OutputStream out=getContentResolver().openOutputStream(destination,"wt")) {
                    if(out==null) throw new IOException("No output stream");
                    expected=Copy.transfer(in,out,count,job);
                }
                try(InputStream in=getContentResolver().openInputStream(destination)) {
                    if(in==null) throw new IOException("Cannot verify output");
                    Copy.verify(in,count,expected,job);
                }
                job.check();
                message="Saved and read-back verified: "+count+" bytes. Originals unchanged.";
            } catch(Exception e) {
                boolean removed=false;
                try { removed=DocumentsContract.deleteDocument(getContentResolver(),destination); } catch(Exception ignored) { }
                message=errorMessage(e)+(removed?" New destination removed.":" A partial destination may remain: remove it in Files. No successful save is claimed.");
            }
            final String text=message;
            runOnUiThread(()-> { if(!isDestroyed()) { busy=false; status.setText(text); update(); } });
        });
    }
    @Override public void onDestroy() {
        if(token!=null) token.cancel();
        worker.execute(()->deleteTree(cache));
        worker.shutdown(); super.onDestroy();
    }
}
