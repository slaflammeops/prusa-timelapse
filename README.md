# Prusa Timelapse

A self-hosted web UI for capturing timelapses from your **Prusa Buddy3D camera**.

Captures frames via RTSP, organizes them by print session, and assembles MP4 videos — all from a clean browser interface. Designed to run on a NAS or any machine with Docker.

## Features

- 📷 RTSP stream capture via FFmpeg
- 🗂️ Session-based frame management (one folder per print)
- 🎬 One-click MP4 assembly per session
- 🖼️ Live preview of latest captured frame
- ⬇️ Download videos directly from the UI
- ⚙️ Persistent settings (camera IP, interval, FPS)
- 🐳 Docker-ready, no build step required

## Requirements

- Prusa Buddy3D camera with RTSP enabled
  → Prusa app → Camera → cogwheel → toggle **"RTSP stream on local network"**
  → Note the camera IP shown below that toggle
- Docker + Docker Compose

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/prusa-timelapse.git
   cd prusa-timelapse
   ```

2. Edit `docker-compose.yml` and update the volume paths:
   ```yaml
   volumes:
     - /path/to/your/app:/app
     - /path/to/your/frames:/frames
     - /path/to/your/videos:/videos
   ```
   Also update `TZ` to your timezone (e.g. `America/New_York`).

3. Deploy:
   ```bash
   docker compose up -d
   ```

4. Open `http://YOUR-HOST-IP:8080` in your browser.

## Usage

1. **Settings** → enter your camera IP and adjust capture interval and FPS
2. **Capture** → click Start when your print begins
3. **Capture** → click Stop when your print ends
4. **Sessions** → click Build on your session, then Download the MP4

## Folder structure

```
prusa-timelapse/
├── main.py              ← FastAPI backend
├── docker-compose.yml
├── static/
│   └── index.html       ← Web UI
├── frames/              ← Captured JPEGs (one subfolder per session)
└── videos/              ← Built MP4 timelapses
```

## Ports

- `8080` → Web UI (change the left side in docker-compose.yml if needed)
