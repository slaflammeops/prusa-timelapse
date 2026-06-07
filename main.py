import os
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# ── paths ──────────────────────────────────────────────────────
FRAMES_DIR = Path("/frames")
VIDEO_DIR  = Path("/videos")
FRAMES_DIR.mkdir(exist_ok=True)
VIDEO_DIR.mkdir(exist_ok=True)

# ── state ──────────────────────────────────────────────────────
state = {
    "capturing": False,
    "building":  False,
    "ffmpeg_proc": None,
    "start_time": None,
    "session": None,
    "log": [],
}

def add_log(msg: str, level: str = "info"):
    entry = {"ts": datetime.now().strftime("%H:%M:%S"), "msg": msg, "level": level}
    state["log"].append(entry)
    if len(state["log"]) > 200:
        state["log"].pop(0)
    print(f"[{entry['ts']}] {msg}")

# ── models ─────────────────────────────────────────────────────
class CaptureRequest(BaseModel):
    cam_ip:    str
    rtsp_path: str = "/live"
    interval:  int = 30

class BuildRequest(BaseModel):
    session: str
    fps:     int = 24

class DeleteRequest(BaseModel):
    session: str

# ── helpers ────────────────────────────────────────────────────
def get_sessions():
    sessions = []
    for d in sorted(FRAMES_DIR.iterdir(), reverse=True):
        if d.is_dir():
            frames = list(d.glob("*.jpg"))
            sessions.append({
                "name": d.name,
                "frames": len(frames),
                "built": (VIDEO_DIR / f"{d.name}.mp4").exists()
            })
    return sessions

# ── API ────────────────────────────────────────────────────────
@app.post("/api/capture/start")
def capture_start(req: CaptureRequest):
    if state["capturing"]:
        return JSONResponse({"ok": False, "error": "Already capturing"})

    session_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir  = FRAMES_DIR / session_name
    session_dir.mkdir(exist_ok=True)

    rtsp_url = f"rtsp://{req.cam_ip}{req.rtsp_path}"
    add_log(f"New session: {session_name}", "ok")
    add_log(f"Capturing from {rtsp_url} every {req.interval}s", "info")

    cmd = [
        "ffmpeg", "-rtsp_transport", "tcp",
        "-err_detect", "ignore_err",
        "-fflags", "+discardcorrupt+genpts",
        "-i", rtsp_url,
        "-vf", f"fps=1/{req.interval}",
        "-qscale:v", "2",
        "-strftime", "1",
        str(session_dir / "frame_%Y%m%d_%H%M%S.jpg"),
        "-loglevel", "warning",
        "-y"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        state["ffmpeg_proc"] = proc
        state["capturing"]   = True
        state["start_time"]  = time.time()
        state["session"]     = session_name

        def watch():
            for line in proc.stderr:
                txt = line.decode(errors="ignore").strip()
                if txt:
                    add_log(txt, "warn")
            proc.wait()
            if state["capturing"]:
                state["capturing"] = False
                add_log("FFmpeg process ended", "warn")

        threading.Thread(target=watch, daemon=True).start()
        return {"ok": True, "session": session_name}
    except Exception as e:
        add_log(str(e), "err")
        return JSONResponse({"ok": False, "error": str(e)})


@app.post("/api/capture/stop")
def capture_stop():
    proc = state.get("ffmpeg_proc")
    if proc and state["capturing"]:
        proc.terminate()
        state["capturing"] = False
        state["ffmpeg_proc"] = None
        session = state["session"]
        frames = len(list((FRAMES_DIR / session).glob("*.jpg"))) if session else 0
        add_log(f"Stopped — {frames} frames saved in {session}", "ok")
        return {"ok": True, "frames": frames, "session": session}
    return JSONResponse({"ok": False, "error": "Not capturing"})


@app.post("/api/build")
def build_video(req: BuildRequest):
    if state["building"]:
        return JSONResponse({"ok": False, "error": "Already building"})

    session_dir = FRAMES_DIR / req.session
    if not session_dir.exists():
        return JSONResponse({"ok": False, "error": "Session not found"})

    frames = sorted(session_dir.glob("*.jpg"))
    if not frames:
        return JSONResponse({"ok": False, "error": "No frames in session"})

    filelist = session_dir / "filelist.txt"
    with open(filelist, "w") as f:
        for frame in frames:
            f.write(f"file '{frame}'\n")

    out = VIDEO_DIR / f"{req.session}.mp4"
    add_log(f"Building {req.session} — {len(frames)} frames @ {req.fps} fps", "info")

    def run_build():
        state["building"] = True
        cmd = [
            "ffmpeg", "-r", str(req.fps),
            "-f", "concat", "-safe", "0",
            "-i", str(filelist),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out), "-y"
        ]
        proc = subprocess.run(cmd, capture_output=True)
        state["building"] = False
        filelist.unlink(missing_ok=True)
        if proc.returncode == 0:
            add_log(f"✓ Video ready: {out.name}", "ok")
        else:
            add_log("Build failed: " + proc.stderr.decode(errors="ignore")[-200:], "err")

    threading.Thread(target=run_build, daemon=True).start()
    return {"ok": True}


@app.post("/api/delete_session")
def delete_session(req: DeleteRequest):
    session_dir = FRAMES_DIR / req.session
    count = 0
    if session_dir.exists():
        for f in session_dir.glob("*.jpg"):
            f.unlink()
            count += 1
        session_dir.rmdir()
    video = VIDEO_DIR / f"{req.session}.mp4"
    if video.exists():
        video.unlink()
    add_log(f"Deleted session {req.session} ({count} frames)", "ok")
    return {"ok": True, "deleted": count}


@app.get("/api/status")
def status():
    session = state["session"]
    frames = 0
    if session and (FRAMES_DIR / session).exists():
        frames = len(list((FRAMES_DIR / session).glob("*.jpg")))
    elapsed = int(time.time() - state["start_time"]) if state["start_time"] and state["capturing"] else 0
    return {
        "capturing": state["capturing"],
        "building":  state["building"],
        "session":   session,
        "frames":    frames,
        "elapsed":   elapsed,
        "sessions":  get_sessions(),
        "log":       state["log"][-50:],
    }


@app.get("/api/preview")
def preview():
    session = state["session"]
    if not session:
        return JSONResponse({"ok": False})
    frames = sorted((FRAMES_DIR / session).glob("*.jpg"))
    if not frames:
        return JSONResponse({"ok": False})
    return FileResponse(frames[-1], media_type="image/jpeg")


@app.get("/api/videos/{filename}")
def download_video(filename: str):
    path = VIDEO_DIR / filename
    if not path.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(path, media_type="video/mp4", filename=filename)


# ── serve frontend ─────────────────────────────────────────────
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
