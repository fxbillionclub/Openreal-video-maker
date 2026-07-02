"""
Core self-hosted video assembly engine.
Pipeline: prompt -> scenes (text) -> per-scene AI art + narration ->
Ken Burns animated clip with animated caption overlay -> crossfade
stitch -> mux with music bed -> final MP4.

Everything runs locally via Pillow + espeak-ng + ffmpeg. No external
API calls, no per-video billing, no rate limit — run it as many times
as your own CPU/GPU can handle.
"""
import json
import os
import re
import shutil
import subprocess
import time
import uuid

from styles import get_style
from scene_art import generate_scene_image, generate_thumbnail, W, H
from audio_engine import synthesize_narration, generate_music_bed, mix_narration_and_music, get_duration

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
THUMBS_DIR = os.path.join(BASE_DIR, "thumbnails")
TMP_DIR = os.path.join(BASE_DIR, "scenes_tmp")
DB_PATH = os.path.join(BASE_DIR, "db.json")
FONT_BOLD = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

FPS = 24
SCENE_DURATION_PAD = 0.9  # extra seconds after narration ends, before crossfade
XFADE_DUR = 0.6


def _run(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {cmd}\n{proc.stderr[-2000:]}")


def _load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH) as f:
            return json.load(f)
    return []


def _save_db(items):
    with open(DB_PATH, "w") as f:
        json.dump(items, f, indent=2)


def list_videos():
    items = _load_db()
    return list(reversed(items))


def get_video(video_id):
    for it in _load_db():
        if it["id"] == video_id:
            return it
    return None


def delete_video(video_id):
    items = _load_db()
    items2 = [it for it in items if it["id"] != video_id]
    _save_db(items2)
    for base, ext in [(VIDEOS_DIR, "mp4"), (THUMBS_DIR, "jpg")]:
        p = os.path.join(base, f"{video_id}.{ext}")
        if os.path.exists(p):
            os.remove(p)
    return True


def build_scenes_from_prompt(prompt: str, style: dict, n_scenes: int = 4):
    """If the user typed several sentences, use each as a scene.
    Otherwise expand a single-topic prompt using the style's story template."""
    prompt = prompt.strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prompt) if s.strip()]
    if len(sentences) >= 2:
        return sentences[:6]
    topic = prompt.rstrip(".!? ") or "an unexpected adventure"
    topic = topic[0:1].upper() + topic[1:]
    if not topic.endswith((".", "!", "?")):
        topic += "."
    templates = style["templates"]
    scenes = [t.format(topic=topic) for t in templates[:n_scenes]]
    return scenes


def _wrap_lines(text, max_chars=24):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _caption_chunks(text, max_chars=24, lines_per_chunk=2):
    """Wrap full scene text into lines, then group into chunks of N lines each,
    so long sentences are shown fully in sequential caption pages instead of
    being cut off."""
    lines = _wrap_lines(text, max_chars=max_chars)
    chunks = []
    for i in range(0, len(lines), lines_per_chunk):
        chunks.append(lines[i:i + lines_per_chunk])
    return chunks or [[text]]


def _drawtext_filters(chunks, text_color, duration):
    """Build a chain of drawtext filters for animated (fade+rise) multi-line captions,
    positioned near the bottom third. `chunks` is a list of line-groups; each chunk
    is shown for an equal slice of `duration` with a quick fade in/out, so long
    scene sentences are shown in full instead of being truncated."""
    filters = []
    color_hex = "%02x%02x%02x" % text_color
    fade_dur = 0.35
    n_chunks = len(chunks)
    slice_dur = duration / n_chunks

    for ci, lines in enumerate(chunks):
        seg_start = ci * slice_dur
        seg_end = seg_start + slice_dur
        n = len(lines)
        for i, line in enumerate(lines):
            safe = line.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
            y_expr = f"(h*0.80)+{i}*(text_h*1.35)-({(n-1)/2}*text_h*1.35)"
            local_t = f"(t-{seg_start:.2f})"
            alpha_expr = (
                f"if(lt(t,{seg_start:.2f}),0,"
                f"if(gt(t,{seg_end:.2f}),0,"
                f"if(lt({local_t},{fade_dur}),{local_t}/{fade_dur},"
                f"if(gt({local_t},{slice_dur - fade_dur:.2f}),"
                f"max(0,({slice_dur:.2f}-{local_t})/{fade_dur}),1))))"
            )
            filters.append(
                "drawtext="
                f"fontfile={FONT_BOLD}:text='{safe}':"
                f"fontcolor=0x{color_hex}@1:fontsize=50:"
                f"borderw=6:bordercolor=black@0.75:"
                f"shadowcolor=black@0.6:shadowx=2:shadowy=3:"
                f"x=(w-text_w)/2:y={y_expr}:"
                f"alpha='{alpha_expr}'"
            )
    return filters


