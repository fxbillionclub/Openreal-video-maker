"""
Self-hosted generative scene artwork.
No external API calls, no GPU required — pure procedural generation
(gradient fields, particle systems, light rays, noise) driven by a hash
of the scene text + style, so every prompt produces a unique, deterministic
piece of art. This is the "free tier" renderer that always works offline.

If ENABLE_DIFFUSION=1 and a GPU + diffusers/torch stack is available,
generate_scene_image() will instead call into diffusion_backend.py for
true text-to-image generation (see that file for how to enable it on
a machine with a GPU).
"""
import hashlib
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

W, H = 1024, 1820  # portrait 9:16 base render size (downscaled/upscaled by ffmpeg as needed)

ENABLE_DIFFUSION = os.environ.get("ENABLE_DIFFUSION", "0") == "1"


def _seed_from(text: str, idx: int) -> random.Random:
    h = hashlib.sha256(f"{text}-{idx}".encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _radial_gradient(size, colors, rnd):
    w, h = size
    img = Image.new("RGB", (w, h))
    cx = rnd.uniform(0.3, 0.7) * w
    cy = rnd.uniform(0.2, 0.6) * h
    maxd = math.hypot(max(cx, w - cx), max(cy, h - cy))
    px = img.load()
    # Render at reduced resolution for speed, then upscale
    small_w, small_h = w // 4, h // 4
    small = Image.new("RGB", (small_w, small_h))
    spx = small.load()
    for y in range(small_h):
        for x in range(small_w):
            sx, sy = x * 4, y * 4
            d = math.hypot(sx - cx, sy - cy) / maxd
            d = min(1.0, d)
            if d < 0.5:
                t = d / 0.5
                c = _lerp(colors[0], colors[1], t)
            else:
                t = (d - 0.5) / 0.5
                c = _lerp(colors[1], colors[2], t)
            spx[x, y] = c
    img = small.resize((w, h), Image.BICUBIC)
    return img


def _add_light_rays(img, rnd, color, count=6):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx = rnd.uniform(0.2, 0.8) * w
    cy = rnd.uniform(-0.1, 0.3) * h
    for i in range(count):
        angle = rnd.uniform(0, math.pi * 2)
        length = rnd.uniform(0.8, 1.4) * h
        width_ang = rnd.uniform(0.02, 0.06)
        a1 = angle - width_ang
        a2 = angle + width_ang
        p1 = (cx, cy)
        p2 = (cx + length * math.cos(a1), cy + length * math.sin(a1))
        p3 = (cx + length * math.cos(a2), cy + length * math.sin(a2))
        alpha = rnd.randint(10, 35)
        draw.polygon([p1, p2, p3], fill=(*color, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(30))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def _draw_particles(img, rnd, kind, color, count=60):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(count):
        x = rnd.uniform(0, w)
        y = rnd.uniform(0, h)
        s = rnd.uniform(3, 14)
        alpha = rnd.randint(40, 160)
        col = (*color, alpha)
        if kind == "petal":
            draw.ellipse([x, y, x + s, y + s * 0.6], fill=col)
        elif kind == "star":
            pts = []
            for k in range(5):
                ang = math.pi / 2 + k * (2 * math.pi / 5)
                pts.append((x + s * math.cos(ang), y + s * math.sin(ang)))
            draw.polygon(pts, fill=col)
        elif kind == "leaf":
            draw.ellipse([x, y, x + s * 0.6, y + s], fill=col)
        else:  # spark
            draw.ellipse([x, y, x + s * 0.3, y + s * 0.3], fill=col)
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.6))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def _draw_silhouette(img, rnd, color):
    """A soft abstract silhouette / horizon shape to suggest a subject or landscape."""
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    kind = rnd.choice(["mountains", "figure", "arch", "orb"])
    dark = tuple(int(c * 0.35) for c in color)
    if kind == "mountains":
        base_y = h * rnd.uniform(0.55, 0.75)
        pts = [(0, h)]
        x = 0
        while x < w:
            x += rnd.uniform(80, 180)
            y = base_y + rnd.uniform(-120, 120)
            pts.append((min(x, w), y))
        pts.append((w, h))
        draw.polygon(pts, fill=(*dark, 160))
    elif kind == "figure":
        cx = w * rnd.uniform(0.35, 0.65)
        base_y = h * rnd.uniform(0.55, 0.7)
        draw.ellipse([cx - 45, base_y - 260, cx + 45, base_y - 170], fill=(*dark, 180))
        draw.polygon(
            [(cx - 70, base_y - 175), (cx + 70, base_y - 175), (cx + 55, h * 0.95), (cx - 55, h * 0.95)],
            fill=(*dark, 180),
        )
    elif kind == "arch":
        cx = w / 2
        draw.ellipse([cx - 260, h * 0.25, cx + 260, h * 0.25 + 520], outline=(*dark, 200), width=26)
    else:
        cx = w * rnd.uniform(0.3, 0.7)
        cy = h * rnd.uniform(0.25, 0.45)
        r = rnd.uniform(120, 220)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*dark, 140))
    overlay = overlay.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def _grain(img, rnd, amount=10):
    import numpy as np

    arr = np.array(img).astype("int16")
    noise = (np.random.RandomState(rnd.randint(0, 999999)).randn(*arr.shape) * amount).astype("int16")
    arr = arr + noise
    arr = arr.clip(0, 255).astype("uint8")
    return Image.fromarray(arr)


def _vignette(img, color):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([-w * 0.3, -h * 0.2, w * 1.3, h * 1.25], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(180))
    dark_layer = Image.new("RGB", (w, h), color)
    return Image.composite(img, dark_layer, mask)


def generate_scene_image(text: str, idx: int, style: dict, out_path: str):
    """Generate one procedural artwork frame for a scene. Deterministic per (text, idx, style)."""
    if ENABLE_DIFFUSION:
        try:
            from diffusion_backend import generate_with_diffusion

            ok = generate_with_diffusion(text, style, out_path, size=(W, H))
            if ok:
                return out_path
        except Exception:
            pass  # fall back to procedural renderer

    rnd = _seed_from(text, idx)
    img = _radial_gradient((W, H), style["gradient"], rnd)
    img = _add_light_rays(img, rnd, style["accent"], count=rnd.randint(4, 8))
    img = _draw_silhouette(img, rnd, style["accent"])
    img = _draw_particles(img, rnd, style["particle"], style["particle_color"], count=rnd.randint(40, 90))
    img = ImageEnhance.Color(img).enhance(1.25)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = _vignette(img, style["vignette"])
    img = _grain(img, rnd, amount=6)
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.save(out_path, quality=92)
    return out_path


def generate_thumbnail(scene_paths, out_path):
    if not scene_paths:
        return None
    img = Image.open(scene_paths[0]).convert("RGB")
    img.thumbnail((480, 854))
    img.save(out_path, quality=88)
    return out_path
