#!/usr/bin/env python3
import json, re, subprocess, requests, os, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load_catalog():
    global CATALOG
    catalog_path = ROOT / "catalog.json"
    if catalog_path.exists():
        CATALOG = json.loads(catalog_path.read_text(encoding="utf-8"))
    else:
        CATALOG = {}

CATALOG = {}
load_catalog()

def download_tools():
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    tools = {
        "https://github.com/RiotArchiveProject/catalog-download-script/raw/refs/heads/main/Tools/rman-dl.exe": TOOLS_DIR / "rman-dl.exe",
        "https://github.com/RiotArchiveProject/catalog-download-script/raw/refs/heads/main/Tools/rman-ls.exe": TOOLS_DIR / "rman-ls.exe",
    }

    for url, local_path in tools.items():
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            remote_bytes = r.content
        except Exception as ex:
            print(f"[Error] Failed to download {local_path.name}: {ex}")
            continue

        try:
            if local_path.exists():
                local_bytes = local_path.read_bytes()
                if local_bytes == remote_bytes:
                    print(f"[Info] {local_path.name} is already up to date.")
                    continue
                else:
                    print(f"[Update] New version of {local_path.name} found. Updating...")
            local_path.write_bytes(remote_bytes)
            print(f"[OK] Downloaded {local_path.name}")
        except Exception as ex:
            print(f"[Error] Could not write {local_path.name}: {ex}")

def update_catalog():
    url = "https://raw.githubusercontent.com/RiotArchiveProject/catalog-download-script/refs/heads/main/catalog.json"
    local_path = ROOT / "catalog.json"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        remote_data = r.content
    except Exception as ex:
        print(f"[Error] Failed to fetch remote catalog: {ex}")
        print("[Info] Reloading local catalog instead.")
        load_catalog()
        download_tools()
        return
    if local_path.exists():
        local_data = local_path.read_bytes()
        if local_data == remote_data:
            print("[Info] Catalog is already up to date. Reloading local copy.")
            load_catalog()
            download_tools()
            return
        else:
            print("[Update] New catalog version found. Updating...")
    try:
        local_path.write_bytes(remote_data)
        print("[OK] Catalog updated successfully.")
    except Exception as ex:
        print(f"[Error] Could not write catalog file: {ex}")
        download_tools()
        return
    load_catalog()
    download_tools()

TOOLS_DIR = ROOT / "Tools"
RMAN_DL = TOOLS_DIR / "rman-dl.exe"
RMAN_LS = TOOLS_DIR / "rman-ls.exe"
# Do not change these values due to a bug
RMAN_DL_JOBS = 3
RMAN_DL_CDN_WORKERS = 3

CACHE_DIR = ROOT / "Cache"
ARCHIVE_DIR = ROOT / "Archive"
BUILDS_DIR = ROOT / "Builds"

HELP_KEYS = ("F1",)
PROJECT_HELP_KEYS = ("F2",)
CREDITS_KEYS = ("F3",)

HELP_TEXT = """
================= Downloader Help =================

[General]
  - This script allows you to download current or older revisions of various projects by Riot Games.
  - This will NOT help you run them, but does simplify the process significantly.
  - There will be bugs and issues. If you find any, or want to leave feedback, please check the Credits section.

[Main Menu Selections]
  1) Download Mode                         - browse all known manifests from catalog.json.
  2) Cache Mode                            - browse only manifests you have cached locally.
  3) Archive Mode                          - brows the local archive data if applicable.
  4) Download or Update Catalog and Tools  - update's the catalog.json if applicable.
  0) Exit                                  - quit the program.

[Project Selection]
  - Choose which project (lol, valorant, etc.) you want to browse.
  - Each project has its own manifests, platforms, and realms.

[Version Filtering]
  - You can enter a regex to match versions.
      Example: ^13\.  - matches all versions starting with 13.
      Example: 3744   - matches any version containing 3744.

[Realm Filtering]
  - Realms are environment tags (e.g. NA1, PBE1).
  - You can filter by "OR" or "AND", and select various tags to refine your search
      Example: NA1|PBE1 - only 

[Language Filtering]
  - When downloading, you can specify language tags.
      Example: en_US|fr_FR  - download English and French only.
  - Some tags are not languages but are content tags, such as "none", "mature" or "video_hq".

[File Filtering]
  - Optional regex to restrict which files are downloaded.
      Example: \.exe$   - only download .exe files.
      Example: Ahri.*   - only files starting with RiotClient.

===================================================
"""

