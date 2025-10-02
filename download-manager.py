#!/usr/bin/env python3
import json, re, subprocess, requests, os, shutil, ctypes
from pathlib import Path
import plistlib

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))

TOOLS_DIR = ROOT / "Tools"
RMAN_DL = TOOLS_DIR / "rman-dl.exe"

CACHE_DIR = ROOT / "Cache"
BUILDS_DIR = ROOT / "Builds"

LANG_GROUPS = {
    "ares": [["none"], ["mature"], ["ar_AE","de_DE","en_US","es_ES","es_MX","fr_FR","id_ID","it_IT","ja_JP","ko_KR","pl_PL","pt_BR","ru_RU","th_TH","tr_TR","vi_VN","zh_CN","zh_TW"]],
    "bacon": [["none"], ["video_hq","video_lq"], ["en_us","fr_fr","de_de","it_it","ja_jp","ko_kr","pl_pl","pt_pl","pt_br","ru_ru","es_mx","es_es","tr_tr"], ["China","Korea","Russia","Taiwan","Turkey","Vietnam","Uncensored"]],
    "ks-foundation": [["none"]],
    "lion": [["none"]],
    "lol": [["none"], ["macos","windows"], ["ar_AE","cs_CZ","de_DE","el_GR","en_AU","en_GB","en_PH","en_SG","en_US","es_AR","es_ES","es_MX","fr_FR","hu_HU","id_ID","it_IT","ja_JP","ko_KR","pl_PL","pt_BR","ro_RO","ru_RU","th_TH","tr_TR","vi_VN","zh_CN","zh_MY","zh_TW"]],
    "valorant": [["none"], ["mature"], ["all_loc","ar_AE","de_DE","en_US","es_ES","es_MX","fr_FR","id_ID","it_IT","ja_JP","ko_KR","pl_PL","pt_BR","ru_RU","th_TH","tr_TR","vi_VN","zh_CN","zh_TW"], ["krrating","twmlogo","vnglogo"]],
}

# ---------- Help System ----------

HELP_KEY = "h"
PROJECT_HELP_KEY = "k"
CREDITS_KEY = "c"

HELP_TEXT = """
================= Downloader Help =================

[General purpose of this downloader script]
  - This script allows you to download current or older revisions of various projects by Riot Games.
  - This will NOT help you run them, but does simplify the process significantly without large storage commitment.
  - There will be bugs and issues. If you find any, or want to leave feedback, please check the Credits section.

[Cache Statistics / Builds Statistics]
  - Cache shows how many manifests and bundle files are stored locally.
  - Builds shows how many extracted builds you have and their disk usage.

[Main Menu Selections]
  1) Search catalog  – browse all known manifests from catalog.json
  2) View cache      – browse only manifests you have cached locally
  3) Exit            – quit the program

[Project Selection]
  - Choose which project (lol, valorant, etc.) you want to browse.
  - Each project has its own manifests, platforms, and realms.

[Version Filtering]
  - You can enter a regex to match versions.
      Example: ^13\.  → matches all versions starting with 13.
      Example: 3744   → matches any version containing 3744.

[Realm Filtering]
  - Realms are environment tags (e.g. NA1, PBE1).
  - You can select ANY or a specific realm.
      Example: choose "NA1" to only see entries deployed to NA1.

[Language Filtering]
  - When downloading, you can specify language tags.
      Example: en_US|fr_FR  → download English and French only.
  - "none" is always included automatically.
  - Some tags are not languages but are content tags, such as "mature" or "video_hq".

[File Filtering]
  - Optional regex to restrict which files are downloaded.
      Example: \.exe$   → only download .exe files.
      Example: Ahri.* → only files starting with RiotClient.

===================================================
"""

