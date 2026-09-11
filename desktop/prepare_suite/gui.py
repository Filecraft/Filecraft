"""Native Tk desktop UI. All parsing/rendering occurs in disposable workers."""
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from . import __version__
from .core import capabilities


def command():
    if getattr(sys,'frozen',False):return [sys.executable,'--worker']
    return [sys.executable,str(Path(__file__).resolve().parents[1]/'launch.py'),'--worker']

class App:
    def __init__(self,root):
        self.root=root;root.title('Prepare — local document suite');root.geometry('1040x780');root.minsize(840,680)
        self.preview_identity=tk.StringVar(value='No preview rendered.');self.preview_request={}
        self.source='';self.busy=False;self.proc=None;self.messages=queue.Queue();self.output='';self.preview_dir=None;self.photo=None
        self.target=tk.StringVar();self.action=tk.StringVar(value='copy');self.password=tk.StringVar();self.output_password=tk.StringVar()
        self.pages=tk.StringVar();self.rotation=tk.StringVar(value='0');self.dpi=tk.StringVar(value='120');self.quality=tk.StringVar(value='85');self.language=tk.StringVar(value='eng')
        self.page=tk.StringVar(value='1');self.annotation=tk.StringVar();self.fields=tk.StringVar(value='{}')
        self.status=tk.StringVar(value='Choose a local file. Originals are never overwritten.')
        outer=ttk.Frame(root,padding=20);outer.pack(fill='both',expand=True)
        ttk.Label(outer,text='Prepare',font=('TkDefaultFont',26,'bold')).pack(anchor='w')
        ttk.Label(outer,text=f'Desktop {__version__}  ·  Local processing  ·  No accounts or uploads').pack(anchor='w',pady=(0,14))
        bar=ttk.Frame(outer);bar.pack(fill='x')
        self.open_button=ttk.Button(bar,text='Choose file…',command=self.choose);self.open_button.pack(side='left')
        self.source_label=ttk.Label(bar,text='No document selected',wraplength=780);self.source_label.pack(side='left',padx=12)
        body=ttk.Frame(outer);body.pack(fill='both',expand=True,pady=14)
        left=ttk.Frame(body);left.pack(side='left',fill='both',expand=True,padx=(0,16))
        right=ttk.LabelFrame(body,text='Visual review',padding=8);right.pack(side='right',fill='both',expand=True)
        ttk.Label(left,text='1. Choose output format',font=('TkDefaultFont',13,'bold')).pack(anchor='w')
        self.target_box=ttk.Combobox(left,textvariable=self.target,state='readonly',width=30);self.target_box.pack(fill='x',pady=6)
        self.target_box.bind('<<ComboboxSelected>>',lambda e:self.explain())
        ttk.Label(left,text='ZIP/GZ work with any extension (archive compression).\nFormat conversion is limited to the choices shown.',wraplength=460).pack(anchor='w',pady=(0,12))
        self.options=ttk.LabelFrame(left,text='2. Conversion options',padding=10);self.options.pack(fill='x')
        self.row('PDF operation',self.action,['copy','optimize','rasterize','encrypt','decrypt','fill','annotate'])
        self.row('Pages (e.g. 1,3,2; blank = all)',self.pages)
        self.row('Clockwise rotation',self.rotation,['0','90','180','270'])
        self.row('Preview / image page',self.page)
        self.row('Render DPI (36–200)',self.dpi)
        self.row('Image quality (1–95)',self.quality)
        self.row('PDF input password',self.password,secret=True)
        self.row('New encryption password',self.output_password,secret=True)
        self.row('OCR language (local data)',self.language)
        self.row('Text note (annotate)',self.annotation)
        self.row('Form values (JSON object)',self.fields)
        ttk.Button(left,text='Inspect PDF / list form fields',command=self.inspect).pack(anchor='w',pady=8)
        ttk.Label(left,text='PDF options apply only to PDF input. OCR needs local Tesseract. Media needs local FFmpeg. Text-first Office conversion loses layout; it does not execute macros.',wraplength=450).pack(anchor='w')
        buttons=ttk.Frame(left);buttons.pack(fill='x',pady=10)
        self.save_button=ttk.Button(buttons,text='3. Export new copy…',command=self.save);self.save_button.pack(side='left')
        self.cancel_button=ttk.Button(buttons,text='Cancel',command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=8)
        pb=ttk.Frame(right);pb.pack(fill='x')
        ttk.Button(pb,text='Preview source',command=lambda:self.preview(False)).pack(side='left')
        ttk.Button(pb,text='Preview output',command=lambda:self.preview(True)).pack(side='left',padx=6)
        self.canvas=tk.Canvas(right,width=330,height=365,background='#e8e9eb',highlightthickness=0);self.canvas.pack(fill='both',expand=True,pady=8)
        ttk.Label(right,text='Rendered in a separate process. Review every page.\nPreview is not sanitization or a readability guarantee.',wraplength=360).pack(anchor='w')
        ttk.Label(right,textvariable=self.preview_identity,wraplength=350).pack(anchor='w')
        self.details=tk.Text(outer,height=5,wrap='word',state='disabled');self.details.pack(fill='x')
        ttk.Label(outer,textvariable=self.status,wraplength=950).pack(fill='x',pady=(10,0))
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(60,self.poll)
    def row(self,label,var,values=None,secret=False):
        n=len(self.options.grid_slaves())//2
        ttk.Label(self.options,text=label).grid(row=n,column=0,sticky='w',pady=2,padx=(0,10))
        widget=ttk.Combobox(self.options,textvariable=var,values=values,state='readonly',width=22) if values else ttk.Entry(self.options,textvariable=var,width=25,show='•' if secret else '')
        widget.grid(row=n,column=1,sticky='ew',pady=2)
        self.options.columnconfigure(1,weight=1)
    def detail(self,text):
        self.details.configure(state='normal');self.details.delete('1.0','end');self.details.insert('1.0',text);self.details.configure(state='disabled')
    def choose(self):
        path=filedialog.askopenfilename(title='Choose a local file')
        if path:
            try:self.load_source(path)
            except Exception as exc:self.status.set(str(exc))
    def load_source(self,path):
        if self.busy:raise ValueError('Cancel or finish the current job first.')
        caps=capabilities(path);self.source=path;self.output='';self.source_label.configure(text=path)
        self.target_box.configure(values=caps['targets']);self.target.set(caps['targets'][0]);self.canvas.delete('all')
        self.photo=None;self.preview_identity.set('No preview rendered.')
        self.password.set('');self.output_password.set('');self.pages.set('');self.fields.set('{}');self.action.set('copy');self.explain()
    def explain(self):
        self.status.set('Ready to create a new copy. Existing files will not be replaced.')
        self.detail('Conversion ≠ compression. Outputs can be larger. Re-encoding can lose metadata, quality, formatting, text layers or interactivity. PDF copy/fill/annotation is not sanitization; active content may remain. Use local folders: system file providers can sync to cloud independently.')
    def get_options(self):
        pages=[int(n.strip())-1 for n in self.pages.get().split(',')] if self.pages.get().strip() else None
        if pages is not None and (not pages or any(n<0 for n in pages)):raise ValueError('Pages must be comma-separated positive numbers.')
        options={'action':self.action.get(),'rotation':int(self.rotation.get()),'page':int(self.page.get())-1,'dpi':int(self.dpi.get()),'quality':int(self.quality.get()),'password':self.password.get(),'output_password':self.output_password.get(),'language':self.language.get(),'annotation':self.annotation.get(),'fields':json.loads(self.fields.get())}
        if pages is not None:options['pages']=pages
        return options
    def save(self):
        if not self.source or self.busy:return
        target=self.target.get();ext='pdf' if target=='ocr-pdf' else 'txt' if target=='ocr-txt' else target
        destination=filedialog.asksaveasfilename(title='Save a new copy — existing files are protected',initialfile=Path(self.source).stem+'-prepared.'+ext,defaultextension='.'+ext)
        if destination:self.begin_export(destination)
    def begin_export(self,destination):
        try:self.start({'source':self.source,'output':destination,'target':self.target.get(),'options':self.get_options()},'export')
        except Exception as exc:self.status.set(str(exc))
    def inspect(self):
        if not self.source or self.busy:return
        if Path(self.source).suffix.lower()!='.pdf':self.status.set('Field inspection is available for PDF input.');return
        self.start({'source':self.source,'mode':'inspect','options':{'password':self.password.get()}},'inspect')
    def preview(self,use_output):
        if self.busy:return
        source=self.output if use_output else self.source
        if not source:self.status.set('Choose a source or export a copy first.');return
        try:
            if self.preview_dir:self.preview_dir.cleanup()
            self.preview_dir=tempfile.TemporaryDirectory(prefix='prepare-preview-')
            destination=str(Path(self.preview_dir.name)/'preview.png')
            options=self.get_options();options['action']='copy';options['dpi']=72
            if use_output and self.output_password.get():options['password']=self.output_password.get()
            self.start({'source':source,'output':destination,'target':'png','options':options},'preview')
        except Exception as exc:self.status.set(str(exc))
    def start(self,request,kind):
        if self.busy:raise ValueError('A job is already running.')
        if kind=='preview':self.preview_request=request
        self.busy=True;self.cancelled=False;self.status.set('Processing locally…');self.cancel_button.configure(state='normal');self.save_button.configure(state='disabled');self.open_button.configure(state='disabled')
        def run():
            try:
                kwargs={'start_new_session':True} if os.name=='posix' else {'creationflags':subprocess.CREATE_NO_WINDOW}
                self.proc=subprocess.Popen(command(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,**kwargs)
                if self.cancelled:self.terminate()
                try:
                    stdout,_=self.proc.communicate(json.dumps(request).encode('utf-8'),timeout=180)
                except subprocess.TimeoutExpired:
                    self.terminate();self.proc.communicate();raise ValueError('Job timed out. Review the output folder before retrying.')
                if self.cancelled:raise ValueError('Cancelled. If export completed just before cancellation, its new copy may remain.')
                if len(stdout)>1_000_000:raise ValueError('Worker response exceeded limit.')
                result=json.loads(stdout)
                self.messages.put((kind,result))
            except Exception as exc:self.messages.put((kind,{'ok':False,'error':str(exc)}))
            finally:self.proc=None
        threading.Thread(target=run,daemon=True).start()
    def terminate(self):
        if self.proc and self.proc.poll() is None:
            try:
                if os.name=='posix':os.killpg(self.proc.pid,signal.SIGKILL)
                else:subprocess.run(['taskkill','/PID',str(self.proc.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
            except (OSError,subprocess.SubprocessError):self.proc.kill()
    def cancel(self):self.cancelled=True;self.terminate()
    def poll(self):
        try:
            kind,response=self.messages.get_nowait();self.busy=False;self.cancel_button.configure(state='disabled');self.save_button.configure(state='normal');self.open_button.configure(state='normal')
            if not response['ok']:self.status.set(response.get('error','Worker failed.'))
            else:
                result=response['result']
                if kind=='preview':
                    from PIL import Image,ImageTk
                    with Image.open(result['output']) as image:
                        image.thumbnail((max(100,self.canvas.winfo_width()-10),max(100,self.canvas.winfo_height()-10)))
                        self.photo=ImageTk.PhotoImage(image.copy())
                    self.canvas.delete('all');self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.photo);self.status.set('Preview rendered locally. Inspect other pages before sharing.')
                    self.preview_identity.set(f"{Path(self.preview_request['source']).name} · page {self.preview_request['options']['page']+1} · SHA-256 {result['input_sha256']}")
                    self.detail(json.dumps(result,indent=2))
                elif kind=='inspect':self.detail(json.dumps(result,indent=2));self.status.set('PDF inspected. No active content was executed.')
                else:
                    self.canvas.delete('all');self.photo=None;self.preview_identity.set('Export complete. Preview output to review the new copy.')
                    self.output=result['output'];self.status.set(f"Saved {result['bytes']:,} bytes from {result['input_bytes']:,} bytes. Original unchanged.");self.detail(json.dumps(result,indent=2))
        except queue.Empty:pass
        finally:
            if self.root.winfo_exists():self.root.after(60,self.poll)
    def close(self):
        self.cancel()
        if self.preview_dir:self.preview_dir.cleanup()
        self.root.destroy()

def main():
    root=tk.Tk();App(root);root.mainloop()
