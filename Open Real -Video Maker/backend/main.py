"""
FastAPI backend for the self-hosted "unlimited" AI video maker.
No API keys, no billing, no rate limiting by design — generation is
only bounded by your own machine's CPU/GPU. Runs a lightweight in-process
job queue so multiple videos can be queued and generated back-to-back
(or in parallel across worker threads) with live progress reported
over polling / SSE.
"""
import os
import threading
import time
import uuid
import queue

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from styles import list_styles, get_style, STYLES
from video_engine import generate_video, list_videos, get_video, delete_video, VIDEOS_DIR, THUMBS_DIR

app = FastAPI(title="OpenReel — Unlimited AI Video Maker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")
app.mount("/thumbnails", StaticFiles(directory=THUMBS_DIR), name="thumbnails")

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# ---- In-memory job tracking (no external DB / queue needed) ----
JOBS = {}
JOBS_LOCK = threading.Lock()
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))
_task_queue: "queue.Queue" = queue.Queue()


class GenerateRequest(BaseModel):
    prompt: str
    style: str = "anime"


def _worker_loop():
    while True:
        job_id, prompt, style_id = _task_queue.get()
        try:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "running"

            def cb(stage, pct):
                with JOBS_LOCK:
                    JOBS[job_id]["stage"] = stage
                    JOBS[job_id]["progress"] = pct

            record = generate_video(prompt, style_id, progress_cb=cb)
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "done"
                JOBS[job_id]["progress"] = 100
                JOBS[job_id]["result"] = record
        except Exception as e:
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = str(e)
        finally:
            _task_queue.task_done()


for _ in range(MAX_WORKERS):
    t = threading.Thread(target=_worker_loop, daemon=True)
    t.start()


@app.get("/api/styles")
def api_styles():
    return {"styles": list_styles()}


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    prompt = (req.prompt or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)
    style_id = req.style if req.style in STYLES else "anime"
    job_id = uuid.uuid4().hex[:10]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "stage": "Queued",
            "prompt": prompt,
            "style": style_id,
            "created_at": time.time(),
        }
    _task_queue.put((job_id, prompt, style_id))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return JSONResponse({"error": "not found"}, status_code=404)
        return dict(job)


@app.get("/api/jobs/{job_id}/stream")
def api_job_stream(job_id: str):
    def gen():
        last = None
        while True:
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                yield "event: error\ndata: not found\n\n"
                return
            payload = f'data: {{"status":"{job["status"]}","progress":{job["progress"]},"stage":"{job["stage"]}"}}\n\n'
            if payload != last:
                yield payload
                last = payload
            if job["status"] in ("done", "error"):
                return
            time.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/videos")
def api_list_videos():
    return {"videos": list_videos()}


@app.get("/api/videos/{video_id}")
def api_get_video(video_id: str):
    v = get_video(video_id)
    if not v:
        return JSONResponse({"error": "not found"}, status_code=404)
    return v


@app.delete("/api/videos/{video_id}")
def api_delete_video(video_id: str):
    delete_video(video_id)
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "queue_size": _task_queue.qsize(), "workers": MAX_WORKERS}


# Serve the frontend last so /api/* and /videos, /thumbnails routes take priority
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
