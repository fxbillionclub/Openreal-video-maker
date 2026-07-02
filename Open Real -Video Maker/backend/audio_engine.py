"""
Self-hosted audio: offline narration (espeak-ng) + procedurally generated
background music/ambience (pure ffmpeg synth, no samples needed) +
sound-shaping so voices don't sound too robotic. Zero API cost, zero limits.
"""
import os
import subprocess
import shlex

FFMPEG = "ffmpeg"


def run(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def synthesize_narration(text: str, out_wav: str, style: dict):
    """Generate narration with espeak-ng, then post-process with ffmpeg filters
    (EQ + light reverb + compression) so it sounds warmer/less robotic."""
    speed = style.get("voice_speed", 160)
    pitch = style.get("voice_pitch", 50)
    raw_wav = out_wav + ".raw.wav"
    safe_text = text.replace('"', "'")
    cmd = f'espeak-ng -v en+f3 -s {speed} -p {pitch} -a 190 -w "{raw_wav}" "{safe_text}"'
    run(cmd)

    # Post process: gentle low-shelf warmth, de-ess-ish highpass, light reverb via aecho, compand
    filt = (
        "highpass=f=90,"
        "equalizer=f=250:t=q:w=1.2:g=3,"
        "equalizer=f=3500:t=q:w=1:g=-2,"
        "aecho=0.8:0.7:20:0.25,"
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=80,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd2 = f'{FFMPEG} -y -i "{raw_wav}" -af "{filt}" -ar 44100 -ac 1 "{out_wav}"'
    run(cmd2)
    try:
        os.remove(raw_wav)
    except OSError:
        pass
    return out_wav


def get_duration(path: str) -> float:
    out = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{path}"',
        shell=True, capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 3.0


def generate_music_bed(duration: float, out_wav: str, style: dict):
    """Purely synthetic ambient pad + soft pulse, generated with ffmpeg's aevalsrc
    (no royalty question, no samples, no external files, no API)."""
    root = style.get("music_root", 220.0)
    scale = style.get("music_scale", [0, 4, 7, 12])
    freqs = [root * (2 ** (s / 12)) for s in scale]

    # Build a layered pad: sum of sines at scale degrees with slow tremolo, quiet noise bed
    expr_terms = []
    for i, f in enumerate(freqs):
        amp = 0.05 / (i + 1)
        lfo = 0.15 + 0.05 * i
        expr_terms.append(f"{amp}*sin(2*PI*{f:.3f}*t)*(0.7+0.3*sin(2*PI*{lfo:.3f}*t))")
    expr = "+".join(expr_terms)

    dur = max(1.0, duration)
    cmd = (
        f'{FFMPEG} -y -f lavfi -i "aevalsrc=\'{expr}\':s=44100:d={dur:.2f}" '
        f'-af "afade=t=in:st=0:d=1.2,afade=t=out:st={max(0, dur - 1.2):.2f}:d=1.2,volume=0.55" '
        f'-ar 44100 -ac 2 "{out_wav}"'
    )
    run(cmd)
    return out_wav


def mix_narration_and_music(narration_wav: str, music_wav: str, out_wav: str):
    cmd = (
        f'{FFMPEG} -y -i "{narration_wav}" -i "{music_wav}" '
        f'-filter_complex "[0:a]volume=1.6[a0];[1:a]volume=0.9[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2,'
        f'loudnorm=I=-14:TP=-1:LRA=11" -ar 44100 -ac 2 "{out_wav}"'
    )
    run(cmd)
    return out_wav
