#!/usr/bin/env python3
import sys, subprocess, importlib, shutil, os, time, tkinter as _tk, tkinter.messagebox as _mb

def _ensure_packages(packages, gui_log_callback=None):
    missing=[]
    for pkg,mod in packages:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append((pkg,mod))
    if not missing:
        return True
    try:
        root=_tk.Tk()
        root.withdraw()
        ok=_mb.askyesno("Install dependencies",f"The following packages are required and missing:\n\n" + "\n".join(p for p,_ in missing) + "\n\nInstall now?")
        root.destroy()
    except Exception:
        ok=True
    if not ok:
        return False
    for pkg,mod in missing:
        cmd=[sys.executable,"-m","pip","install",pkg]
        if os.name!="nt":
            cmd.insert(3,"--user")
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            out_lines=[]
            while True:
                line=proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    out_lines.append(line.rstrip())
                    if gui_log_callback:
                        try:
                            gui_log_callback(line.rstrip())
                        except Exception:
                            pass
                    else:
                        print(line.rstrip())
            rc=proc.wait()
            if rc!=0:
                if gui_log_callback:
                    gui_log_callback(f"[Error] pip install returned {rc} for {pkg}")
                return False
            time.sleep(0.2)
            importlib.invalidate_caches()
            importlib.import_module(mod)
        except Exception as ex:
            if gui_log_callback:
                gui_log_callback(f"[Error] Failed to install {pkg}: {ex}")
            return False
    return True

if not _ensure_packages([("requests","requests")]):
    try:
        _tk.Tk().withdraw()
        _mb.showerror("Missing dependencies","Required Python packages could not be installed. Please install them manually and restart the app.")
    except Exception:
        print("Required packages missing; please install 'requests' and restart.")
    sys.exit(1)

import json,re,threading,requests,subprocess,os,shutil,signal
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk,messagebox
import tkinter.font as tkfont

ROOT=Path(__file__).resolve().parent
TOOLS_DIR=ROOT/"Tools"
CACHE_DIR=ROOT/"Cache"
ARCHIVE_DIR=ROOT/"Archive"
BUILDS_DIR=ROOT/"Builds"
CATALOG_PATH=ROOT/"catalog.json"
PREFS_PATH=ROOT/"preferences.json"

RMAN_DL=TOOLS_DIR/"rman-dl.exe"
RMAN_LS=TOOLS_DIR/"rman-ls.exe"

RMAN_DL_JOBS=3
RMAN_DL_CDN_WORKERS=3

TOOL_URLS={
"https://github.com/RiotArchiveProject/catalog-download-script/raw/refs/heads/main/Tools/rman-dl.exe":TOOLS_DIR/"rman-dl.exe",
"https://github.com/RiotArchiveProject/catalog-download-script/raw/refs/heads/main/Tools/rman-ls.exe":TOOLS_DIR/"rman-ls.exe",
}
CATALOG_URL="https://raw.githubusercontent.com/RiotArchiveProject/catalog-download-script/refs/heads/main/catalog.json"

for d in (TOOLS_DIR,CACHE_DIR,ARCHIVE_DIR,BUILDS_DIR):
    d.mkdir(parents=True,exist_ok=True)

def load_catalog():
    if CATALOG_PATH.exists():
        try:
            return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_catalog_bytes(data_bytes: bytes):
    try:
        CATALOG_PATH.write_bytes(data_bytes)
        return True
    except Exception:
        return False

def load_prefs():
    if PREFS_PATH.exists():
        try:
            return json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_prefs(prefs):
    try:
        PREFS_PATH.write_text(json.dumps(prefs,indent=2),encoding="utf-8")
    except Exception:
        pass

def normalize_platform(entry):
    if not isinstance(entry,dict):
        return "unknown"
    plats=entry.get("platforms")
    if isinstance(plats,(list,tuple)) and plats:
        return ",".join(str(p) for p in plats)
    plat=entry.get("platform")
    if plat:
        return str(plat)
    return "unknown"

