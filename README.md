# Prusa Timelapse

A self-hosted web UI for capturing timelapses from your **Prusa Buddy3D camera**.

Captures JPEG frames via RTSP stream using FFmpeg, organizes them by print session, and assembles MP4 videos — all from a clean browser interface. Designed to run on a NAS or any machine with Docker.

---

## Features

- 📷 RTSP stream capture via FFmpeg with error tolerance flags for unstable streams
- 🗂️ Session-based frame management — one subfolder per print, named by timestamp
- 🎬 One-click MP4 assembly per session using H.264/libx264
- 🖼️ Live preview of latest captured frame (refreshes every 3 seconds)
- ⬇️ Download videos directly from the browser
- ⚙️ Persistent settings saved in browser localStorage (camera IP, interval, FPS)
- 🐳 Docker-ready, no build step — runs on `python:3.12-slim` with FFmpeg installed at startup

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Video capture | FFmpeg (RTSP → JPEG frames) |
| Video assembly | FFmpeg (concat → H.264 MP4) |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Container | Docker / Docker Compose |
| Camera protocol | RTSP (port 554) |
| Stream format | H.264 over TCP |

---

## Requirements

- **Prusa Buddy3D camera** with RTSP enabled
  → Prusa app → Camera → cogwheel → toggle **"RTSP stream on local network"**
  → Note the camera IP shown below that toggle
- Docker + Docker Compose
- Camera and host must be on the same local network

---

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/prusa-timelapse.git
   cd prusa-timelapse
   ```

2. Edit `docker-compose.yml` and update the volume paths:
   ```yaml
   volumes:
     - /path/to/your/app:/app        # folder containing main.py and static/
     - /path/to/your/frames:/frames  # where JPEG frames will be saved
     - /path/to/your/videos:/videos  # where MP4 videos will be saved
   ```
   Also update `TZ` to your timezone (e.g. `America/New_York`).

3. Deploy:
   ```bash
   docker compose up -d
   ```

4. Open `http://YOUR-HOST-IP:8080` in your browser.

> **First startup** takes 1–2 minutes while Docker installs FFmpeg and the Python dependencies inside the container. Subsequent starts are fast.

---

## Usage

1. **Settings** → enter your camera IP (e.g. `192.168.1.42`), adjust capture interval and output FPS
2. **Capture** → click **Start** when your print begins — a timestamped session folder is created automatically
3. **Capture** → click **Stop** when your print ends
4. **Sessions** → click **Build** to assemble the MP4, then **Download**

---

## Configuration

| Setting | Default | Description |
|---|---|---|
| Camera IP | `192.168.1.42` | IP of the Buddy3D camera on your LAN |
| RTSP path | `/live` | Stream path (don't change unless needed) |
| Capture interval | `30s` | One frame every N seconds (1–120) |
| Playback FPS | `24` | Output video framerate (12 / 24 / 30) |

---

## FFmpeg capture flags

The capture command uses the following flags for reliability:

```
-rtsp_transport tcp       # use TCP instead of UDP for stability
-err_detect ignore_err    # continue on stream decode errors
-fflags discardcorrupt    # silently drop corrupted frames
-fflags genpts            # generate missing timestamps
-qscale:v 2               # JPEG quality (2 = best, 31 = worst)
```

---

## Folder structure

```
prusa-timelapse/
├── main.py                        ← FastAPI backend
├── docker-compose.yml
├── static/
│   └── index.html                 ← Web UI (single file, no framework)
├── frames/
│   ├── 2026-06-04_18-30-00/       ← Session folder (one per print)
│   │   ├── frame_20260604_183045.jpg
│   │   └── frame_20260604_183115.jpg
│   └── 2026-06-05_09-15-00/
└── videos/
    ├── 2026-06-04_18-30-00.mp4
    └── 2026-06-05_09-15-00.mp4
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/capture/start` | Start FFmpeg capture, creates session |
| `POST` | `/api/capture/stop` | Stop FFmpeg process |
| `POST` | `/api/build` | Assemble MP4 from session frames |
| `POST` | `/api/delete_session` | Delete session frames and video |
| `GET` | `/api/status` | Returns capture state, frame count, session list |
| `GET` | `/api/preview` | Returns latest captured JPEG |
| `GET` | `/api/videos/{filename}` | Download a built MP4 |

---

## Ports

- `8080` → Web UI (change the left side in `docker-compose.yml` if already in use)

---

## Acknowledgments

Built with the help of [Claude Sonnet 4.5](https://claude.ai) by Anthropic — assisted with architecture, backend, frontend, and Docker configuration.