def _build_scene_clip(image_path, narration_wav, scene_text, style, out_mp4, idx):
    dur = get_duration(narration_wav) + SCENE_DURATION_PAD
    zoom_in = idx % 2 == 0
    frames = int(dur * FPS)

    # Ken Burns zoompan: slow zoom in/out with slight pan, deterministic by idx
    if zoom_in:
        z_expr = f"min(zoom+0.0009,1.18)"
        x_expr = "iw/2-(iw/zoom/2)+ (on/{})*40".format(max(frames, 1))
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        z_expr = f"if(eq(on,0),1.18,max(zoom-0.0009,1.0))"
        x_expr = "iw/2-(iw/zoom/2) - (on/{})*40".format(max(frames, 1))
        y_expr = "ih/2-(ih/zoom/2)"

    chunks = _caption_chunks(scene_text)
    caption_filters = _drawtext_filters(chunks, style["text_color"], dur)
    vf_chain = (
        f"scale=1600:-1,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        f"vignette=PI/4,"
        + ",".join(caption_filters)
    )

    cmd = (
        f'ffmpeg -y -loop 1 -i "{image_path}" -i "{narration_wav}" '
        f'-t {dur:.2f} -vf "{vf_chain}" '
        f'-c:v libx264 -pix_fmt yuv420p -r {FPS} -c:a aac -shortest "{out_mp4}"'
    )
    _run(cmd)
    return out_mp4, dur


def _crossfade_concat(clip_paths, durations, out_path):
    if len(clip_paths) == 1:
        shutil.copy(clip_paths[0], out_path)
        return out_path

    inputs = "".join(f'-i "{p}" ' for p in clip_paths)
    n = len(clip_paths)
    vfilter_parts = []
    afilter_parts = []
    running_offset = 0.0
    v_labels = [f"{i}:v" for i in range(n)]
    a_labels = [f"{i}:a" for i in range(n)]

    cur_v = v_labels[0]
    cur_a = a_labels[0]
    for i in range(1, n):
        offset = running_offset + durations[i - 1] - XFADE_DUR
        offset = max(offset, 0.01)
        out_v = f"v{i}"
        out_a = f"a{i}"
        vfilter_parts.append(
            f"[{cur_v}][{v_labels[i]}]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.2f}[{out_v}]"
        )
        afilter_parts.append(
            f"[{cur_a}][{a_labels[i]}]acrossfade=d={XFADE_DUR}[{out_a}]"
        )
        cur_v = out_v
        cur_a = out_a
        running_offset = offset + XFADE_DUR

    filter_complex = ";".join(vfilter_parts + afilter_parts)
    cmd = (
        f'ffmpeg -y {inputs} -filter_complex "{filter_complex}" '
        f'-map "[{cur_v}]" -map "[{cur_a}]" -c:v libx264 -pix_fmt yuv420p -c:a aac "{out_path}"'
    )
    _run(cmd)
    return out_path


def generate_video(prompt: str, style_id: str, progress_cb=None):
    """Main entry point: builds a full short video from a text prompt.
    progress_cb(stage:str, pct:int) optional callback for live progress."""
    style = get_style(style_id)
    style = {**style, "id": style_id}
    video_id = uuid.uuid4().hex[:12]
    work_dir = os.path.join(TMP_DIR, video_id)
    os.makedirs(work_dir, exist_ok=True)

    def prog(stage, pct):
        if progress_cb:
            progress_cb(stage, pct)

    prog("Writing script", 5)
    scenes = build_scenes_from_prompt(prompt, style)
    n = len(scenes)

    clip_paths = []
    durations = []
    scene_images = []

    for i, scene_text in enumerate(scenes):
        base_pct = 10 + int(60 * (i / n))
        prog(f"Painting scene {i+1}/{n}", base_pct)
        img_path = os.path.join(work_dir, f"scene_{i}.jpg")
        generate_scene_image(scene_text, i, style, img_path)
        scene_images.append(img_path)

        prog(f"Recording voiceover {i+1}/{n}", base_pct + 5)
        narr_path = os.path.join(work_dir, f"narr_{i}.wav")
        synthesize_narration(scene_text, narr_path, style)

        prog(f"Animating scene {i+1}/{n}", base_pct + 8)
        clip_path = os.path.join(work_dir, f"clip_{i}.mp4")
        _, dur = _build_scene_clip(img_path, narr_path, scene_text, style, clip_path, i)
        clip_paths.append(clip_path)
        durations.append(dur)

    prog("Editing sequence together", 78)
    stitched = os.path.join(work_dir, "stitched.mp4")
    _crossfade_concat(clip_paths, durations, stitched)

    prog("Composing music score", 86)
    total_dur = get_duration(stitched)
    music_path = os.path.join(work_dir, "music.wav")
    generate_music_bed(total_dur, music_path, style)

    prog("Final mix & mastering", 92)
    final_out = os.path.join(VIDEOS_DIR, f"{video_id}.mp4")
    cmd = (
        f'ffmpeg -y -i "{stitched}" -i "{music_path}" '
        f'-filter_complex "[0:a]volume=1.5[a0];[1:a]volume=0.8[a1];[a0][a1]amix=inputs=2:duration=first,loudnorm=I=-14:TP=-1:LRA=11[aout]" '
        f'-map 0:v -map "[aout]" -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -movflags +faststart "{final_out}"'
    )
    _run(cmd)

    prog("Generating thumbnail", 97)
    thumb_out = os.path.join(THUMBS_DIR, f"{video_id}.jpg")
    generate_thumbnail(scene_images, thumb_out)

    record = {
        "id": video_id,
        "prompt": prompt,
        "style": style_id,
        "style_name": style["name"],
        "scenes": scenes,
        "duration": round(total_dur, 1),
        "created_at": time.time(),
        "video_url": f"/videos/{video_id}.mp4",
        "thumb_url": f"/thumbnails/{video_id}.jpg",
    }
    items = _load_db()
    items.append(record)
    _save_db(items)

    shutil.rmtree(work_dir, ignore_errors=True)
    prog("Done", 100)
    return record