PROJECT_HELP_TEXT = """
================= Project-Specific Notes =================

[ares] - Ares
  - This project is very early valorant when it was still called Project A, and no longer exists on Riot's servers.

[bacon] - Legends of Runeterra
  - This project has two halves. To have a completed build you must have both halves.
      Client - Contains the main exe. Very small manifest. Usually less than 1 megabyte.
      Data - Contians all the card data, assets, sounds, video files, etc. Very large manifest.
  - Later revisions of this script will attempt to automate this structure. For now it must be made manually
  - The full build structure is as follows (using a default, live realm install as reference)
      C:\Riot Games\LoR\live\Game
      C:\Riot Games\LoR\live\PatcherData\PatchableFiles

[ks-foundation] - Riot Client
  - No additional notes for this project

[lion] - 2XKO
  - Version strings are very long, and may change in the future.
      Hotfixes use their changelist revision rather than their full string currently.

[lol] - League of Legends/TFT
  - LoL has two parts and they act independently of each other, so you do not need both.
      Client - Contains the Store, Splash Art, Queues, anything that is NOT "in-game". Manifest is marginally smaller than Game.
      Game - Contains Champions, Maps, Sounds, VO, anything you see "in-game". Manifest is typically 2-3x bigger than the Client.
  - Typically most users will be looking for Windows entries. Filter them by platform and realm as needed.
  - This project has Windows, Mac, iOS, Android, and "Neutral" platforms.
      Neutral is used for content that is shared between platforms. They contain no executables.
  - LoL and TFT are shipped together.
      If you are looking for TFT Mobile assets, filter by "Neutral" and it will usually be the smaller manifest.
  
[valorant] - Valorant
  - This is primarily PC-focused, but does contain hotfixes for PlayStation 5 and Xbox Series X.

==========================================================
"""

CREDITS_TEXT = """
================= Credits =================

This downloader script was created and maintained by:
  - PixelButts
  - https://x.com/PixelButts
  - https://bsky.app/profile/pixel-butts.bsky.social

The tools this downloader script utilizes:
  - https://github.com/moonshadow565/rman

Special thanks to:
  - Everyone who provided feedback and improvements

To leave feedback or report a bug, you can reach me here:
  - https://github.com/RiotArchiveProject/catalog-download-script

===========================================
"""

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_help():
    clear_screen()
    print(HELP_TEXT)
    input("Press Enter to return...")
    clear_screen()

def show_project_help():
    clear_screen()
    print(PROJECT_HELP_TEXT)
    input("Press Enter to return...")
    clear_screen()

def show_credits():
    clear_screen()
    print(CREDITS_TEXT)
    input("Press Enter to return...")
    clear_screen()

def input_with_help(prompt=""):
    val = input(prompt).strip()
    if not val:
        return val
    up = val.upper()
    if up in HELP_KEYS:
        show_help()
        return "__REDRAW__"
    if up in PROJECT_HELP_KEYS:
        show_project_help()
        return "__REDRAW__"
    if up in CREDITS_KEYS:
        show_credits()
        return "__REDRAW__"
    return val.lower()


SELECTED_MANIFESTS = {}

def _sel_key(source, project):
    return (source, project)

def get_selection(source, project):
    return SELECTED_MANIFESTS.get(_sel_key(source, project), set())

def set_selection(source, project, selection_set):
    if selection_set:
        SELECTED_MANIFESTS[_sel_key(source, project)] = set(selection_set)
    else:
        SELECTED_MANIFESTS.pop(_sel_key(source, project), None)

def clear_selection_for(source, project):
    SELECTED_MANIFESTS.pop(_sel_key(source, project), None)

def clear_all_selections():
    SELECTED_MANIFESTS.clear()

def selection_exceeds_limit(source=None, count=0, limit=100):
    if source == "archive":
        return False
    return count > limit

def set_console_size(width=180, height=48):
    try:
        os.system(f'mode con: cols={width} lines={height}')
    except Exception:
        try:
            cols, rows = shutil.get_terminal_size()
            print(f"[Info] Current terminal size: {cols}x{rows}")
        except Exception:
            pass

def ask_number(prompt, min_val, max_val, redraw=None):
    while True:
        val = input_with_help(prompt)
        if val == "__REDRAW__":
            if redraw:
                redraw()
            continue
        val = val.strip()
        if val.isdigit():
            num = int(val)
            if min_val <= num <= max_val:
                return num
        print(f"Please enter a number between {min_val} and {max_val}.")

def print_indexed_grid(options, per_row=5, zero_label="ANY"):
    if not options:
        return
    max_len = max(len(opt) for opt in options)
    idx_width = len(str(len(options)))
    col_width = idx_width + 2 + max_len + 2
    print(f"{0:>{idx_width}}) {zero_label:<{max_len}}", end="")
    print()
    for i, opt in enumerate(options, 1):
        cell = f"{i:>{idx_width}}) {opt:<{max_len}}"
        print(cell.ljust(col_width), end="")
        if i % per_row == 0:
            print()
    if len(options) % per_row != 0:
        print()

