# home_main.py (launcher with logs, BAT→Direct fallback, cleaner, and Recreate .venv)
from __future__ import annotations
import os, sys, time, socket, subprocess, webbrowser, shutil
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Money Buddy — Home", page_icon="💼", layout="wide")

ROOT = Path(__file__).resolve().parent
APPS = {
    "AstroLotto": {
        "script": ROOT / "AstroLotto" / "programs" / "app_main.py",
        "bat": ROOT / "AstroLotto" / "Launch-AstroLotto.bat",
        "port": 8502,
    },
    "BreakoutBuddy": {
        "script": ROOT / "BreakoutBuddy" / "programs" / "app_main.py",
        "bat": ROOT / "BreakoutBuddy" / "Launch-BreakoutBuddy.bat",
        "port": 8503,
    },
}

# ---------------- utilities ----------------
def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _find_python() -> list[str]:
    exe = sys.executable or ""
    if exe and Path(exe).exists():
        return [exe]
    return ["py", "-3"]

def _append_log(log_file: Path | None, text: str) -> None:
    if not log_file:
        return
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(text if text.endswith("\n") else text + "\n")
    except Exception:
        pass

def _run(cmd: list[str], cwd: Path | None, log_file: Path | None) -> tuple[int, str]:
    try:
        res = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, shell=False)
        out = res.stdout or ""
    except Exception as e:
        out = f"[launcher] failed to run: {cmd}\n{e}"
        res = type("X", (), {"returncode": 1})()
    _append_log(log_file, "\n$ " + " ".join(cmd))
    if out:
        _append_log(log_file, out)
    return res.returncode, out

def _start_streamlit(script: Path, port: int, log_file: Path | None = None) -> subprocess.Popen:
    py = _find_python()
    cmd = py + ["-m", "streamlit", "run", str(script), "--server.port", str(port)]
    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    stdout = open(log_file, "a", encoding="utf-8") if log_file else subprocess.DEVNULL
    stderr = subprocess.STDOUT if log_file else subprocess.DEVNULL
    return subprocess.Popen(
        cmd, cwd=str(script.parent), stdout=stdout, stderr=stderr,
        startupinfo=startupinfo, creationflags=creationflags,
        close_fds=True, shell=False,
    )

