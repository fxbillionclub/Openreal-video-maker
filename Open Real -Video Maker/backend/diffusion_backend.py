"""
OPTIONAL true text-to-image backend using an open-source diffusion model
(Stable Diffusion). This is NOT required to run the app — the app works
fully offline/free with the procedural renderer in scene_art.py.

To enable real AI-generated scene art on a machine that has a GPU:

    pip install diffusers transformers accelerate safetensors torch --extra-index-url https://download.pytorch.org/whl/cu121
    export ENABLE_DIFFUSION=1
    export SD_MODEL_ID=stabilityai/sd-turbo   # or any open-source model you like

Then just start the backend normally (uvicorn main:app). The model is
downloaded once from Hugging Face (free, no per-call API cost) and cached
locally — after that every generation runs on your own hardware, so it
truly has no usage limit and no API bill.
"""
import os
import threading

_pipe = None
_lock = threading.Lock()


def _load_pipe():
    global _pipe
    if _pipe is not None:
        return _pipe
    with _lock:
        if _pipe is not None:
            return _pipe
        import torch
        from diffusers import AutoPipelineForText2Image

        model_id = os.environ.get("SD_MODEL_ID", "stabilityai/sd-turbo")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        pipe = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=dtype)
        pipe = pipe.to(device)
        _pipe = pipe
        return _pipe


STYLE_SUFFIX = {
    "anime": "anime key visual, studio quality, cinematic lighting, vibrant colors",
    "horror": "dark horror atmosphere, cinematic, eerie fog, high contrast, film grain",
    "comedy": "bright colorful cartoon style, playful, exaggerated, fun lighting",
    "scifi": "futuristic sci-fi concept art, neon lighting, epic scale, cinematic",
    "nature": "nature photography style, soft natural light, warm and cozy",
    "history": "ancient historical epic painting style, golden hour lighting, dramatic",
}


def generate_with_diffusion(text: str, style: dict, out_path: str, size=(768, 1344)) -> bool:
    try:
        pipe = _load_pipe()
        suffix = STYLE_SUFFIX.get(style.get("id", ""), "cinematic, high detail")
        prompt = f"{text}, {suffix}, vertical composition, no text, no watermark"
        image = pipe(
            prompt=prompt,
            num_inference_steps=int(os.environ.get("SD_STEPS", "4")),
            guidance_scale=0.0,
            height=size[1] - (size[1] % 8),
            width=size[0] - (size[0] % 8),
        ).images[0]
        image = image.resize(size)
        image.save(out_path, quality=92)
        return True
    except Exception as e:
        print("Diffusion backend unavailable, falling back to procedural art:", e)
        return False