def select_realms_interactive(available_realms, current_mode="OR", current_set=None):
    def parse_indices(s, max_idx):
        s = s.strip()
        if not s:
            return set()
        toks = [t.strip() for t in s.split(",") if t.strip()]
        idxs = set()
        for t in toks:
            if "-" in t:
                try:
                    a, b = t.split("-", 1)
                    a_i = int(a); b_i = int(b)
                    if a_i <= 0 or b_i <= 0:
                        continue
                    for i in range(min(a_i, b_i), max(a_i, b_i) + 1):
                        if 0 <= i <= max_idx:
                            idxs.add(i)
                except Exception:
                    continue
            else:
                try:
                    i = int(t)
                    if 0 <= i <= max_idx:
                        idxs.add(i)
                except Exception:
                    continue
        return idxs

    mode = current_mode or "OR"
    selected = set(current_set) if current_set else set()
    max_idx = len(available_realms)
    while True:
        clear_screen()
        print("\n--- Realm Selection ---")
        print(f"Mode: {mode}")
        if selected:
            print("Selected:", ", ".join(sorted(selected)))
        else:
            print("Selected: (ANY)")
        print("\nAvailable realms:")
        print_indexed_grid(available_realms, per_row=5, zero_label="ANY")
        print("\nControls:")
        print("  Enter indices (e.g., 1,3-5) to toggle selection")
        print("  0 = ANY (clear selection)    a = select all    n = clear selection")
        print("  m = toggle mode    d = done (apply)    c = cancel (leave unchanged)")
        choice = input_with_help("Choose: ").strip().lower()
        if choice == "__REDRAW__":
            continue
        if choice == "c":
            return None, None
        if choice == "d":
            return mode, (selected if selected else None)
        if choice == "a":
            selected = set(available_realms)
            continue
        if choice == "n":
            selected.clear()
            continue
        if choice == "m":
            mode = "AND" if mode == "OR" else "OR"
            continue
        idxs = parse_indices(choice, max_idx)
        if not idxs:
            print("Invalid input. Enter indices, '0', 'a', 'n', 'm', 'd', or 'c'.")
            input_with_help("Press Enter to continue...")
            continue
        if 0 in idxs:
            if len(idxs) > 1:
                print("If you choose 0 (ANY) you cannot select other indices at the same time.")
                input_with_help("Press Enter to continue...")
                continue
            selected.clear()
            continue
        for i in sorted(idxs):
            idx0 = i - 1
            if 0 <= idx0 < len(available_realms):
                realm = available_realms[idx0]
                if realm in selected:
                    selected.remove(realm)
                else:
                    selected.add(realm)
        continue

def print_aligned_grid(items, per_row=6):
    if not items:
        return
    max_len = max(len(s) for s in items)
    col_width = max_len + 2
    for i, s in enumerate(items, 1):
        print(f"{s:<{col_width}}", end="")
        if i % per_row == 0:
            print()
    if len(items) % per_row != 0:
        print()

def sanitize_version(ver):
    safe = re.sub(r'[:*?"<>|]', "", ver)
    return safe

def download_manifest(project, manifest_id, dest_base=CACHE_DIR):
    url = f"https://{project}.secure.dyn.riotcdn.net/channels/public/releases/{manifest_id}.manifest"
    dest = dest_base / project / "releases" / f"{manifest_id}.manifest"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 404:
                print(f"[Warn] Manifest {manifest_id} for project '{project}' not found (404). Skipping.")
                return None
            r.raise_for_status()
            dest.write_bytes(r.content)
            print(f"[OK] Downloaded manifest to {dest}")
        except requests.exceptions.RequestException as ex:
            print(f"[Error] Failed to download manifest {manifest_id} for project '{project}': {ex}")
            return None
    return dest

def prompt_languages(project, manifest_id, detected_langs=None):
    entry = CATALOG.get(project, {}).get(manifest_id, {})
    if project == "lol":
        plat = entry.get("platform", "").lower()
        if "windows" in plat:
            autodetect = ["none", "windows"]
        elif "mac" in plat:
            autodetect = ["none", "macos"]
        else:
            autodetect = ["none"]
    else:
        autodetect = ["none"]
    def draw_lang_prompt(detected=None):
        print("\n--- Language Filter ---")
        if detected:
            print(f"\nDetected languages/tags for {project}")
            print_aligned_grid(detected, per_row=6)
        else:
            print(f"\nLanguage hint for {project}: {'|'.join(autodetect)}")
        print()
    prompt_text = "Enter languages/tags separated with | (e.g., none|windows|en_US), or leave blank for no filter (all files): "

    while True:
        draw_lang_prompt(detected_langs)
        choice = input_with_help(prompt_text)
        if choice == "__REDRAW__":
            continue
        choice = choice.strip()
        if not choice:
            return None
        langs = [t.strip() for t in choice.split("|") if t.strip()]
        if "none" not in langs:
            langs.insert(0, "none")
        return "|".join(langs)