def _start_via_bat(bat: Path, log_file: Path | None = None) -> subprocess.Popen | None:
    if not bat.exists() or os.name != "nt":
        return None
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    if log_file:
        _append_log(log_file, f"\n=== Launch via BAT at {time.ctime()} ===")
        cmd = f'cmd /c ""{bat}" >> "{log_file}" 2>&1"'
    else:
        cmd = f'"{bat}"'
    return subprocess.Popen(
        cmd, cwd=str(bat.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=creationflags, shell=True,
    )

def _start_app(name: str, cfg: dict, mode: str, wait_s: float = 30.0, log_dir: Path | None = None) -> str:
    port = cfg["port"]
    if _port_open("127.0.0.1", port):
        return f"{name} already running on {port}."
    log_path = (log_dir / f"launcher_{name.lower()}.log") if log_dir else None
    if log_path:
        _append_log(log_path, f"\n=== Launch at {time.ctime()} ===")

    used = "direct"
    if mode == "BAT (use per-app venv)" and cfg.get("bat"):
        proc = _start_via_bat(cfg["bat"], log_file=log_path)
        if proc is not None:
            used = "bat"
        else:
            _start_streamlit(cfg["script"], port, log_file=log_path)
    else:
        _start_streamlit(cfg["script"], port, log_file=log_path)

    for _ in range(int(max(1, wait_s / 0.5))):
        time.sleep(0.5)
        if _port_open("127.0.0.1", port):
            return f"{name} started on port {port} (mode={used})."
    return f"{name} launch issued (mode={used}), but port {port} not open after {int(wait_s)}s."

def _stop_app(cfg: dict) -> str:
    port = cfg["port"]
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :%d') do @echo %a" % port,
                shell=True, text=True, stderr=subprocess.DEVNULL,
            )
            pids = {line.strip() for line in out.splitlines() if line.strip().isdigit()}
            for pid in pids:
                subprocess.call(["taskkill", "/PID", pid, "/F"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["lsof", f"-i:{port}", "-t"], text=True)
            for pid in {p for p in out.split() if p.isdigit()}:
                subprocess.call(["kill", "-9", pid])
        except Exception:
            pass
    time.sleep(0.3)
    return "Stopped." if not _port_open("127.0.0.1", port) else "Could not confirm stop."

def _open(name: str, cfg: dict):
    webbrowser.open_new_tab(f"http://127.0.0.1:{cfg['port']}")

# ---------- venv helpers ----------
def _venv_paths(app_root: Path) -> tuple[Path, Path]:
    if os.name == "nt":
        py = app_root / ".venv" / "Scripts" / "python.exe"
        pip = app_root / ".venv" / "Scripts" / "pip.exe"
    else:
        py = app_root / ".venv" / "bin" / "python"
        pip = app_root / ".venv" / "bin" / "pip"
    return py, pip

def _find_requirements(app_root: Path) -> Path | None:
    candidates = [
        app_root / "extras" / "requirements.txt",
        app_root / "requirements.txt",
        ROOT / "extras" / "requirements.txt",
        ROOT / "requirements.txt",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def _recreate_venv_for_app(name: str, cfg: dict, log_dir: Path | None) -> str:
    """Stop app, nuke .venv, create new one, upgrade pip, install requirements."""
    app_root = cfg["script"].parent.parent
    log_path = (log_dir / f"launcher_{name.lower()}.log") if log_dir else None
    _append_log(log_path, f"\n=== Recreate .venv for {name} at {time.ctime()} ===")
    # Stop first to release file locks on Windows
    _stop_app(cfg)

    venv_dir = app_root / ".venv"
    try:
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
            _append_log(log_path, f"[launcher] removed {venv_dir}")
    except Exception as e:
        _append_log(log_path, f"[launcher] could not remove {venv_dir}: {e}")
        return f"Failed: could not remove existing .venv ({e})."

    # Create venv
    rc, out = _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=app_root, log_file=log_path)
    if rc != 0:
        return "Failed: venv creation error. See launcher log."

    vpy, _ = _venv_paths(app_root)
    if not vpy.exists():
        _append_log(log_path, "[launcher] venv python not found after creation.")
        return "Failed: venv python not found."

    # Upgrade pip toolchain
    rc, _ = _run([str(vpy), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
                 cwd=app_root, log_file=log_path)
    if rc != 0:
        return "Failed: pip upgrade error. See launcher log."

    # Install requirements if present
    req = _find_requirements(app_root)
    if req:
        rc, _ = _run([str(vpy), "-m", "pip", "install", "-r", str(req)], cwd=app_root, log_file=log_path)
        if rc != 0:
            return f"Failed: package install error from {req}. See launcher log."
        return f".venv recreated for {name}. Installed from {req}."
    else:
        _append_log(log_path, "[launcher] no requirements file found.")
        return f".venv recreated for {name}. No requirements file found."

# ---------------- UI ----------------
st.title("💼 Money Buddy — Home")
st.write("Start/stop, open, embed, clean junk, or rebuild venvs.")

# Global launcher options
with st.expander("Launcher options (advanced)"):
    mode = st.radio("Start method", ["BAT (use per-app venv)", "Direct (current Python)"], index=0, horizontal=True)
    wait_s = st.slider("Startup wait (seconds)", 5, 60, 30, 5)
    log_launch = st.checkbox("Capture logs", value=True)
    log_dir = ROOT / "Logs" if log_launch else None
    if log_dir:
        st.caption(f"Logs will be written to: {log_dir}")

if "status" not in st.session_state:
    st.session_state["status"] = {k: "" for k in APPS}

colA, colB = st.columns(2)
for col, (name, cfg) in zip((colA, colB), APPS.items()):
    with col:
        st.subheader(name)
        running = _port_open("127.0.0.1", cfg["port"])
        st.markdown(f"**Status:** {'🟢 Running' if running else '🔴 Stopped'}  (port {cfg['port']})")
        c1, c2, c3 = st.columns(3)
        if c1.button(f"Start {name}", use_container_width=True, key=f"start_{name}"):
            msg = _start_app(name, cfg, mode, wait_s=wait_s, log_dir=log_dir)
            st.session_state["status"][name] = msg
            st.rerun()
        if c2.button(f"Stop {name}", use_container_width=True, key=f"stop_{name}"):
            msg = _stop_app(cfg)
            st.session_state["status"][name] = msg
            st.rerun()
        if c3.button(f"Open {name}", use_container_width=True, key=f"open_{name}"):
            _open(name, cfg)
            st.session_state["status"][name] = "Opened in browser."
            st.rerun()

        c4, _ = st.columns([1, 2])
        if c4.button(f"Recreate .venv", use_container_width=True, key=f"venv_{name}"):
            with st.spinner(f"Recreating .venv for {name}…"):
                msg = _recreate_venv_for_app(name, cfg, log_dir)
            st.session_state["status"][name] = msg
            st.success(msg)

        status_msg = st.session_state["status"].get(name, "")
        if status_msg:
            st.info(status_msg)

        embed = st.toggle(f"Embed {name} here", value=False, key=f"embed_{name}")
        if embed:
            if running:
                st.components.v1.iframe(f"http://127.0.0.1:{cfg['port']}", height=900)
            else:
                st.info("App not running yet. Click Start, then toggle embed.")

# -------- Maintenance: project cleanup --------
st.divider()
st.subheader("Maintenance — Clean build junk")

with st.expander("Clean up generated files", expanded=False):
    st.write("Select what to remove across the project. **CSV and JSON are never touched.**")
    colc1, colc2, colc3 = st.columns(3)
    rm_bak = colc1.checkbox("*.bak", value=True)
    rm_pyc = colc1.checkbox("*.pyc", value=True)
    rm_log = colc2.checkbox("*.log", value=True)
    rm_pycache = colc2.checkbox("__pycache__ dirs", value=True)
    rm_venv = colc3.checkbox(".venv/.venv_home or pyvenv.cfg folders (danger)", value=False,
                             help="Deletes virtual environments. You'll need to reinstall packages afterwards.")
    preview = st.button("Preview what will be deleted", type="secondary")
    do_clean = st.button("Delete the files above", type="primary",
                         disabled=not st.session_state.get("cleanup_preview_ready", False))

    def _scan_cleanup(root: Path, rm_bak: bool, rm_pyc: bool, rm_log: bool,
                      rm_pycache: bool, rm_venv: bool, limit: int = 20000):
        files, dirs = [], []
        exts = set()
        if rm_bak: exts.add(".bak")
        if rm_pyc: exts.add(".pyc")
        if rm_log: exts.add(".log")
        seen = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)

            if rm_pycache and dp.name == "__pycache__":
                dirs.append(dp); dirnames[:] = []; continue
            if rm_venv and dp.name == ".venv":
                dirs.append(dp); dirnames[:] = []; continue

            for bad in (".git", ".hg", ".svn"):
                if bad in dirnames:
                    dirnames.remove(bad)

            for fn in filenames:
                if fn.lower().endswith((".csv", ".json")):
                    continue
                p = dp / fn
                if p.suffix.lower() in exts:
                    files.append(p)
                    seen += 1
                    if seen >= limit:
                        return files, dirs, True
        return files, dirs, False

    if preview:
        files, dirs, truncated = _scan_cleanup(ROOT, rm_bak, rm_pyc, rm_log, rm_pycache, rm_venv)
        total_bytes = 0
        for p in files:
            try:
                total_bytes += p.stat().st_size
            except Exception:
                pass
        st.session_state["cleanup_preview"] = {"files": [str(p) for p in files],
                                               "dirs": [str(d) for d in dirs],
                                               "bytes": int(total_bytes),
                                               "truncated": truncated}
        st.session_state["cleanup_preview_ready"] = True

    if st.session_state.get("cleanup_preview_ready"):
        info = st.session_state.get("cleanup_preview", {})
        files = info.get("files", [])
        dirs = info.get("dirs", [])
        total_bytes = info.get("bytes", 0)
        truncated = info.get("truncated", False)

        st.markdown(f"**Files:** {len(files)}  •  **Dirs:** {len(dirs)}  •  **Approx size:** {total_bytes/1024/1024:.2f} MB")
        if truncated:
            st.caption("Preview truncated after 20,000 items. Narrow your selection if needed.")
        with st.expander("Show paths", expanded=False):
            st.code("\n".join([*dirs, *files]) or "(nothing to delete)")

    if do_clean and st.session_state.get("cleanup_preview_ready"):
        info = st.session_state.get("cleanup_preview", {})
        files = [Path(p) for p in info.get("files", [])]
        dirs = [Path(p) for p in info.get("dirs", [])]
        removed_files = removed_dirs = errors = 0
        for p in files:
            try:
                p.unlink(missing_ok=True); removed_files += 1
            except Exception:
                errors += 1
        for d in dirs:
            try:
                shutil.rmtree(d, ignore_errors=False); removed_dirs += 1
            except Exception:
                errors += 1
        st.success(f"Removed {removed_files} files and {removed_dirs} directories. Errors: {errors}.")
        st.session_state["cleanup_preview_ready"] = False
        st.session_state["cleanup_preview"] = {}

# Log viewer
if (log_dir and any((log_dir / f"launcher_{n.lower()}.log").exists() for n in APPS)):
    st.divider()
    st.subheader("Launcher logs")
    for name in APPS:
        lf = log_dir / f"launcher_{name.lower()}.log"
        if lf.exists():
            try:
                with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()[-6000:]
            except Exception:
                txt = "(could not read log file)"
            st.markdown(f"**{name}** — `{lf}`")
            st.text_area(f"Log: {name}", txt, height=200)