PROJECT_HELP_TEXT = """
================= Project-Specific Notes =================

[ares] - Ares
  - This project is very early valorant when it was still called Project A, and no longer exists on Riot's servers.
      Due to this, it is mentioned but not present in the catalog, but may be when this is resolved.

[bacon] - Legends of Runeterra
  - This project has two halves. To have a completed build you must have both halves.
      Client - Contains the main exe. Very small manifest. Usually less than 1 megabyte.
      Data - Contians all the card data, assets, sounds, video files, etc. Very large manifest. Usually over 10 megabytes
  - Later revisions of this script will attempt to automate this structure. For now it must be made manually
  - The full build structure is as follows (using a default, live realm install as reference)
      C:\Riot Games\LoR\live\Game
      C:\Riot Games\LoR\live\PatcherData\PatchableFiles

[ks-foundation] - Riot Client
  - No additional notes for this project

[lion] - 2XKO
  - Version strings are very long, and may change in the future.

[lol] - League of Legends/TFT
  - LoL has two parts and they act independently of each other, so you do not need both.
      Client - Contains the Store, Splash Art, Queues, anything that is NOT "in-game". Manifest is marginally smaller than Game.
      Game - Contains Champions, Maps, Sounds, VO, anything you see "in-game". Manifest is typically 2-3x bigger than the Client.
  - Typically most users will be looking for Windows entries. Filter them by platform and realm as needed.
  - This project has Windows, Mac, iOS, Android, and "Neutral" platforms.
      Neutral is used for content that is shared between platforms. They hold no executables or platform-specific data.
  - LoL and TFT are shipped together.
      If you are looking for TFT Mobile assets, filter by "Neutral" and it will usually be the smaller one.
  
[valorant] - Valorant
  - This is primarily PC-focused, but does contain hotfixes for PlayStation 5 and Xbox Series X.
  - This project also has several specific asset tags I do not know how to properly match. Use your best judgment.

==========================================================
"""

