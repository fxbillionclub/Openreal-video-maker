# OpenReel — Unlimited AI Video Maker (Self-Hosted)

Yeh aapka apna, poori tarah se free aur unlimited AI video maker hai — bilkul
oiioii.ai jaisa dikhta hai, lekin **koi API key, koi credit system, koi bill
nahi hai**. Sab kuch aapke apne computer (desktop) par chalta hai.

Ismein kya hota hai:
- Aap ek prompt likhte ho (jaise: "a curious fox discovers a glowing crystal")
- 6 alag-alag styles mein se chunte ho (Anime, Horror, Comedy, Sci-Fi, Nature, History)
- App khud AI art scenes banata hai, awaaz mein narration bolta hai, background
  music generate karta hai, aur sab kuch ek MP4 video mein jod deta hai
- Sab kuch aapke computer par hi hota hai — offline, free, unlimited

---

## 🖥️ Desktop par install kaise karein (Windows / Mac / Linux)

### Step 1: Python install karo (agar pehle se nahi hai)
- [python.org/downloads](https://www.python.org/downloads/) se **Python 3.10 ya usse naya version** download karo.
- Windows par install karte waqt **"Add Python to PATH"** checkbox zaroor tick karo.

### Step 2: FFmpeg install karo
FFmpeg video banane/jodne ke liye zaroori hai.

**Windows:**
1. [ffmpeg.org/download.html](https://ffmpeg.org/download.html) se Windows build download karo (ya `winget install ffmpeg` command se, agar winget hai).
2. Extract karo aur `bin` folder ka path apne System PATH mein add karo.
3. Terminal/CMD mein `ffmpeg -version` chala kar check karo ki kaam kar raha hai.

**Mac:**
```
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```
sudo apt update && sudo apt install ffmpeg espeak-ng
```

**Windows par espeak-ng (awaaz/narration ke liye):**
- [github.com/espeak-ng/espeak-ng/releases](https://github.com/espeak-ng/espeak-ng/releases) se installer download karo aur install karo.
- Iske baad `espeak-ng` bhi PATH mein hona chahiye (installer aksar khud kar deta hai).

### Step 3: Project folder khol kar dependencies install karo

Terminal/Command Prompt mein is folder ke andar jao:

```
cd oii-clone/backend
pip install -r requirements.txt
```

### Step 4: App start karo

```
python -m uvicorn main:app --host 0.0.0.0 --port 8008
```

Terminal mein kuch aisa dikhega:
```
Uvicorn running on http://0.0.0.0:8008
```

### Step 5: Browser mein kholo

Apne browser mein yeh address kholo:

```
http://localhost:8008
```

Bas! Ab aap prompt likh kar jitni chaho utni videos bana sakte ho —
koi limit nahi, koi payment nahi.

---

## 🎨 Real AI-generated art (optional upgrade, GPU chahiye)

By default yeh app apna khud ka procedural art-generation engine use karta hai
(no GPU chahiye, turant chalta hai). Agar aapke paas GPU wala computer hai aur
aap **asli photorealistic/anime AI images** chahte ho (Stable Diffusion jaisa),
toh:

```
pip install diffusers transformers accelerate safetensors torch --extra-index-url https://download.pytorch.org/whl/cu121
```

Phir app start karne se pehle yeh environment variable set karo:

**Windows (CMD):**
```
set ENABLE_DIFFUSION=1
python -m uvicorn main:app --host 0.0.0.0 --port 8008
```

**Mac/Linux:**
```
export ENABLE_DIFFUSION=1
python -m uvicorn main:app --host 0.0.0.0 --port 8008
```

Model pehli baar Hugging Face se free mein download hoga (koi API cost nahi),
uske baad hamesha aapke apne GPU par chalega.

---

## 📁 Project Structure

```
oii-clone/
├── backend/
│   ├── main.py              → FastAPI server + API routes
│   ├── video_engine.py      → Poora video banane ka pipeline
│   ├── scene_art.py         → AI-style art generator (offline)
│   ├── diffusion_backend.py → Optional real Stable Diffusion backend
│   ├── audio_engine.py      → Narration + music generator
│   ├── styles.py            → 6 video styles ki settings
│   ├── fonts/                → Caption fonts
│   ├── videos/                → Generated final videos yahan save hote hain
│   └── thumbnails/            → Video thumbnails
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## ❓ Common Problems

- **"ffmpeg: command not found"** → FFmpeg PATH mein add nahi hua, Step 2 dobara check karo.
- **Awaaz nahi aa rahi / narration fail ho raha hai** → espeak-ng install nahi hai ya PATH mein nahi hai.
- **Video generate hone mein time lag raha hai** → Yeh normal hai, CPU par har video ~30-60 second leta hai (scenes ki sankhya par depend karta hai). GPU ke saath aur fast/behtar hoga.
- **Port already in use** → `--port 8008` ki jagah koi aur number use karo, jaise `--port 8080`, aur phir browser mein woh naya port use karo.

Enjoy your unlimited, free, self-hosted video maker! 🎬