def parse_timestamp(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        try:
            return datetime.strptime(ts,"%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None

def sanitize_version(ver):
    return re.sub(r'[:*?"<>|]',"",str(ver or "unknown"))

def sanitize_artifact(a):
    return re.sub(r'[:*?"<>|/\\]',"",str(a or "unknown"))

def human_mb(bytes_val):
    try:
        mb=int(bytes_val)/1024/1024
    except Exception:
        return str(bytes_val)
    return f"{mb:.2f} MB" if mb<10 else f"{mb:.1f} MB"

def human_readable_bytes(n):
    try:
        n=int(n)
    except Exception:
        return str(n)
    if n<1024:
        return f"{n} B"
    if n<1024**2:
        return f"{n/1024:.1f} KB"
    if n<1024**3:
        return f"{n/1024**2:.2f} MB"
    return f"{n/1024**3:.2f} GB"

def download_tools_and_catalog(progress_callback=None):
    TOOLS_DIR.mkdir(parents=True,exist_ok=True)
    success=True
    try:
        if progress_callback:
            progress_callback("Fetching catalog.json...")
        r=requests.get(CATALOG_URL,timeout=30)
        r.raise_for_status()
        save_catalog_bytes(r.content)
        if progress_callback:
            progress_callback("catalog.json updated.")
    except Exception as ex:
        success=False
        if progress_callback:
            progress_callback(f"[Warn] Could not fetch catalog: {ex}")
    for url,local_path in TOOL_URLS.items():
        try:
            if progress_callback:
                progress_callback(f"Downloading {local_path.name}...")
            r=requests.get(url,timeout=30)
            r.raise_for_status()
            remote_bytes=r.content
            if local_path.exists():
                local_bytes=local_path.read_bytes()
                if local_bytes==remote_bytes:
                    if progress_callback:
                        progress_callback(f"{local_path.name} up to date.")
                    continue
            local_path.write_bytes(remote_bytes)
            if progress_callback:
                progress_callback(f"{local_path.name} downloaded.")
        except Exception as ex:
            success=False
            if progress_callback:
                progress_callback(f"[Warn] Failed to download {local_path.name}: {ex}")
    return success

def download_manifest(project: str, manifest_id: str, dest_base=CACHE_DIR):
    url=f"https://{project}.secure.dyn.riotcdn.net/channels/public/releases/{manifest_id}.manifest"
    dest=dest_base/project/"releases"/f"{manifest_id}.manifest"
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        return dest
    try:
        r=requests.get(url,timeout=30)
        if r.status_code==404:
            return None
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
    except Exception:
        return None

def run_rman_dl_cmd(project,manifest_path:Path,outdir:Path,langs=None,file_filter=None,mode="download",multithreaded=False,jobs=None,cdn_workers=None):
    if not RMAN_DL.exists():
        raise FileNotFoundError(f"rman-dl not found at {RMAN_DL}")
    cmd=[str(RMAN_DL)]
    if langs:
        cmd+=["-l",langs]
    if file_filter:
        cmd+=["-p",file_filter]
    if mode=="archive":
        cmd+=["--cache-readonly"]
        cache_path=ARCHIVE_DIR/project/"bundles"/f"{project}.bundle"
        cache_path.parent.mkdir(parents=True,exist_ok=True)
        cmd+=["--cache",str(cache_path)]
    else:
        cmd+=["--cdn",f"https://{project}.secure.dyn.riotcdn.net/channels/public"]
        cache_path=CACHE_DIR/project/"bundles"/f"{project}-cache.bundle"
        cache_path.parent.mkdir(parents=True,exist_ok=True)
        cmd+=["--cache",str(cache_path)]
    cmd+=[str(manifest_path),str(outdir)]
    if multithreaded:
        try:
            j_val=int(jobs) if jobs is not None else RMAN_DL_JOBS
        except Exception:
            j_val=RMAN_DL_JOBS
        try:
            c_val=int(cdn_workers) if cdn_workers is not None else RMAN_DL_CDN_WORKERS
        except Exception:
            c_val=RMAN_DL_CDN_WORKERS
        cmd+=["--jobs",str(j_val),"--cdn-workers",str(c_val)]
    proc=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    return proc

def run_rman_ls_cmd(manifest_path:Path,filter_lang=None,filter_path=None,fmt=None,timeout=30):
    if not RMAN_LS.exists():
        return None
    cmd=[str(RMAN_LS)]
    if fmt:
        cmd+=["--format",fmt]
    if filter_lang:
        cmd+=["-l",filter_lang]
    if filter_path:
        cmd+=["-p",filter_path]
    cmd+=[str(manifest_path)]
    try:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        out,err=proc.communicate(timeout=timeout)
        if proc.returncode!=0:
            return None
        lines=[ln.strip() for ln in out.splitlines() if ln.strip()]
        return lines
    except Exception:
        return None

def compute_manifest_size_from_metadata(project,manifest_id,selected_langs=None,file_filter_regex=None):
    base=CACHE_DIR
    meta=base/project/"metadata"/f"{manifest_id}.txt"
    if not meta.exists():
        return None
    try:
        text=meta.read_text(encoding="utf-8")
    except Exception:
        return None
    selected_set=None
    if selected_langs:
        if isinstance(selected_langs,str):
            toks=[t.strip() for t in selected_langs.split("|") if t.strip()]
        else:
            toks=[t.strip() for t in selected_langs if isinstance(t,str) and t.strip()]
        if toks:
            selected_set={t.lower() for t in toks}
    file_re=None
    if file_filter_regex:
        try:
            file_re=re.compile(file_filter_regex,re.IGNORECASE)
        except re.error:
            file_re=None
    total=0
    for ln in text.splitlines():
        ln=ln.strip()
        if not ln:
            continue
        parts=ln.rsplit(",",3)
        if len(parts)==4:
            path_field=parts[0].strip()
            size_field=parts[1].strip()
            langs_field=parts[3].strip()
        else:
            parts2=ln.rsplit(",",1)
            if len(parts2)!=2:
                continue
            rest,lang_field=parts2
            rest_parts=rest.rsplit(",",1)
            if len(rest_parts)!=2:
                continue
            path_field=rest_parts[0].strip()
            size_field=rest_parts[1].strip()
            langs_field=lang_field.strip()
        if file_re and not file_re.search(path_field):
            continue
        try:
            size_val=int(size_field)
        except Exception:
            continue
        if selected_set:
            if not langs_field:
                lang_tokens=["none"]
            else:
                lang_tokens=[t.strip() for t in re.split(r'[;,\|,]',langs_field) if t and t.strip()]
                if not lang_tokens:
                    lang_tokens=["none"]
            lang_tokens_lc={t.lower() for t in lang_tokens}
            if lang_tokens_lc.isdisjoint(selected_set):
                continue
        total+=size_val
    return total

class DownloadManagerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Download Manager")
        self.geometry("1200x760")
        self.minsize(900,520)
        self.catalog={}
        self.prefs=load_prefs()
        self.current_mode="download"
        self.selected_project=None
        self.filtered_entries=[]
        self.sort_state={"col":"Timestamp","reverse":True}
        self.marked={}
        self.page_size_options=[100,500,1000,"All"]
        self.page_size=tk.StringVar(value=str(self.prefs.get("page_size",100)))
        self.current_page=1
        self.total_pages=1
        self._preserve_selection=None
        self.running_procs=[]
        self.multithread_var=tk.BooleanVar(value=self.prefs.get("multithreaded",False))
        self._abort_all_requested=False
        self._abort_current_requested=False
        self._notes_save_after_id=None
        self._build_ui()
        self._load_window_prefs()
        self._load_catalog_into_ui()
        self.bind("<Configure>",self._on_window_resize)
        self.protocol("WM_DELETE_WINDOW",self._on_close)

    def _build_ui(self):
        top_toolbar=ttk.Frame(self)
        top_toolbar.pack(side=tk.TOP,fill=tk.X)
        self.update_btn=ttk.Button(top_toolbar,text="Update Catalog & Tools",command=self._on_update_catalog)
        self.update_btn.pack(side=tk.LEFT,padx=4,pady=4)
        ttk.Button(top_toolbar,text="Credits",command=self._on_credits).pack(side=tk.LEFT,padx=4,pady=4)
        ttk.Label(top_toolbar,text="Mode:").pack(side=tk.LEFT,padx=(10,2))
        self.mode_var=tk.StringVar(value="download")
        mode_combo=ttk.Combobox(top_toolbar,textvariable=self.mode_var,values=["download","archive"],state="readonly",width=10)
        mode_combo.pack(side=tk.LEFT,padx=2)
        mode_combo.bind("<<ComboboxSelected>>",self._on_mode_change)
        ttk.Button(top_toolbar,text="Select All",command=self._select_all_filtered).pack(side=tk.LEFT,padx=6)
        ttk.Button(top_toolbar,text="Clear Selections",command=self._clear_selections).pack(side=tk.LEFT,padx=6)
        ttk.Button(top_toolbar,text="Download Selected",command=self._on_run_rman_dl).pack(side=tk.LEFT,padx=6)
        ttk.Button(top_toolbar,text="Abort (Current)",command=self._abort_current_proc).pack(side=tk.LEFT,padx=6)
        ttk.Button(top_toolbar,text="Abort (All)",command=self._abort_all_procs).pack(side=tk.LEFT,padx=6)
        ttk.Checkbutton(top_toolbar,text="Multithreaded",variable=self.multithread_var).pack(side=tk.LEFT,padx=6)

        self.main_pane=ttk.PanedWindow(self,orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH,expand=True)

        left_frame=ttk.Frame(self.main_pane,width=200)
        self.main_pane.add(left_frame,weight=1)
        mid_frame=ttk.Frame(self.main_pane)
        self.main_pane.add(mid_frame,weight=3)
        right_frame=ttk.Frame(self.main_pane,width=320)
        self.main_pane.add(right_frame,weight=2)

        ttk.Label(left_frame,text="Projects").pack(anchor=tk.W,padx=6,pady=(6,0))
        proj_frame=ttk.Frame(left_frame)
        proj_frame.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        self.project_listbox=tk.Listbox(proj_frame,exportselection=False)
        self.project_listbox.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        self.project_listbox.bind("<<ListboxSelect>>",lambda e:self._on_project_select())
        proj_scroll=ttk.Scrollbar(proj_frame,orient=tk.VERTICAL,command=self.project_listbox.yview)
        proj_scroll.pack(side=tk.RIGHT,fill=tk.Y)
        self.project_listbox.config(yscrollcommand=proj_scroll.set)

        mid_top=ttk.Frame(mid_frame)
        mid_top.pack(fill=tk.X,padx=6,pady=(6,0))

        fframe2=ttk.Frame(mid_top)
        fframe2.pack(fill=tk.X,pady=(0,4))

        ttk.Label(fframe2,text="Version").grid(row=0,column=0,padx=2)
        self.filter_version=tk.StringVar()
        v_entry=ttk.Entry(fframe2,textvariable=self.filter_version,width=12)
        v_entry.grid(row=1,column=0,padx=2)
        self.filter_version.trace_add("write",lambda *a:self._on_filter_change())

        ttk.Label(fframe2,text="Year").grid(row=0,column=1,padx=2)
        self.filter_year=tk.StringVar()
        y_entry=ttk.Entry(fframe2,textvariable=self.filter_year,width=8)
        y_entry.grid(row=1,column=1,padx=2)
        self.filter_year.trace_add("write",lambda *a:self._on_filter_change())
        ttk.Button(fframe2,text="...",width=2,command=self._open_year_popup).grid(row=1,column=2,padx=2)

        ttk.Label(fframe2,text="Size").grid(row=0,column=3,padx=2)
        self.filter_size=tk.StringVar()
        s_entry=ttk.Entry(fframe2,textvariable=self.filter_size,width=10)
        s_entry.grid(row=1,column=3,padx=2)
        self.filter_size.trace_add("write",lambda *a:self._on_filter_change())

        ttk.Label(fframe2,text="Platform(s)").grid(row=0,column=4,padx=2)
        self.filter_platform=tk.StringVar()
        p_entry=ttk.Entry(fframe2,textvariable=self.filter_platform,width=14)
        p_entry.grid(row=1,column=4,padx=2)
        self.filter_platform.trace_add("write",lambda *a:self._on_filter_change())
        ttk.Button(fframe2,text="...",width=2,command=self._open_platform_popup).grid(row=1,column=5,padx=2)

        ttk.Label(fframe2,text="Realms").grid(row=0,column=6,padx=2)
        self.filter_realms=tk.StringVar()
        r_entry=ttk.Entry(fframe2,textvariable=self.filter_realms,width=14)
        r_entry.grid(row=1,column=6,padx=2)
        self.filter_realms.trace_add("write",lambda *a:self._on_filter_change())
        ttk.Button(fframe2,text="...",width=2,command=self._open_realms_popup).grid(row=1,column=7,padx=2)

        ttk.Label(fframe2,text="Artifact").grid(row=0,column=8,padx=2)
        self.filter_artifact=tk.StringVar()
        a_entry=ttk.Entry(fframe2,textvariable=self.filter_artifact,width=12)
        a_entry.grid(row=1,column=8,padx=2)
        self.filter_artifact.trace_add("write",lambda *a:self._on_filter_change())
        ttk.Button(fframe2,text="...",width=2,command=self._open_artifact_popup).grid(row=1,column=9,padx=2)

        page_controls_frame=ttk.Frame(fframe2)
        page_controls_frame.grid(row=0,column=10,rowspan=2,padx=(12,0),sticky=tk.E)
        ttk.Label(page_controls_frame,text="Page size:").pack(side=tk.LEFT)
        page_combo=ttk.Combobox(page_controls_frame,textvariable=self.page_size,values=[str(x) for x in self.page_size_options],width=6,state="readonly")
        page_combo.pack(side=tk.LEFT,padx=4)
        page_combo.bind("<<ComboboxSelected>>",lambda e:self._on_page_size_change())
        ttk.Button(page_controls_frame,text="Prev",command=self._prev_page).pack(side=tk.LEFT,padx=4)
        ttk.Button(page_controls_frame,text="Next",command=self._next_page).pack(side=tk.LEFT,padx=4)
        self.page_entry=ttk.Entry(page_controls_frame,width=8)
        self.page_entry.pack(side=tk.LEFT,padx=(6,0))
        self.page_entry.bind("<Return>",lambda e:self._goto_page())

        ttk.Label(mid_frame,text="Entries").pack(anchor=tk.W,padx=6,pady=(0,0))
        cols=("Download","ManifestID","Version","Timestamp","Size","Platform","Realms","ArtifactType")
        tree_frame=ttk.Frame(mid_frame)
        tree_frame.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        self.tree=ttk.Treeview(tree_frame,columns=cols,show="headings",selectmode="extended")
        self.tree.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        tree_v=ttk.Scrollbar(tree_frame,orient=tk.VERTICAL,command=self.tree.yview)
        tree_v.pack(side=tk.RIGHT,fill=tk.Y)
        tree_h=ttk.Scrollbar(mid_frame,orient=tk.HORIZONTAL,command=self.tree.xview)
        tree_h.pack(fill=tk.X,padx=6)
        self.tree.config(yscrollcommand=tree_v.set,xscrollcommand=tree_h.set)
        self._col_min_widths={
            "Download":60,"ManifestID":140,"Version":140,"Timestamp":160,"Size":90,"Platform":140,"Realms":140,"ArtifactType":120,
        }
        for c in cols:
            self.tree.heading(c,text=c,command=lambda _c=c:self._on_column_click(_c))
            self.tree.column(c,width=self._col_min_widths.get(c,100),anchor=tk.W,minwidth=self._col_min_widths.get(c,80))
        self.tree.bind("<<TreeviewSelect>>",lambda e:self._on_entry_select())
        self.tree.bind("<Button-1>",self._on_tree_click,add="+")

        status_frame=ttk.Frame(mid_frame)
        status_frame.pack(fill=tk.BOTH,padx=6,pady=(0,6))
        ttk.Label(status_frame,text="Status / Log:").pack(anchor=tk.W)
        log_frame=ttk.Frame(status_frame)
        log_frame.pack(fill=tk.BOTH,expand=True)
        self.log_text=tk.Text(log_frame,height=8,wrap=tk.NONE)
        self.log_text.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        log_v=ttk.Scrollbar(log_frame,orient=tk.VERTICAL,command=self.log_text.yview)
        log_v.pack(side=tk.RIGHT,fill=tk.Y)
        log_h=ttk.Scrollbar(status_frame,orient=tk.HORIZONTAL,command=self.log_text.xview)
        log_h.pack(fill=tk.X)
        self.log_text.config(yscrollcommand=log_v.set,xscrollcommand=log_h.set)

        cache_info_frame=ttk.Frame(right_frame)
        cache_info_frame.pack(fill=tk.X,padx=6,pady=(6,0))
        ttk.Label(cache_info_frame,text="Cache Info").grid(row=0,column=0,sticky=tk.W)
        self.cache_count_var=tk.StringVar(value="Manifests: 0")
        self.cache_size_var=tk.StringVar(value="Cache size: 0 B")
        self.cache_bundle_var=tk.StringVar(value="Bundle: (none)")
        ttk.Label(cache_info_frame,textvariable=self.cache_count_var).grid(row=1,column=0,sticky=tk.W,padx=(0,4))
        ttk.Label(cache_info_frame,textvariable=self.cache_size_var).grid(row=1,column=1,sticky=tk.W,padx=(0,4))
        ttk.Label(cache_info_frame,textvariable=self.cache_bundle_var).grid(row=1,column=2,sticky=tk.W,padx=(0,4))
        btn_frame=ttk.Frame(cache_info_frame)
        btn_frame.grid(row=2,column=0,columnspan=3,pady=(6,0),sticky=tk.W)
        ttk.Button(btn_frame,text="Refresh Cache Info",command=self._refresh_cache_info).pack(side=tk.LEFT,padx=4)
        ttk.Button(btn_frame,text="Clear Cache (project)",command=self._clear_cache_for_project).pack(side=tk.LEFT,padx=4)

        ttk.Label(right_frame,text="Notes").pack(anchor=tk.W,padx=6,pady=(6,0))
        details_frame=ttk.Frame(right_frame)
        details_frame.pack(fill=tk.BOTH,expand=True,padx=6,pady=6)
        self.notes_text=tk.Text(details_frame,height=20,wrap=tk.WORD,undo=True)
        self.notes_text.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        det_v=ttk.Scrollbar(details_frame,orient=tk.VERTICAL,command=self.notes_text.yview)
        det_v.pack(side=tk.RIGHT,fill=tk.Y)
        self.notes_text.config(yscrollcommand=det_v.set)
        self.notes_text.bind("<<Modified>>",self._on_notes_modified)

        self.status_var=tk.StringVar(value="Ready")
        status=ttk.Label(self,textvariable=self.status_var,relief=tk.SUNKEN,anchor=tk.W)
        status.pack(side=tk.BOTTOM,fill=tk.X)

        self._font=tkfont.nametofont("TkDefaultFont")
        self._char_width=max(self._font.measure("0"),6)

        self.tree.tag_configure("marked",background="#fff2cc")
        self.tree.tag_configure("incache",background="#f0f0f0")

    def _log(self,text):
        self.log_text.insert(tk.END,text+"\n")
        self.log_text.see(tk.END)
        self._set_status(text)

    def _set_status(self,text):
        self.status_var.set(text)

    def _on_mode_change(self,*_):
        self.current_mode=self.mode_var.get()

    def _on_update_catalog(self):
        popup=tk.Toplevel(self)
        popup.transient(self)
        popup.grab_set()
        popup.title("Updating Catalog & Tools")
        popup.geometry("600x520")
        txt=tk.Text(popup,wrap=tk.WORD)
        txt.pack(fill=tk.BOTH,expand=True,padx=8,pady=8)
        close_btn=ttk.Button(popup,text="Close",state=tk.DISABLED,command=popup.destroy)
        close_btn.pack(pady=(0,8))
        def append(s):
            txt.insert(tk.END,s+"\n"); txt.see(tk.END)
        def worker():
            append("Starting update...")
            ok=download_tools_and_catalog(progress_callback=lambda s: append(s))
            if ok:
                append("Update completed successfully.")
            else:
                append("Update finished with warnings or errors.")
            append("Reloading catalog...")
            self.after(100,self._load_catalog_into_ui)
            append("Done.")
            close_btn.config(state=tk.NORMAL)
        threading.Thread(target=worker,daemon=True).start()

    def _on_credits(self):
        popup=tk.Toplevel(self)
        popup.transient(self); popup.grab_set(); popup.title("Credits")
        popup.geometry("600x520")
        txt=tk.Text(popup,wrap=tk.WORD)
        txt.pack(fill=tk.BOTH,expand=True,padx=8,pady=8)
        credits_text=(
"This downloader script was created and maintained by:\n"
"  PixelButts\n"
"  - https://x.com/PixelButts\n"
"  - https://bsky.app/profile/pixel-butts.bsky.social\n\n"
"To leave feedback or report a bug:\n"
"  - https://github.com/RiotArchiveProject/catalog-download-script\n"
)
        txt.insert("1.0",credits_text)
        txt.config(state=tk.DISABLED)
        btns=ttk.Frame(popup); btns.pack(pady=6)
        ttk.Button(btns,text="Close",command=popup.destroy).pack(side=tk.LEFT,padx=6)

    def _load_catalog_into_ui(self):
        self.catalog=load_catalog()
        projects=sorted(self.catalog.keys())
        self.project_listbox.delete(0,tk.END)
        for p in projects:
            self.project_listbox.insert(tk.END,p)
        if projects:
            cur=self.selected_project
            if cur and cur in projects:
                idx=projects.index(cur)
                self.project_listbox.selection_clear(0,tk.END)
                self.project_listbox.selection_set(idx)
                self.project_listbox.see(idx)
                self._on_project_select()
                return
            self.project_listbox.selection_set(0)
            self._on_project_select()

    def _on_project_select(self):
        sel=self.project_listbox.curselection()
        if not sel:
            return
        idx=sel[0]
        project=self.project_listbox.get(idx)
        self.selected_project=project
        proj_prefs=self.prefs.get(project,{})
        if proj_prefs:
            self.filter_version.set(proj_prefs.get("version",""))
            self.filter_year.set(proj_prefs.get("year",""))
            self.filter_size.set(proj_prefs.get("size",""))
            self.filter_platform.set(proj_prefs.get("platform",""))
            self.filter_realms.set(proj_prefs.get("realms",""))
            self.filter_artifact.set(proj_prefs.get("artifact",""))
        else:
            self.filter_version.set("")
            self.filter_year.set("")
            self.filter_size.set("")
            self.filter_platform.set("")
            self.filter_realms.set("")
            self.filter_artifact.set("")
        self.marked.setdefault(project,set())
        self.current_page=1
        self._apply_filter()
        self._refresh_cache_info()
        self._load_project_notes()

    def _populate_page(self):
        prev_sel=self._preserve_selection or set()
        self._preserve_selection=None
        self.tree.delete(*self.tree.get_children())
        if not self.filtered_entries:
            try:
                self.page_entry.delete(0,tk.END)
                self.page_entry.insert(0,"0/0")
            except Exception:
                pass
            return
        ps=self.page_size.get()
        if ps=="All":
            page_items=self.filtered_entries
            self.total_pages=1
            self.current_page=1
        else:
            try:
                ps_int=int(ps)
            except Exception:
                ps_int=100
            total=len(self.filtered_entries)
            self.total_pages=max(1,(total+ps_int-1)//ps_int)
            if self.current_page<1:
                self.current_page=1
            if self.current_page>self.total_pages:
                self.current_page=self.total_pages
            start=(self.current_page-1)*ps_int
            end=start+ps_int
            page_items=self.filtered_entries[start:end]
        for mid,e in page_items:
            incache=(CACHE_DIR/self.selected_project/"releases"/f"{mid}.manifest").exists()
            marked_set=self.marked.get(self.selected_project,set())
            checkbox="☑" if mid in marked_set else "☐"
            tags=()
            if incache:
                tags=("incache",)
            if mid in marked_set:
                tags=tuple(set(tags)|{"marked"})
            self.tree.insert("",tk.END,iid=mid,values=(
                checkbox,mid,e.get("version",""),e.get("timestamp",""),human_mb(e.get("size","")),normalize_platform(e),"|".join(e.get("realms",[]) or []),e.get("artifact_type","")
            ),tags=tags)
        if prev_sel:
            to_select=[iid for iid in prev_sel if self.tree.exists(iid)]
            if to_select:
                try:
                    self.tree.selection_set(to_select)
                except Exception:
                    pass
        try:
            self.page_entry.delete(0,tk.END)
            self.page_entry.insert(0,f"{self.current_page}/{self.total_pages}")
        except Exception:
            pass
        self._autosize_columns()

    def _on_filter_change(self):
        if hasattr(self,"_filter_after_id"):
            try:
                self.after_cancel(self._filter_after_id)
            except Exception:
                pass
        self._filter_after_id=self.after(200,self._apply_filter)

    def _apply_filter(self):
        if not self.selected_project:
            return
        entries=list(self.catalog.get(self.selected_project,{}).items())
        patterns={}
        v=self.filter_version.get().strip()
        if v:
            patterns["version"]=v.lower()
        y=self.filter_year.get().strip()
        if y:
            patterns["year"]=y
        s=self.filter_size.get().strip()
        if s:
            patterns["size"]=s
        p=self.filter_platform.get().strip()
        if p:
            patterns["platform"]=[tok.strip().lower() for tok in re.split(r'[,\|;]',p) if tok.strip()]
        r=self.filter_realms.get().strip()
        if r:
            patterns["realms"]=[tok.strip().lower() for tok in re.split(r'[,\|;]',r) if tok.strip()]
        a=self.filter_artifact.get().strip()
        if a:
            patterns["artifact"]=[tok.strip().lower() for tok in re.split(r'[,\|;]',a) if tok.strip()]
        filtered=[]
        for mid,e in entries:
            fields={
                "version":str(e.get("version","")),
                "timestamp":str(e.get("timestamp","")),
                "year":(parse_timestamp(e.get("timestamp","")).year if parse_timestamp(e.get("timestamp","")) else ""),
                "size":human_mb(e.get("size","")),
                "platform":normalize_platform(e),
                "artifact":str(e.get("artifact_type","")),
                "realms":"|".join(e.get("realms",[]) or [])
            }
            ok=True
            if "version" in patterns:
                if not fields["version"].lower().startswith(patterns["version"]):
                    ok=False
            if ok and "year" in patterns:
                if str(fields["year"])!=str(patterns["year"]):
                    ok=False
            if ok and "size" in patterns:
                sval=patterns["size"]
                m=re.match(r'^\s*([<>]=?)\s*([\d\.]+)\s*(GB|MB)?\s*$',sval,re.IGNORECASE)
                if m:
                    op,num,unit=m.groups()
                    num=float(num)
                    if not unit:
                        unit="MB"
                    unit=unit.upper()
                    bytes_threshold=int(num*(1024**2 if unit=="MB" else 1024**3))
                    try:
                        entry_bytes=int(e.get("size",0))
                    except Exception:
                        entry_bytes=0
                    if op==">":
                        if not (entry_bytes>bytes_threshold): ok=False
                    elif op=="<":
                        if not (entry_bytes<bytes_threshold): ok=False
                    elif op==">=":
                        if not (entry_bytes>=bytes_threshold): ok=False
                    elif op=="<=":
                        if not (entry_bytes<=bytes_threshold): ok=False
                else:
                    if sval.lower() not in fields["size"].lower():
                        ok=False
            if ok and "platform" in patterns:
                plats=[p.strip().lower() for p in fields["platform"].split(",") if p.strip()]
                if not any(tok in plats for tok in patterns["platform"]):
                    ok=False
            if ok and "artifact" in patterns:
                if not any(tok in fields["artifact"].lower() for tok in patterns["artifact"]):
                    ok=False
            if ok and "realms" in patterns:
                realm_tokens=[t.strip().lower() for t in re.split(r'[,\|;]',fields["realms"]) if t.strip()]
                if not any(tok in realm_tokens for tok in patterns["realms"]):
                    ok=False
            if ok:
                filtered.append((mid,e))
        col=self.sort_state.get("col","Timestamp")
        rev=self.sort_state.get("reverse",True)
        def sort_key(item):
            mid,ent=item
            if col=="Timestamp":
                dt=parse_timestamp(ent.get("timestamp",""))
                return dt or datetime.min
            if col=="Version":
                return ent.get("version","")
            if col=="Size":
                try:
                    return int(ent.get("size",0))
                except Exception:
                    return 0
            if col=="Platform":
                return normalize_platform(ent)
            if col=="ArtifactType":
                return ent.get("artifact_type","")
            if col=="ManifestID":
                return mid
            if col=="Realms":
                return "|".join(ent.get("realms",[]) or [])
            return ent.get("timestamp","")
        filtered.sort(key=sort_key,reverse=rev)
        self.filtered_entries=filtered
        self.prefs.setdefault(self.selected_project,{})
        self.prefs[self.selected_project].update({
            "version":self.filter_version.get().strip(),
            "year":self.filter_year.get().strip(),
            "size":self.filter_size.get().strip(),
            "platform":self.filter_platform.get().strip(),
            "realms":self.filter_realms.get().strip(),
            "artifact":self.filter_artifact.get().strip(),
        })
        self.prefs["multithreaded"]=self.multithread_var.get()
        self.prefs["page_size"]=self.page_size.get()
        save_prefs(self.prefs)
        self.current_page=1
        self._populate_page()
        self._set_status(f"Filter applied: {len(filtered)} entries")

    def _on_page_size_change(self):
        self.current_page=1
        self._populate_page()

    def _prev_page(self):
        if self.current_page>1:
            self.current_page-=1
            self._populate_page()

    def _next_page(self):
        if self.current_page<self.total_pages:
            self.current_page+=1
            self._populate_page()

    def _goto_page(self):
        txt=self.page_entry.get().strip()
        if "/" in txt:
            try:
                p=int(txt.split("/",1)[0])
            except Exception:
                return
        else:
            try:
                p=int(txt)
            except Exception:
                return
        if p<1:
            p=1
        if p>self.total_pages:
            p=self.total_pages
        self.current_page=p
        self._populate_page()

    def _open_platform_popup(self):
        if not self.selected_project:
            return
        unique_plats=set()
        for _, e in self.catalog.get(self.selected_project,{}).items():
            plat_field = normalize_platform(e)
            for tok in [p.strip() for p in plat_field.split(",") if p.strip()]:
                unique_plats.add(tok)
        values=sorted(unique_plats)
        self._open_multi_choice_popup("Platform(s)",values,self.filter_platform)

    def _open_artifact_popup(self):
        if not self.selected_project:
            return
        values=sorted({(e.get("artifact_type","") or "") for _,e in self.catalog.get(self.selected_project,{}).items()})
        self._open_multi_choice_popup("Artifact Type",values,self.filter_artifact)

    def _open_realms_popup(self):
        if not self.selected_project:
            return
        values=sorted({r for _,e in self.catalog.get(self.selected_project,{}).items() for r in (e.get("realms",[]) or [])})
        self._open_multi_choice_popup("Realms",values,self.filter_realms)

    def _open_year_popup(self):
        if not self.selected_project:
            return
        years=set()
        for _,e in self.catalog.get(self.selected_project,{}).items():
            dt=parse_timestamp(e.get("timestamp",""))
            if dt:
                years.add(str(dt.year))
        self._open_multi_choice_popup("Year",sorted(years),self.filter_year,single_choice=True)

    def _open_multi_choice_popup(self,title,values,target_var,single_choice=False):
        popup=tk.Toplevel(self)
        popup.transient(self); popup.grab_set(); popup.title(title)
        popup.geometry("600x520")
        frame=ttk.Frame(popup); frame.pack(fill=tk.BOTH,expand=True,padx=8,pady=8)
        canvas=tk.Canvas(frame); canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        vsb=ttk.Scrollbar(frame,orient=tk.VERTICAL,command=canvas.yview); vsb.pack(side=tk.RIGHT,fill=tk.Y)
        canvas.configure(yscrollcommand=vsb.set)
        inner=ttk.Frame(canvas); canvas.create_window((0,0),window=inner,anchor="nw")
        def on_config(e): canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>",on_config)
        vars={}
        cols=3
        for i,val in enumerate(values):
            var=tk.BooleanVar(value=False)
            chk=ttk.Checkbutton(inner,text=val,variable=var)
            r=i//cols; c=i%cols
            chk.grid(row=r,column=c,sticky=tk.W,padx=6,pady=2)
            vars[val]=var
        if single_choice:
            def on_chk_click(vname):
                for k in vars:
                    vars[k].set(k==vname)
            for k in vars:
                for child in inner.grid_slaves():
                    if isinstance(child,ttk.Checkbutton) and child.cget("text")==k:
                        child.config(command=lambda name=k:on_chk_click(name))
                        break
        def on_apply():
            sel=[k for k,v in vars.items() if v.get()]
            if single_choice:
                target_var.set(sel[0] if sel else "")
            else:
                target_var.set(",".join(sel))
            popup.destroy()
        btns=ttk.Frame(popup); btns.pack(pady=6)
        ttk.Button(btns,text="Apply",command=on_apply).pack(side=tk.LEFT,padx=6)
        ttk.Button(btns,text="Cancel",command=popup.destroy).pack(side=tk.LEFT,padx=6)

    def _on_tree_click(self,event):
        region=self.tree.identify("region",event.x,event.y)
        if region!="cell":
            return
        col=self.tree.identify_column(event.x)
        row=self.tree.identify_row(event.y)
        if not row:
            return
        if col=="#1":
            project=self.selected_project
            if project is None:
                return
            marked_set=self.marked.setdefault(project,set())
            if row in marked_set:
                marked_set.remove(row)
                self.tree.set(row,"Download","☐")
                tags=set(self.tree.item(row,"tags")); tags.discard("marked"); self.tree.item(row,tags=tuple(tags))
                self._log(f"Unmarked {row} for download.")
            else:
                marked_set.add(row)
                self.tree.set(row,"Download","☑")
                tags=set(self.tree.item(row,"tags")); tags.add("marked"); self.tree.item(row,tags=tuple(tags))
                self._log(f"Marked {row} for download.")
            return

    def _on_entry_select(self):
        sel=self.tree.selection()
        if not sel:
            self._load_project_notes()
            return
        self._load_project_notes()

    def _load_project_notes(self):
        try:
            self.notes_text.delete("1.0",tk.END)
            if self.selected_project:
                proj_prefs=self.prefs.get(self.selected_project,{})
                notes=proj_prefs.get("notes","")
                if notes is None:
                    notes=""
                self.notes_text.insert("1.0",notes)
            self.notes_text.edit_modified(False)
        except Exception:
            pass

    def _on_notes_modified(self,event=None):
        try:
            if not self.notes_text.edit_modified():
                return
        except Exception:
            return
        try:
            self.notes_text.edit_modified(False)
        except Exception:
            pass
        if self._notes_save_after_id:
            try:
                self.after_cancel(self._notes_save_after_id)
            except Exception:
                pass
        self._notes_save_after_id=self.after(500,self._save_project_notes)

    def _save_project_notes(self):
        self._notes_save_after_id=None
        if not self.selected_project:
            return
        try:
            notes=self.notes_text.get("1.0",tk.END).rstrip("\n")
            self.prefs.setdefault(self.selected_project,{})
            self.prefs[self.selected_project]["notes"]=notes
            self.prefs["multithreaded"]=self.multithread_var.get()
            self.prefs["page_size"]=self.page_size.get()
            save_prefs(self.prefs)
            self._log(f"Notes saved for project {self.selected_project}.")
        except Exception as ex:
            self._log(f"[Error] Failed to save notes: {ex}")

    def _select_all_filtered(self):
        project=self.selected_project
        if not project:
            return
        mids=[mid for mid,_ in self.filtered_entries]
        marked_set=self.marked.setdefault(project,set())
        for mid in mids:
            marked_set.add(mid)
        self._preserve_selection=set(mids)
        self._populate_page()
        self._log(f"Selected {len(mids)} manifests for download (all filtered).")

    def _clear_selections(self):
        project=self.selected_project
        if not project:
            return
        self.marked.setdefault(project,set()).clear()
        self._preserve_selection=set()
        self._populate_page()
        self._log("Cleared all in-memory selections for current project.")

    def _gather_languages_for_manifests(self,project,mids,dest_base):
        langs=set()
        for mid in mids:
            meta=CACHE_DIR/project/"metadata"/f"{mid}.txt"
            if not meta.exists():
                mpath=dest_base/project/"releases"/f"{mid}.manifest"
                if not mpath.exists():
                    mpath=download_manifest(project,mid,dest_base=dest_base)
                if mpath and mpath.exists() and RMAN_LS.exists():
                    lines=run_rman_ls_cmd(mpath)
                    if lines:
                        meta.parent.mkdir(parents=True,exist_ok=True)
                        meta.write_text("\n".join(lines),encoding="utf-8")
            if meta.exists():
                try:
                    text=meta.read_text(encoding="utf-8")
                except Exception:
                    continue
                for ln in text.splitlines():
                    parts=ln.rsplit(",",1)
                    if len(parts)==2:
                        lang_field=parts[1].strip()
                        for p in re.split(r'[;,\|]',lang_field):
                            p=p.strip()
                            if p:
                                langs.add(p)
        if not langs:
            langs.add("none")
        return sorted(langs)

    def _open_language_selector(self,project,mids,dest_base):
        langs=self._gather_languages_for_manifests(project,mids,dest_base)
        popup=tk.Toplevel(self)
        popup.transient(self); popup.grab_set(); popup.title("Language selection")
        popup.geometry("600x520")
        frame=ttk.Frame(popup); frame.pack(fill=tk.BOTH,expand=True,padx=8,pady=8)
        canvas=tk.Canvas(frame); canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        vsb=ttk.Scrollbar(frame,orient=tk.VERTICAL,command=canvas.yview); vsb.pack(side=tk.RIGHT,fill=tk.Y)
        canvas.configure(yscrollcommand=vsb.set)
        inner=ttk.Frame(canvas); canvas.create_window((0,0),window=inner,anchor="nw")
        def on_config(e): canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>",on_config)
        vars={}
        cols=3
        for i,val in enumerate(langs):
            var=tk.BooleanVar(value=False)
            chk=ttk.Checkbutton(inner,text=val,variable=var)
            r=i//cols; c=i%cols
            chk.grid(row=r,column=c,sticky=tk.W,padx=6,pady=2)
            vars[val]=var
        entry_var=tk.StringVar()
        entry=ttk.Entry(popup,textvariable=entry_var,width=60)
        entry.pack(fill=tk.X,padx=8,pady=(0,6))
        def sync_from_checkboxes():
            sel=[k for k,v in vars.items() if v.get()]
            entry_var.set("|".join(sel))
        def sync_from_entry(*_):
            txt=entry_var.get().strip()
            toks=[t.strip() for t in txt.split("|") if t.strip()]
            for k in vars:
                vars[k].set(k in toks)
        for v in vars.values():
            v.trace_add("write",lambda *a:sync_from_checkboxes())
        entry_var.trace_add("write",sync_from_entry)
        btns=ttk.Frame(popup); btns.pack(pady=6)
        ttk.Button(btns,text="Apply",command=lambda:popup.destroy()).pack(side=tk.LEFT,padx=6)
        ttk.Button(btns,text="Cancel",command=lambda:(entry_var.set(""),popup.destroy())).pack(side=tk.LEFT,padx=6)
        self.wait_window(popup)
        return entry_var.get().strip()

    def _on_run_rman_dl(self):
        project=self.selected_project
        if project is None:
            return
        marked_set=self.marked.get(project,set())
        if marked_set:
            mids=list(marked_set)
        else:
            sel=self.tree.selection()
            if not sel:
                messagebox.showinfo("No selection","Select one or more entries or mark them with the checkbox in the first column.")
                return
            mids=list(sel)
        mode=self.current_mode
        dest_base=ARCHIVE_DIR if mode=="archive" else CACHE_DIR
        self._preserve_selection=set(mids)
        lang_input=self._open_language_selector(project,mids,dest_base)
        if lang_input is None:
            return
        file_filter=simple_input_dialog(self,"File path regex filter (leave blank for all):")
        if file_filter is None:
            return
        multithreaded=self.multithread_var.get()
        self._abort_all_requested=False
        self._abort_current_requested=False

        def worker():
            self._log("Estimating sizes (using metadata / rman-ls where available)...")
            per=[]
            total=0
            missing=[]
            for mid in mids:
                size=compute_manifest_size_from_metadata(project,mid,selected_langs=lang_input or None,file_filter_regex=file_filter or None)
                if size is None:
                    mpath=dest_base/project/"releases"/f"{mid}.manifest"
                    if not mpath.exists():
                        self._log(f"Downloading manifest {mid} for size estimation...")
                        mpath=download_manifest(project,mid,dest_base=dest_base)
                    if mpath and mpath.exists() and RMAN_LS.exists():
                        lines=run_rman_ls_cmd(mpath,filter_lang=lang_input or None,filter_path=file_filter or None)
                        if lines:
                            meta_dir=CACHE_DIR/project/"metadata"
                            meta_dir.mkdir(parents=True,exist_ok=True)
                            (meta_dir/f"{mid}.txt").write_text("\n".join(lines),encoding="utf-8")
                            size=compute_manifest_size_from_metadata(project,mid,selected_langs=lang_input or None,file_filter_regex=file_filter or None)
                if size is None:
                    per.append((mid,None)); missing.append(mid)
                else:
                    per.append((mid,size)); total+=size
            lines=[]
            for mid,sz in per:
                if sz is None:
                    lines.append(f"{mid}: size unknown (metadata missing)")
                else:
                    lines.append(f"{mid}: {human_readable_bytes(sz)} ({sz} bytes)")
            total_line = f"Total estimated: {human_readable_bytes(total)} ({total} bytes)"

            if len(mids) > 10:
                display_text = f"{len(mids)} manifests selected.\n\n{total_line}\n\nNote: Detailed per-manifest sizes are available in the log."
            else:
                display_text = "\n".join(lines) + "\n\n" + total_line
                if missing:
                    display_text += "\n\nNote: Some manifests had missing metadata and were excluded from the estimate."

            confirm = messagebox.askyesno("Confirm rman-dl", display_text + "\n\nProceed to run rman-dl for these manifests?")
            if not confirm:
                self._log("rman-dl cancelled by user.")
                return
            self._log("Starting rman-dl processes (sequential, one manifest at a time)...")
            for mid in mids:
                if self._abort_all_requested:
                    self._log("Abort (All) requested; stopping queued rman-dl jobs.")
                    break
                mpath=dest_base/project/"releases"/f"{mid}.manifest"
                if not mpath.exists():
                    self._log(f"Downloading manifest {mid} before rman-dl...")
                    mpath=download_manifest(project,mid,dest_base=dest_base)
                    if not mpath:
                        self._log(f"[Warn] Manifest {mid} not found; skipping rman-dl.")
                        continue
                entry=self.catalog.get(project,{}).get(mid,{})
                version=sanitize_version(entry.get("version","unknown"))
                artifact_type=sanitize_artifact(entry.get("artifact_type","unknown"))
                base=f"{project}-{version}-{artifact_type}-{mid}"
                outdir=BUILDS_DIR/project/base
                outdir.mkdir(parents=True,exist_ok=True)
                try:
                    self._log(f"Starting rman-dl for {mid} (multithreaded={multithreaded})...")
                    proc=run_rman_dl_cmd(project,mpath,outdir,langs=lang_input or None,file_filter=file_filter or None,mode=mode,multithreaded=multithreaded)
                    self.running_procs.append(proc)
                    self._stream_proc_to_log(proc,mid)
                    while True:
                        if self._abort_current_requested:
                            try:
                                if os.name=="nt":
                                    proc.terminate()
                                else:
                                    os.kill(proc.pid,signal.SIGTERM)
                                self._log(f"Abort (Current) requested; terminated pid {getattr(proc,'pid',None)}")
                            except Exception as ex:
                                self._log(f"Failed to terminate current pid {getattr(proc,'pid',None)}: {ex}")
                            self._abort_current_requested=False
                        if self._abort_all_requested:
                            try:
                                if os.name=="nt":
                                    proc.terminate()
                                else:
                                    os.kill(proc.pid,signal.SIGTERM)
                                self._log(f"Abort (All) requested; terminated pid {getattr(proc,'pid',None)}")
                            except Exception as ex:
                                self._log(f"Failed to terminate pid {getattr(proc,'pid',None)}: {ex}")
                            break
                        ret = proc.poll()
                        if ret is not None:
                            break
                        time.sleep(0.2)
                    try:
                        rc=proc.wait(timeout=1)
                    except Exception:
                        rc=proc.returncode
                    self._log(f"rman-dl finished for {mid} with exit code {proc.returncode}")
                except FileNotFoundError as ex:
                    self._log(f"[Error] {ex}")
                    messagebox.showerror("rman-dl missing",str(ex))
                    return
                except Exception as ex:
                    self._log(f"[Error] rman-dl failed for {mid}: {ex}")
            self._log("All rman-dl jobs completed or aborted.")
            self._abort_all_requested=False
            self._abort_current_requested=False

        threading.Thread(target=worker,daemon=True).start()

    def _stream_proc_to_log(self,proc,mid):
        def reader():
            try:
                for line in proc.stdout:
                    self._log(f"[{mid}] {line.rstrip()}")
                proc.wait()
                self._log(f"[{mid}] Process exited with code {proc.returncode}")
            except Exception as ex:
                self._log(f"[{mid}] Error reading process output: {ex}")
            finally:
                try:
                    self.running_procs.remove(proc)
                except Exception:
                    pass
                self.after(200,lambda:(self._refresh_cache_info(),self._apply_filter()))
        threading.Thread(target=reader,daemon=True).start()

    def _abort_current_proc(self):
        if not self.running_procs:
            self._log("No running rman-dl processes to abort (current).")
            return
        self._abort_current_requested=True
        self._log("Abort (Current) requested; attempting to terminate current process.")

    def _abort_all_procs(self):
        if not self.running_procs and not self._is_worker_running():
            self._log("No running rman-dl processes to abort (all).")
            return
        ok=messagebox.askyesno("Abort downloads","Terminate all running and queued rman-dl processes?")
        if not ok:
            return
        self._abort_all_requested=True
        for proc in list(self.running_procs):
            try:
                if os.name=="nt":
                    proc.terminate()
                else:
                    os.kill(proc.pid,signal.SIGTERM)
                self._log(f"Sent terminate to pid {proc.pid}")
            except Exception as ex:
                self._log(f"Failed to terminate pid {getattr(proc,'pid',None)}: {ex}")
        self._log("Abort (All) requested; terminating running processes and preventing queued jobs.")

    def _is_worker_running(self):
        return bool(self.running_procs)

    def _open_builds_folder(self):
        path=BUILDS_DIR
        path.mkdir(parents=True,exist_ok=True)
        if os.name=="nt":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open",str(path)])

    def _compute_cache_info(self,project):
        base=CACHE_DIR/project
        manifest_count=0
        total_bytes=0
        bundle_exists=False
        if base.exists():
            for p in base.rglob("*.manifest"):
                manifest_count+=1
            for f in base.rglob("*"):
                if f.is_file():
                    try:
                        total_bytes+=f.stat().st_size
                    except Exception:
                        pass
            bundles_dir=base/"bundles"
            if bundles_dir.exists():
                for b in bundles_dir.glob("*.bundle"):
                    bundle_exists=True
                    break
        return manifest_count,total_bytes,bundle_exists

    def _refresh_cache_info(self):
        project=self.selected_project
        if not project:
            self.cache_count_var.set("Manifests: 0")
            self.cache_size_var.set("Cache size: 0 B")
            self.cache_bundle_var.set("Bundle: (none)")
            return
        def worker():
            self._set_status("Refreshing cache info...")
            count,size,bundle=self._compute_cache_info(project)
            self.cache_count_var.set(f"Manifests: {count}")
            self.cache_size_var.set(f"Cache size: {human_mb(size)}")
            self.cache_bundle_var.set(f"Bundle: {'present' if bundle else '(none)'}")
            self._set_status("Cache info updated.")
        threading.Thread(target=worker,daemon=True).start()

    def _clear_cache_for_project(self):
        project=self.selected_project
        if not project:
            return
        ok=messagebox.askyesno("Clear cache",f"Delete cache (manifests, bundles, metadata) for project '{project}'? This cannot be undone.")
        if not ok:
            return
        def worker():
            base=CACHE_DIR/project
            try:
                if base.exists():
                    shutil.rmtree(base)
                self._log(f"Cache cleared for project {project}.")
            except Exception as ex:
                self._log(f"[Error] Failed to clear cache: {ex}")
            self.after(200,lambda:(self._refresh_cache_info(),self._apply_filter()))
        threading.Thread(target=worker,daemon=True).start()

    def _on_column_click(self,col):
        if self.sort_state.get("col")==col:
            self.sort_state["reverse"]=not self.sort_state.get("reverse",False)
        else:
            self.sort_state["col"]=col
            self.sort_state["reverse"]=False if col!="Timestamp" else True
        self._apply_filter()

    def _autosize_columns(self):
        cols=self.tree["columns"]
        for c in cols:
            max_text_len=len(c)
            for i,iid in enumerate(self.tree.get_children()):
                if i>200:
                    break
                val=self.tree.set(iid,c) or ""
                l=len(str(val))
                if l>max_text_len:
                    max_text_len=l
            neww=max(self._col_min_widths.get(c,80),int(max_text_len*self._char_width*0.95)+20)
            try:
                self.tree.column(c,width=neww)
            except Exception:
                pass

    def _on_window_resize(self,event):
        self.after(150,self._autosize_columns)
        # do not save geometry or sash positions here (reverted)

    def _load_window_prefs(self):
        # only restore simple prefs: multithreaded and page_size; do not restore geometry/sashes
        mt=self.prefs.get("multithreaded",False)
        self.multithread_var.set(mt)
        ps=self.prefs.get("page_size",100)
        self.page_size.set(str(ps))

    def _save_window_prefs_debounced(self):
        # only persist minimal prefs
        try:
            self.prefs["multithreaded"]=self.multithread_var.get()
            self.prefs["page_size"]=self.page_size.get()
            save_prefs(self.prefs)
        except Exception:
            pass

    def _on_close(self):
        try:
            if self._notes_save_after_id:
                self.after_cancel(self._notes_save_after_id)
                self._save_project_notes()
            else:
                self._save_project_notes()
        except Exception:
            pass
        try:
            self._save_window_prefs_debounced()
        except Exception:
            pass
        self.destroy()

def simple_input_dialog(parent,prompt):
    dlg=tk.Toplevel(parent)
    dlg.transient(parent); dlg.grab_set(); dlg.title(prompt)
    tk.Label(dlg,text=prompt).pack(padx=8,pady=8)
    var=tk.StringVar()
    entry=ttk.Entry(dlg,textvariable=var,width=60)
    entry.pack(padx=8,pady=4)
    entry.focus_set()
    result={"value":None}
    def on_ok():
        result["value"]=var.get().strip(); dlg.destroy()
    def on_cancel():
        dlg.destroy()
    btns=ttk.Frame(dlg); btns.pack(pady=8)
    ttk.Button(btns,text="OK",command=on_ok).pack(side=tk.LEFT,padx=4)
    ttk.Button(btns,text="Cancel",command=on_cancel).pack(side=tk.LEFT,padx=4)
    parent.wait_window(dlg)
    return result["value"]

if __name__=="__main__":
    app=DownloadManagerGUI()
    app.mainloop()