CREDITS_TEXT = """
================= Credits =================

This downloader script was created and maintained by:
  - PixelButts

The tools this downloader script utilizes are created by
  - moonshadow565 (rman)

Special thanks to:
  - Riot Games
  - Open source libraries (requests, pathlib, etc.)
  - Everyone who provided feedback and improvements

To leave feedback or report a bug, you can reach me here:
  - Riot Archive Project Discord: https://discord.gg/pjMv95NWW5
  - https://x.com/PixelButts
  - https://bsky.app/profile/pixel-butts.bsky.social

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
    val = input(prompt).strip().lower()
    if val == HELP_KEY:
        show_help()
        return "__REDRAW__"
    if val == PROJECT_HELP_KEY:
        show_project_help()
        return "__REDRAW__"
    if val == CREDITS_KEY:
        show_credits()
        return "__REDRAW__"
    return val

# ---------- Helpers ----------
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
    """
    Ask for a number within [min_val, max_val].
    If help is invoked, calls redraw() (if provided) and re-prompts.
    """
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
    """
    Print options in aligned columns with indices.
    0 is reserved for 'ANY'.
    """
    if not options:
        return
    max_len = max(len(opt) for opt in options)
    idx_width = len(str(len(options)))
    col_width = idx_width + 2 + max_len + 2  # "NN) value  "

    # Print 0 first
    print(f"{0:>{idx_width}}) {zero_label:<{max_len}}", end="")
    print()  # newline after 0

    for i, opt in enumerate(options, 1):
        cell = f"{i:>{idx_width}}) {opt:<{max_len}}"
        print(cell.ljust(col_width), end="")
        if i % per_row == 0:
            print()
    if len(options) % per_row != 0:
        print()

def print_aligned_grid(items, per_row=6):
    """
    Print a list of strings in neat aligned columns, no indices.
    """
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

def download_manifest(project, manifest_id):
    url = f"https://{project}.secure.dyn.riotcdn.net/channels/public/releases/{manifest_id}.manifest"
    dest = CACHE_DIR / project / "releases" / f"{manifest_id}.manifest"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"[OK] Downloaded manifest to {dest}")
    return dest

def prompt_languages(project, manifest_id):
    groups = LANG_GROUPS.get(project, [["none"]])
    entry = CATALOG.get(project, {}).get(manifest_id, {})
    autodetect = []

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

    def draw_lang_prompt():
        #clear_screen()  # optional
        print("\n--- Language Filter ---   [Type 'h' for Help | 'k' for Project Help | 'c' for Credits]")
        print("\nAvailable language/tag groups for", project)
        for group in groups:
            print_aligned_grid(group, per_row=6)
        print(f"\nCurrent language filter: \"{'|'.join(autodetect)}\"")

    while True:
        draw_lang_prompt()
        choice = input_with_help(
            "Enter languages/tags separated by | (or leave blank for no filter): "
        )
        if choice == "__REDRAW__":
            # loop will redraw and re‑ask
            continue

        choice = choice.strip()
        if not choice:
            return None

        langs = choice.split("|")
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

def run_rman_dl(project, manifest_path, outdir, langs=None, file_filter=None, use_cache=True):
    cache_path = CACHE_DIR / project / "bundles" / f"{project}-cache.bundle"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(RMAN_DL)]
    if langs:
        cmd += ["-l", langs]
    if file_filter:
        cmd += ["-p", file_filter]
    cmd += ["--cdn", f"https://{project}.secure.dyn.riotcdn.net/channels/public"]
    if use_cache:
        cmd += ["--cache", str(cache_path)]
    cmd += [str(manifest_path), str(outdir)]
    print("[CMD]", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT)

def format_mb(bytes_val):
    try:
        mb = int(bytes_val) / 1024 / 1024
    except Exception:
        return str(bytes_val)
    return f"{mb:.2f} MB" if mb < 10 else f"{mb:.1f} MB"

def human_mb(size_val):
    return format_mb(size_val)

def show_stats():
    term_width = shutil.get_terminal_size((120, 20)).columns
    gap = 4

    cache_data = {}
    for proj in CATALOG.keys():
        bundle_dir = CACHE_DIR / proj / "bundles"
        releases_dir = CACHE_DIR / proj / "releases"
        size = sum(f.stat().st_size for f in bundle_dir.glob("*.bundle")) if bundle_dir.exists() else 0
        count = sum(1 for _ in releases_dir.glob("*.manifest")) if releases_dir.exists() else 0
        cache_data[proj] = (size, count)

    cache_total_size = sum(s for s, _ in cache_data.values())
    cache_total_count = sum(c for _, c in cache_data.values())

    builds_data = {}
    for proj in CATALOG.keys():
        proj_dir = BUILDS_DIR / proj
        if proj_dir.exists():
            build_dirs = [d for d in proj_dir.iterdir() if d.is_dir()]
            count = len(build_dirs)
            size = sum(f.stat().st_size for d in build_dirs for f in d.rglob("*") if f.is_file())
        else:
            size, count = 0, 0
        builds_data[proj] = (size, count)

    builds_total_size = sum(s for s, _ in builds_data.values())
    builds_total_count = sum(c for _, c in builds_data.values())

    left_title = "[Cache Statistics]"
    right_title = "[Builds Statistics]"
    left_totals = f"Total cache size: {format_mb(cache_total_size)}   Total cached count: {cache_total_count}"
    right_totals = f"Total size: {format_mb(builds_total_size)}   Total count: {builds_total_count}"

    left_proj_max = max(
        (len(f"  {p}: Size {format_mb(s)}, Count {c}") for p, (s, c) in cache_data.items()),
        default=0
    )
    right_proj_max = max(
        (len(f"  {p}: Size {format_mb(s)}, Count {c}") for p, (s, c) in builds_data.items()),
        default=0
    )
    left_width = max(len(left_title), len(left_totals), left_proj_max)
    right_width = max(len(right_title), len(right_totals), right_proj_max)

    if left_width + gap + right_width > term_width:
        right_width = max(20, term_width - left_width - gap)

    def print_row(left, right):
        print(f"{left:<{left_width}}{' ' * gap}{right:<{right_width}}")

    print_row(left_title, right_title)
    print_row(left_totals, right_totals)

    for proj in CATALOG.keys():
        c_size, c_count = cache_data[proj]
        b_size, b_count = builds_data[proj]
        left = f"  {proj}: Size {format_mb(c_size)}, Count {c_count}"
        right = f"  {proj}: Size {format_mb(b_size)}, Count {b_count}"
        print_row(left, right)

def check_cache_size(project, threshold_mb=25600):
    bundle_dir = CACHE_DIR / project / "bundles"
    size = sum(f.stat().st_size for f in bundle_dir.glob("*.bundle")) if bundle_dir.exists() else 0
    mb = size / 1024 / 1024

    if mb > threshold_mb:
        while True:
            ans = input_with_help(
                f"[Cache] {project} cache is {format_mb(size)}, exceeds {threshold_mb} MB. Clean? (y/N): "
            ).strip().lower()
            if ans == "__REDRAW__":
                clear_screen()
                print(f"[Cache] {project} cache is {format_mb(size)}, exceeds {threshold_mb} MB. Clean? (y/N): ")
                continue
            break
        if ans == "y":
            for f in bundle_dir.glob("*.bundle"):
                try:
                    f.unlink()
                except Exception as ex:
                    print(f"[Warn] Could not delete {f}: {ex}")
            print("[Cache] Cleaned.")

# ---------- Unified Search (catalog or cache) ----------
def draw_project_selection(projects):
    clear_screen()
    show_stats()
    print("\n[Project Selection]   [Type 'h' for Help | 'k' for Project Help | 'c' for Credits]")
    for i, p in enumerate(projects, 1):
        print(f"  {i}) {p}")

def search_data(source="catalog", page_size=20):
    if source == "catalog":
        projects = list(CATALOG.keys())
    else:
        projects = [p for p in CATALOG.keys() if (CACHE_DIR / p).exists()]
    if not projects:
        print("[Info] No projects available.")
        input_with_help("Press Enter to return...")
        return None, [], None, None

    regex = ""
    realm = None
    plat = None
    page = 0

    draw_project_selection(projects)
    choice = ask_number("Select project: ", 1, len(projects), redraw=lambda: draw_project_selection(projects))
    project = projects[choice - 1]

    while True:
        clear_screen()
        results = []
        if source == "catalog":
            items = CATALOG[project].items()
        else:
            items = []
            for m in (CACHE_DIR / project).rglob("*.manifest"):
                mid = m.stem
                entry = CATALOG[project].get(mid)
                if entry:
                    items.append((mid, entry))

        for mid, entry in items:
            if regex and not re.search(regex, entry.get("version", "")):
                continue
            if realm and realm not in entry.get("realms", []):
                continue
            if plat and entry.get("platform") != plat:
                continue
            results.append((mid, entry))
        results.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)

        show_stats()
        print(f"\n[Current Filter] project={project}, version_regex='{regex or 'ALL'}', platform={plat or 'ANY'}, realm={realm or 'ANY'}")
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
        print(f"\n[Page {page+1}/{total_pages}]   [Type 'h' for Help | 'k' for Project Help | 'c' for Credits]\n")

        print("Results:")
        print("  [e] next page  [q] previous page  [0] download all")
        print("Filter:")
        print("  [j] project  [v] version  [r] realm  [p] platform")
        print("  [x] back to menu\n")

        choice = input_with_help("Choose : ").strip().lower()
        if choice == "__REDRAW__":
            continue

        if choice == "e" and end < len(results):
            page += 1
        elif choice == "q" and page > 0:
            page -= 1
        elif choice == "0":
            if len(results) > 100:
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                if confirm == "__REDRAW__":
                    continue
                if confirm != "y":
                    print("Cancelled.")
                    input_with_help("Press Enter to continue...")
                    continue
            return project, results, realm, plat
        elif choice == "j":
            draw_project_selection(projects)
            idx = ask_number("Select project: ", 1, len(projects), redraw=lambda: draw_project_selection(projects))
            project = projects[idx - 1]
            regex, realm, plat, page = "", None, None, 0
        elif choice == "v":
            while True:
                regex_input = input_with_help("Enter version regex (blank for all): ").strip()
                if regex_input == "__REDRAW__":
                    continue
                regex = regex_input
                break
            page = 0
        elif choice == "r":
            realms = sorted({r for _, e in results for r in e.get("realms", [])})
            if not realms:
                print("[Warn] No realms available.")
                input_with_help("Press Enter to continue...")
            else:
                print("Available realms:")
                print_indexed_grid(realms, per_row=5, zero_label="ANY")
                ridx = ask_number("Select realm (0=ANY): ", 0, len(realms))
                realm = None if ridx == 0 else realms[ridx - 1]
            page = 0
        elif choice == "p":
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
        elif choice == "x":
            clear_screen()
            return project, [], realm, plat
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(results):
                return project, [results[num - 1]], realm, plat
            else:
                print("Invalid index.")
                input_with_help("Press Enter to continue...")
        else:
            print("Invalid input.")
            input_with_help("Press Enter to continue...")
            
# ---------- Unified Download ----------
def handle_downloads(project, results, mode="d"):
    if not results:
        return

    if mode == "d":
        langs_str = prompt_languages(project, results[0][0])
        if langs_str is None:
            base_langs_list = []
        else:
            base_langs_list = langs_str.split("|") if isinstance(langs_str, str) else langs_str

        file_filter = None
        while True:
            filter_input = input_with_help("Enter optional file filter regex (or press Enter to skip): ").strip()
            if filter_input == "__REDRAW__":
                clear_screen()
                print("[Type 'h' for Help | 'k' for Project Help | 'c' for Credits]")
                continue
            if filter_input:
                try:
                    re.compile(filter_input)
                    file_filter = filter_input
                except re.error:
                    print("[Error] Invalid regex pattern. Skipping file filter.")
                    file_filter = None
            break
    else:
        base_langs_list = []
        file_filter = None

    for mid, entry in results:
        mpath = download_manifest(project, mid)
        if mode == "d":
            langs_list = list(base_langs_list)

            # --- Project-specific rules ---
            if project == "lol" and langs_list:
                p = entry.get("platform", "").lower()
                if "windows" in p and "windows" not in langs_list:
                    langs_list.append("windows")
                elif "mac" in p and "macos" not in langs_list:
                    langs_list.append("macos")

            if project == "valorant" and "all_loc" in langs_list:
                langs_list = ["none", "all_loc"]

            lang_str = "|".join(langs_list) if langs_list else None
            outdir = build_output_dir(project, mid, entry, lang_str)
            if lang_str:
                print(f"[Info] Final language filter: {lang_str}")
            else:
                print("[Info] No language filter applied (downloading all)")
            run_rman_dl(project, mpath, outdir, lang_str, file_filter)

    check_cache_size(project)
    clear_screen()

# ---------- Main Menu ----------
def draw_main_menu():
    clear_screen()
    show_stats()
    print("\n=== Main Menu ===   [Type 'h' for Help | 'k' for Project Help | 'c' for Credits]")
    print("1) Search catalog")
    print("2) View cache")
    print("3) Exit")

def main_menu():
    set_console_size(180, 48)
    while True:
        draw_main_menu()
        choice = input_with_help("Select: ")
        if choice == "__REDRAW__":
            continue
        choice = choice.strip()

        if choice == "1":
            project, results, realm, plat = search_data(source="catalog")
            if not results:
                continue
            if len(results) > 100:
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                if confirm == "__REDRAW__":
                    continue
                if confirm != "y":
                    print("Cancelled.")
                    continue
            mode = input_with_help("Download manifests only (m) or manifests + run rman-dl (d)? [Default is d]: ").strip().lower() or "d"
            if mode == "__REDRAW__":
                continue
            handle_downloads(project, results, mode)

        elif choice == "2":
            project, results, realm, plat = search_data(source="cache")
            if not results:
                continue
            if len(results) > 100:
                print(f"[Error] Too many entries selected ({len(results)}). Max allowed is 100.")
                input_with_help("Press Enter to continue...")
                continue
            if len(results) > 10:
                confirm = input_with_help(f"[Warning] You are about to download {len(results)} entries. Proceed? (y/N): ").strip().lower()
                if confirm == "__REDRAW__":
                    continue
                if confirm != "y":
                    print("Cancelled.")
                    continue
            mode = input_with_help("Download manifests only (m) or manifests + run rman-dl (d)? [Default is d]: ").strip().lower() or "d"
            if mode == "__REDRAW__":
                continue
            handle_downloads(project, results, mode)

        elif choice == "3":
            print("Exiting.")
            break
        else:
            print("Invalid choice, please try again.")
            input_with_help("Press Enter to continue...")

if __name__ == "__main__":
    main_menu()