def build_output_dir(project, manifest_id, entry, langs=None):
    version = sanitize_version(entry.get("version","unknown"))
    platform = entry.get("platform","unknown")
    base = f"{project}-{version}-{platform}-{manifest_id}"
    outdir = BUILDS_DIR / project / base
    outdir.mkdir(parents=True, exist_ok=True)
    if langs:
        (outdir.parent / f"{base}_filter.txt").write_text(langs, encoding="utf-8")
    return outdir

def run_rman_dl(project, manifest_path, outdir, langs=None, file_filter=None, mode="download", jobs=None, cdn_workers=None):
    if jobs is None:
        jobs = RMAN_DL_JOBS
    if cdn_workers is None:
        cdn_workers = RMAN_DL_CDN_WORKERS
    cmd = [str(RMAN_DL)]
    if langs:
        cmd += ["-l", langs]
    if file_filter:
        cmd += ["-p", file_filter]

    if mode == "archive":
        cmd += ["--cache-readonly"]
        cache_path = ARCHIVE_DIR / project / "bundles" / f"{project}.bundle"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--cache", str(cache_path)]
    else:
        cmd += ["--cdn", f"https://{project}.secure.dyn.riotcdn.net/channels/public"]
        cache_path = CACHE_DIR / project / "bundles" / f"{project}-cache.bundle"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["--cache", str(cache_path)]
    cmd += [str(manifest_path), str(outdir)]
    try:
        j_val = int(jobs)
    except Exception:
        j_val = RMAN_DL_JOBS
    try:
        c_val = int(cdn_workers)
    except Exception:
        c_val = RMAN_DL_CDN_WORKERS
    cmd += ["--jobs", str(j_val), "--cdn-workers", str(c_val)]
    print("[CMD]", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT)


def run_rman_ls(manifest_path, filter_lang=None, filter_path=None, fmt=None, timeout=None):
    if not RMAN_LS.exists():
        print(f"[Error] rman-ls not found at {RMAN_LS}")
        return None
    cmd = [str(RMAN_LS)]
    if fmt:
        cmd += ["--format", fmt]
    if filter_lang:
        cmd += ["-l", filter_lang]
    if filter_path:
        cmd += ["-p", filter_path]
    cmd += [str(manifest_path)]
    try:
        print(f"[Info] parsing manifest {manifest_path.stem}...")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT)
        out, err = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            print(f"[Warn] rman-ls exited with code {proc.returncode}. stderr: {err.strip()}")
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return lines
    except subprocess.TimeoutExpired:
        proc.kill()
        print("[Error] rman-ls timed out.")
        return None
    except Exception as ex:
        print(f"[Error] Failed to run rman-ls: {ex}")
        return None

def prepare_manifest_metadata(project, manifest_id, use_archive=False, allow_manifest_download=True):
    base_dir = ARCHIVE_DIR if use_archive else CACHE_DIR
    manifest_path = base_dir / project / "releases" / f"{manifest_id}.manifest"

    if not use_archive:
        if not manifest_path.exists():
            if allow_manifest_download:
                mpath = download_manifest(project, manifest_id, dest_base=CACHE_DIR)
                if mpath is None:
                    print(f"[Warn] Could not obtain manifest {manifest_id} for project {project}.")
                    return None
                manifest_path = mpath
            else:
                print(f"[Warn] Manifest {manifest_id} missing in cache and downloads are disabled for this mode; skipping.")
                return None
    else:
        if not manifest_path.exists():
            print(f"[Warn] Archive manifest not found at {manifest_path}. Skipping.")
            return None
    metadata_dir = base_dir / project / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = metadata_dir / f"{manifest_id}.txt"
    if metadata_file.exists():
        try:
            lines = [ln.strip() for ln in metadata_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
            langs = set()
            for ln in lines:
                parts = ln.rsplit(",", 1)
                if len(parts) == 2:
                    lang_field = parts[1].strip()
                    langs.update(_split_and_normalize_langs(lang_field))
            return sorted(langs)
        except Exception as ex:
            print(f"[Warn] Failed to read metadata file {metadata_file}: {ex}")
    lines = run_rman_ls(manifest_path)
    if lines is None:
        return None
    try:
        metadata_file.write_text("\n".join(lines), encoding="utf-8")
    except Exception as ex:
        print(f"[Warn] Failed to write metadata file {metadata_file}: {ex}")

    langs = set()
    for ln in lines:
        parts = ln.rsplit(",", 1)
        if len(parts) == 2:
            lang_field = parts[1].strip()
            langs.update(_split_and_normalize_langs(lang_field))
    return sorted(langs)

def prefetch_and_parse_manifests(project, manifest_list, use_archive=False, allow_manifest_download=True):
    results = {}
    base_dir = ARCHIVE_DIR if use_archive else CACHE_DIR
    for mid in manifest_list:
        manifest_path = base_dir / project / "releases" / f"{mid}.manifest"
        if not manifest_path.exists():
            if use_archive:
                print(f"[Warn] Archive manifest missing for {mid}; skipping.")
                continue
            if allow_manifest_download:
                mpath = download_manifest(project, mid, dest_base=CACHE_DIR)
                if mpath is None:
                    print(f"[Warn] Failed to download manifest {mid}; skipping.")
                    continue
                manifest_path = mpath
            else:
                print(f"[Warn] Manifest {mid} missing in cache and downloads are disabled for this mode; skipping.")
                continue
        results[mid] = {'manifest_path': manifest_path, 'langs': None}
    if not results:
        return {}
    for mid in list(results.keys()):
        langs = prepare_manifest_metadata(project, mid, use_archive=use_archive, allow_manifest_download=allow_manifest_download)
        if langs is None:
            print(f"[Warn] Could not parse metadata for {mid}; it will be skipped.")
            results.pop(mid, None)
            continue
        results[mid]['langs'] = langs
    return results

def _split_and_normalize_langs(lang_field):
    if not lang_field:
        return set()
    parts = re.split(r'[;,\|]', lang_field)
    langs = {p.strip() for p in parts if p and p.strip()}
    return langs

def _bytes_to_gb(bytes_val):
    try:
        gb = int(bytes_val) / 1024 / 1024 / 1024
    except Exception:
        return None
    return gb

def _format_gb(bytes_val):
    gb = _bytes_to_gb(bytes_val)
    if gb is None:
        return f"{bytes_val} B"
    if gb < 0.1:
        return f"{gb:.3f} GB"
    if gb < 1:
        return f"{gb:.2f} GB"
    return f"{gb:.1f} GB"

def _manifest_metadata_path(project, manifest_id, use_archive=False):
    base = ARCHIVE_DIR if use_archive else CACHE_DIR
    return base / project / "metadata" / f"{manifest_id}.txt"

def compute_manifest_size_from_metadata(project, manifest_id, selected_langs=None, file_filter_regex=None, use_archive=False):
    meta_path = _manifest_metadata_path(project, manifest_id, use_archive=use_archive)
    if not meta_path.exists():
        return None
    selected_set = None
    if selected_langs:
        if isinstance(selected_langs, str):
            toks = [t.strip() for t in selected_langs.split("|") if t.strip()]
        else:
            toks = [t.strip() for t in selected_langs if isinstance(t, str) and t.strip()]
        if toks:
            selected_set = {t.lower() for t in toks}
        else:
            selected_set = None

    file_re = None
    if file_filter_regex:
        try:
            file_re = re.compile(file_filter_regex, re.IGNORECASE)
        except re.error:
            file_re = None

    try:
        text = meta_path.read_text(encoding="utf-8")
    except Exception:
        return None

    total = 0
    try:
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue

            parts = ln.rsplit(",", 3)
            if len(parts) == 4:
                path_field = parts[0].strip()
                size_field = parts[1].strip()
                langs_field = parts[3].strip()
            else:
                parts2 = ln.rsplit(",", 1)
                if len(parts2) != 2:
                    continue
                rest, lang_field = parts2
                rest_parts = rest.rsplit(",", 1)
                if len(rest_parts) != 2:
                    continue
                path_field = rest_parts[0].strip()
                size_field = rest_parts[1].strip()
                langs_field = lang_field.strip()
            if file_re and not file_re.search(path_field):
                continue
            try:
                size_val = int(size_field)
            except Exception:
                continue
            if selected_set:
                if not langs_field:
                    lang_tokens = ["none"]
                else:
                    lang_tokens = [t.strip() for t in re.split(r'[;,\|,]', langs_field) if t and t.strip()]
                    if not lang_tokens:
                        lang_tokens = ["none"]
                lang_tokens_lc = {t.lower() for t in lang_tokens}
                if lang_tokens_lc.isdisjoint(selected_set):
                    continue
            total += size_val
    except Exception:
        return None
    return total

def format_mb(bytes_val):
    try:
        mb = int(bytes_val) / 1024 / 1024
    except Exception:
        return str(bytes_val)
    return f"{mb:.2f} MB" if mb < 10 else f"{mb:.1f} MB"

def human_mb(size_val):
    return format_mb(size_val)

def check_cache_size(project, threshold_mb=25600):
    return

def draw_project_selection(projects):
    clear_screen()
    print("\n[Project Selection]   [Type 'F1' for Help | 'F2' for Project Help | 'F3' for Credits]")
    for i, p in enumerate(projects, 1):
        print(f"  {i}) {p}")

def search_data(source="catalog", page_size=20):
    if source == "catalog":
        projects = list(CATALOG.keys())
    elif source == "cache":
        projects = [p for p in CATALOG.keys() if (CACHE_DIR / p).exists()]
    elif source == "archive":
        projects = [p for p in CATALOG.keys() if (ARCHIVE_DIR / p).exists()]
    else:
        projects = []
    if not projects:
        print("[Info] No projects available.")
        input_with_help("Press Enter to return...")
        return None, [], None, None
    regex = ""
    realm_mode = "OR"
    realm_set = None
    plat = None
    page = 0
    draw_project_selection(projects)
    choice = ask_number("Select project: ", 1, len(projects), redraw=lambda: draw_project_selection(projects))
    project = projects[choice - 1]
    selection = set(get_selection(source, project))
    while True:
        clear_screen()
        results = []
        if source == "catalog":
            items = CATALOG[project].items()
        else:
            items = []
            base_dir = CACHE_DIR if source == "cache" else ARCHIVE_DIR
            for m in (base_dir / project).rglob("*.manifest"):
                mid = m.stem
                entry = CATALOG[project].get(mid)
                if entry:
                    items.append((mid, entry))
        for mid, entry in items:
            if regex and not re.search(regex, entry.get("version", "")):
                continue
            if realm_set:
                entry_realms = set(entry.get("realms", []) or [])
                if realm_mode == "OR":
                    if entry_realms.isdisjoint(realm_set):
                        continue
                else:
                    if not realm_set.issubset(entry_realms):
                        continue
            if plat and entry.get("platform") != plat:
                continue
            results.append((mid, entry))
        results.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
        realm_display = "ANY"
        if realm_set:
            realm_display = f"{realm_mode}:{'|'.join(sorted(realm_set))}"
        print(f"\n[Current Filter] source={source}, project={project}, version_regex='{regex or 'ALL'}', platform={plat or 'ANY'}, realm={realm_display}")
        print(f"[Info] Results after filters: {len(results)}\n")
        start = page * page_size
        end = start + page_size
        subset = results[start:end]
        rows = []
        for idx, (mid, e) in enumerate(subset, start + 1):
            rows.append({
                "Idx": str(idx),
                "ManifestID": mid,
                "Version": e.get("version", ""),
                "Timestamp": e.get("timestamp", ""),
                "Size": human_mb(e.get("size", "")),
                "Platform": e.get("platform", "unknown"),
                "Realms": "|".join(e.get("realms", [])),
            })
        col_names = ["Idx","ManifestID","Version","Timestamp","Size","Platform","Realms"]
        col_widths = {col: len(col) for col in col_names}
        for r in rows:
            for col in col_names:
                col_widths[col] = max(col_widths[col], len(str(r[col])))
        term_width = shutil.get_terminal_size((120, 20)).columns
        SPACING = 2
        total_width = sum(col_widths.values()) + (len(col_names)-1)*SPACING
        for col in ["Version","Realms"]:
            while total_width > term_width and col_widths[col] > 10:
                col_widths[col] -= 1
                total_width = sum(col_widths.values()) + (len(col_names)-1)*SPACING
        header = (" " * SPACING).join(f"{col:<{col_widths[col]}}" for col in col_names)
        print(header)
        print("-" * min(term_width, len(header)))
        for r in rows:
            line = (" " * SPACING).join(
                f"{str(r[col])[:col_widths[col]]:<{col_widths[col]}}" for col in col_names
            )
            print(line)
        total_pages = (len(results) - 1) // page_size + 1 if results else 1
        print(f"\n[Page {page+1}/{total_pages}]   [Type F1 for Help | F2 for Project Help | F3 for Credits]\n")
        if selection:
            if len(selection) > 25:
                print(f"Selected manifests: {len(selection)}")
            else:
                print("Selected manifests:")
                print(", ".join(selection))
        else:
            print("Selected manifests: (none)")
        print("\nControls:")
        print("  [e] next page  [q] previous page  [0] select all results on this filter")
        print("  [j] switch project  [v] version  [r] realm  [p] platform")
        print("  [d] done (start download/processing of selected manifests)")
        print("  [x] back to menu\n")
        print("Select/Deselect an entry by entering it's Idx number")
        print()
        choice = input_with_help("Choose : ").strip().lower()
        if choice == "__REDRAW__":
            continue
        if choice == "e" and end < len(results):
            page += 1
            continue
        if choice == "q" and page > 0:
            page -= 1
            continue
        if choice == "0":
            if selection_exceeds_limit(source, len(results)):
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            selection = {mid for mid, _ in results}
            set_selection(source, project, selection)
            print(f"[Info] Selected {len(selection)} manifests.")
            input_with_help("Press Enter to continue...")
            continue
        if choice == "d":
            if not selection:
                print("[Warn] No manifests selected. Select at least one index before pressing 'd'.")
                input_with_help("Press Enter to continue...")
                continue
            selected_results = [item for item in results if item[0] in selection]
            realm_return = realm_display if realm_set else None
            return project, selected_results, realm_return, plat
        if choice == "j":
            clear_selection_for(source, project)
            draw_project_selection(projects)
            idx = ask_number("Select project: ", 1, len(projects), redraw=lambda: draw_project_selection(projects))
            project = projects[idx - 1]
            regex, realm_mode, realm_set, plat, page = "", "OR", None, None, 0
            selection = set(get_selection(source, project))
            continue
        if choice == "v":
            while True:
                regex_input = input_with_help("Enter version regex (blank for all): ").strip()
                if regex_input == "__REDRAW__":
                    continue
                regex = regex_input
                break
            page = 0
            clear_selection_for(source, project)
            selection = set()
            continue
        if choice == "r":
            realms = sorted({r for _, e in results for r in e.get("realms", [])})
            if not realms:
                print("[Warn] No realms available.")
                input_with_help("Press Enter to continue...")
            else:
                new_mode, new_set = select_realms_interactive(realms, current_mode=realm_mode, current_set=realm_set)
                if new_mode is None and new_set is None:
                    pass
                else:
                    realm_mode = new_mode
                    realm_set = set(new_set) if new_set else None
            page = 0
            clear_selection_for(source, project)
            selection = set()
            continue
        if choice == "p":
            plats = sorted({e.get("platform", "unknown") for _, e in results})
            if not plats:
                print("[Warn] No platforms available.")
                input_with_help("Press Enter to continue...")
            else:
                print("Available platforms:")
                print_indexed_grid(plats, per_row=5, zero_label="ANY")
                pidx = ask_number("Select platform (0=ANY): ", 0, len(plats))
                plat = None if pidx == 0 else plats[pidx - 1]
            page = 0
            clear_selection_for(source, project)
            selection = set()
            continue
        if choice == "x":
            clear_selection_for(source, project)
            clear_screen()
            return project, [], None, plat
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(results):
                mid = results[num - 1][0]
                if mid in selection:
                    selection.remove(mid)
                    print(f"[Info] Deselected {mid}")
                else:
                    selection.add(mid)
                    print(f"[Info] Selected {mid}")
                set_selection(source, project, selection)
                input_with_help("Press Enter to continue...")
                continue
            else:
                print("Invalid index.")
                input_with_help("Press Enter to continue...")
                continue
        print("Invalid input.")
        input_with_help("Press Enter to continue...")

def confirm_and_compute_sizes_loop(project, manifest_ids, parsed, use_archive=False):
    if not manifest_ids:
        print("[Error] No manifests provided to confirm_and_compute_sizes_loop.")
        return False, [], None
    while True:
        aggregated_langs = sorted({lang for info in parsed.values() for lang in (info.get('langs') or [])})
        first_mid = manifest_ids[0]
        langs_str = prompt_languages(project, first_mid, aggregated_langs)
        if langs_str == "__REDRAW__":
            continue
        selected_langs = [] if langs_str is None else (langs_str.split("|") if isinstance(langs_str, str) else langs_str)
        file_filter = None
        while True:
            filter_input = input_with_help("Enter optional file filter regex (or press Enter to skip): ").strip()
            if filter_input == "__REDRAW__":
                break
            if filter_input:
                try:
                    re.compile(filter_input)
                    file_filter = filter_input
                except re.error:
                    print("[Error] Invalid regex pattern. Skipping file filter.")
                    file_filter = None
            break
        if filter_input == "__REDRAW__":
            continue
        per_manifest = []
        total_bytes = 0
        missing_meta_count = 0
        for mid in manifest_ids:
            size_bytes = compute_manifest_size_from_metadata(
                project, mid,
                selected_langs if selected_langs else None,
                file_filter,
                use_archive=use_archive
            )
            if size_bytes is None:
                per_manifest.append((mid, None))
                missing_meta_count += 1
            else:
                per_manifest.append((mid, size_bytes))
                total_bytes += size_bytes
        print("\nEstimated download sizes with current filters:")
        if len(manifest_ids) > 25:
            print(f"  Selected manifests: {len(manifest_ids)} (details suppressed for large selection)")
        elif len(manifest_ids) > 10:
            print(f"  Selected manifests: {len(manifest_ids)}")
        if len(manifest_ids) > 10:
            print(f"\n  Total estimated size: {_format_gb(total_bytes)} ({total_bytes} bytes)")
            if missing_meta_count:
                print(f"  Note: {missing_meta_count} manifest(s) had missing or unreadable metadata and were excluded from the estimate.")
        else:
            for mid, sz in per_manifest:
                if sz is None:
                    print(f"  {mid}: metadata missing or unreadable (excluded from estimate)")
                else:
                    print(f"  {mid}: {_format_gb(sz)} ({sz} bytes)")
            print(f"\n  Total estimated size: {_format_gb(total_bytes)} ({total_bytes} bytes)")
        if total_bytes >= 100 * 1024**3:
            print("\n[Warn] Total estimated size is >= 100 GB. Proceed with caution.")
        while True:
            confirm = input_with_help("Proceed with download? (y to proceed / r to retry filters / c to cancel selection): ").strip().lower()
            if confirm == "__REDRAW__":
                continue
            if confirm == "y":
                return True, selected_langs, file_filter
            if confirm == "r":
                break
            if confirm == "c":
                print("Cancelled. Returning to selection.")
                return False, selected_langs, file_filter
            print("Please enter 'y' to proceed, 'r' to retry filters, or 'n' to cancel.")

def handle_downloads(project, results, mode="download", use_archive=False):
    if not results:
        return
    manifest_ids = [mid for mid, _ in results]
    allow_manifest_download = True if mode == "download" else False
    if mode == "archive":
        use_archive = True

    parsed = prefetch_and_parse_manifests(project, manifest_ids, use_archive=use_archive, allow_manifest_download=allow_manifest_download)
    if not parsed:
        print("[Error] No manifests available to process after prefetch/parse.")
        input_with_help("Press Enter to continue...")
        return
    if mode == "m":
        print("[Info] Manifests and metadata prepared (manifest-only mode).")
        input_with_help("Press Enter to continue...")
        return
    proceed_result = confirm_and_compute_sizes_loop(project, manifest_ids, parsed, use_archive=use_archive)
    if not proceed_result:
        print("[Info] Download cancelled or aborted.")
        return
    proceed, selected_langs, file_filter = proceed_result
    if not proceed:
        print("[Info] Download cancelled. You can adjust filters and retry.")
        return
    lang_str = "|".join(selected_langs) if selected_langs else None
    for mid, entry in results:
        if mid not in parsed:
            print(f"[Warn] Manifest {mid} was not prepared (skipping).")
            continue
        mpath = parsed[mid].get('manifest_path')
        if not mpath or not mpath.exists():
            print(f"[Warn] Manifest file for {mid} missing at expected path {mpath}; skipping.")
            continue
        outdir = build_output_dir(project, mid, entry, lang_str)
        if lang_str:
            print(f"[Info] Final language filter for {mid}: {lang_str}")
        else:
            print(f"[Info] No language filter applied for {mid} (downloading all)")
        run_rman_dl(project, mpath, outdir, langs=lang_str, file_filter=file_filter, mode=mode)
    check_cache_size(project)
    print("\nDownload complete.")
    input("Press Enter to return to the main menu...")
    clear_screen()

def draw_main_menu():
    clear_screen()
    clear_all_selections()
    print("\n=== Main Menu ===   [Type 'F1' for Help | 'F2' for Project Help | 'F3' for Credits]")
    print("1) Download Mode")
    print("2) Cache Mode")
    print("3) Archive Mode")
    print("4) Download or Update Catalog and Tools")
    print("0) Exit")


def main_menu():
    set_console_size(180, 48)
    while True:
        draw_main_menu()
        choice = input_with_help("Select: ")
        if choice == "__REDRAW__":
            continue
        choice = choice.strip()
        if choice == "4":
            update_catalog()
            input("Press Enter to return to the main menu...")
            continue
        if choice == "1":
            project, results, realm, plat = search_data(source="catalog")
            if not results:
                continue
            if selection_exceeds_limit("catalog", len(results)):
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                while True:
                    confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                    if confirm == "__REDRAW__":
                        continue
                    if confirm == "y":
                        break
                    if confirm == "n":
                        print("Cancelled.")
                        break
                    print("Please enter 'y' to proceed or 'n' to cancel.")
                if confirm != "y":
                    continue
            mode = "d"
            handle_downloads(project, results, mode="download", use_archive=False)
        elif choice == "2":
            project, results, realm, plat = search_data(source="cache")
            if not results:
                continue
            if selection_exceeds_limit("cache", len(results)):
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                while True:
                    confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                    if confirm == "__REDRAW__":
                        continue
                    if confirm == "y":
                        break
                    if confirm == "n":
                        print("Cancelled.")
                        break
                    print("Please enter 'y' to proceed or 'n' to cancel.")
                if confirm != "y":
                    continue
            mode = "d"
            handle_downloads(project, results, mode="cache", use_archive=False)
        elif choice == "3":
            project, results, realm, plat = search_data(source="archive")
            if not results:
                continue
            if selection_exceeds_limit("archive", len(results)):
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                while True:
                    confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                    if confirm == "__REDRAW__":
                        continue
                    if confirm == "y":
                        break
                    if confirm == "n":
                        print("Cancelled.")
                        break
                    print("Please enter 'y' to proceed or 'n' to cancel.")
                if confirm != "y":
                    continue
            mode = "d"
            handle_downloads(project, results, mode="archive", use_archive=True)
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid choice, please try again.")
            input_with_help("Press Enter to continue...")

if __name__ == "__main__":
    main_menu()