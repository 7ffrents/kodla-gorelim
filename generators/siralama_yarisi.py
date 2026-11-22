"""Siralama algoritmalari yarisi: sesli + muzikli Short (Kodla Gorelim, video 3).
Kullanim: python siralama_yarisi.py <cikti_klasoru>
Gerekenler: numpy, pillow, ffmpeg, piper-tts (tools/tts.py)."""
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from tts import synth  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/siralama")
TMP.mkdir(exist_ok=True)

W, H, FPS = 1080, 1920, 30
SR = 44100
N = 50
K = 3                      # kare basina adim
BG = (15, 23, 42)
CYAN = (56, 189, 248)
AMBER = (245, 158, 11)
GREEN = (52, 211, 153)
WHITE = (241, 245, 249)
GREY = (100, 116, 139)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
F_T, F_L, F_S, F_B = font(70), font(46), font(36, False), font(60)

# ---------------- algoritmalar (jeneratorler) ----------------
def bubble(a):
    n = len(a)
    for i in range(n):
        for j in range(n - 1 - i):
            yield (j, j + 1)
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                yield (j, j + 1)

def insertion(a):
    for i in range(1, len(a)):
        j = i
        while j > 0:
            yield (j - 1, j)
            if a[j - 1] > a[j]:
                a[j - 1], a[j] = a[j], a[j - 1]
                yield (j - 1, j)
                j -= 1
            else:
                break

def quick(a, lo=0, hi=None):
    if hi is None:
        hi = len(a) - 1
    if lo >= hi:
        return
    p = a[hi]
    i = lo
    for j in range(lo, hi):
        yield (j, hi)
        if a[j] < p:
            a[i], a[j] = a[j], a[i]
            yield (i, j)
            i += 1
    a[i], a[hi] = a[hi], a[i]
    yield (i, hi)
    yield from quick(a, lo, i - 1)
    yield from quick(a, i + 1, hi)

random.seed(7)
base = list(range(1, N + 1))
random.shuffle(base)
algos = [("Kabarcık sıralama", bubble), ("Araya ekleme", insertion), ("Hızlı sıralama", quick)]
states = [list(base) for _ in algos]
gens = [fn(states[i]) for i, (_, fn) in enumerate(algos)]
# adim sayilarini onceden bul
steps = []
for _, fn in algos:
    tmp = list(base)
    steps.append(sum(1 for _ in fn(tmp)))
finish_step = steps
print("adimlar", steps)

T_INTRO = 5.0
f_intro = int(T_INTRO * FPS)
finish_frame = [f_intro + math.ceil(s / K) for s in steps]
f_end = max(finish_frame) + int(7.5 * FPS)
TOTAL = f_end
finish_t = [f / FPS for f in finish_frame]
print("bitis (sn)", [round(t, 1) for t in finish_t], "toplam", round(TOTAL / FPS, 1))

# ---------------- anlatim (TTS) ----------------
order = sorted(range(3), key=lambda i: finish_t[i])
names = {0: "Kabarcık sıralama", 1: "Araya ekleme", 2: "Hızlı sıralama"}
lines = [(0.4, "Üç sıralama algoritması. Aynı sayılar, aynı başlangıç. Hadi yarışsınlar.")]
lines.append((finish_t[order[0]] + 0.2, f"{names[order[0]]} birinci oldu."))
lines.append((finish_t[order[1]] + 0.2, f"{names[order[1]]} ikinci."))
lines.append((finish_t[order[2]] + 0.2, f"{names[order[2]]} en son bitirdi."))
lines.append((finish_t[order[2]] + 3.2, "Aynı iş, çok farklı hız. Algoritma seçimi işte bu yüzden önemli."))

def load_wav_44k(p):
    out = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0

total_len = TOTAL / FPS + 1.0
mix_len = int(total_len * SR)
voice = np.zeros(mix_len, dtype=np.float32)
cursor = 0.0
for i, (t, text) in enumerate(lines):
    wavp = TMP / f"v{i}.wav"
    synth(text, wavp, "fahrettin")
    clip = load_wav_44k(wavp)
    start = max(t, cursor + 0.25)
    s = int(start * SR)
    voice[s:s + len(clip)] += clip
    cursor = start + len(clip) / SR
    print(f"anlatim {i}: {start:.1f}-{cursor:.1f}  {text}")
assert cursor < total_len, "anlatim videodan uzun"

# ---------------- muzik (ozgun sentez) ----------------
def tone(freq, dur, kind="tri", vol=1.0, a=0.01, r=0.08):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "sine":
        w = np.sin(2 * np.pi * freq * t)
    elif kind == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(2 * np.pi * freq * t))
    else:
        w = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * 2 * freq * t)
    env = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    env[:na] = np.linspace(0, 1, na)
    env[-nr:] *= np.linspace(1, 0, nr)
    return (w * env * vol).astype(np.float32)

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)

music = np.zeros(mix_len, dtype=np.float32)
bpm = 92
beat = 60.0 / bpm
chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]   # Am F C G
bar = 0
tpos = 0.0
while tpos < total_len:
    ch = chords[bar % 4]
    # pad
    for m in ch:
        p = tone(mtof(m - 12), beat * 4, "sine", 0.10, a=0.3, r=0.6)
        s = int(tpos * SR)
        e = min(mix_len, s + len(p))
        music[s:e] += p[:e - s]
    # arpeji
    for k in range(8):
        m = ch[k % 3] + (12 if k % 4 == 3 else 0)
        p = tone(mtof(m), beat * 0.5, "tri", 0.10, a=0.005, r=0.12)
        s = int((tpos + k * beat / 2) * SR)
        e = min(mix_len, s + len(p))
        if s < mix_len:
            music[s:e] += p[:e - s]
    # bas
    b = tone(mtof(ch[0] - 12), beat * 2, "sine", 0.18, a=0.01, r=0.3)
    for off in (0, 2):
        s = int((tpos + off * beat) * SR)
        e = min(mix_len, s + len(b))
        if s < mix_len:
            music[s:e] += b[:e - s]
    tpos += beat * 4
    bar += 1

# ---------------- siralama sesleri + kareler ----------------
sfx = np.zeros((mix_len, 2), dtype=np.float32)
pans = [0.25, 0.5, 0.75]            # sol-orta-sag (0..1)

def add_blip(t, value, panel):
    freq = 220 * 2 ** (value / N * 2.0)          # 220..880 Hz
    p = tone(freq, 0.05, "sine", 0.05, a=0.004, r=0.03)
    s = int(t * SR)
    e = min(mix_len, s + len(p))
    if s >= mix_len:
        return
    l = math.cos(pans[panel] * math.pi / 2)
    r_ = math.sin(pans[panel] * math.pi / 2)
    sfx[s:e, 0] += p[:e - s] * l
    sfx[s:e, 1] += p[:e - s] * r_

PANEL_H = 380
PANEL_Y = [380, 860, 1340]
BAR_W = (W - 120) / N
counts = [0, 0, 0]
done = [False, False, False]

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
       "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", str(TMP / "v.mp4")]
pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)

def center(d, y, text, f, fill):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)

for frame in range(TOTAL):
    active = [None, None, None]
    if frame >= f_intro:
        for i in range(3):
            if done[i]:
                continue
            for k in range(K):
                try:
                    a, b = next(gens[i])
                except StopIteration:
                    done[i] = True
                    break
                counts[i] += 1
                active[i] = (a, b)
                t = frame / FPS + k / (K * FPS)
                add_blip(t, states[i][b], i)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center(d, 90, "Sıralama yarışı", F_T, WHITE)
    center(d, 180, "3 algoritma, aynı 50 sayı", F_L, CYAN)
    for i in range(3):
        y0 = PANEL_Y[i]
        d.text((60, y0 - 70), algos[i][0], font=F_L, fill=WHITE)
        if done[i]:
            cnt = f"{order.index(i) + 1}. oldu ✓  {counts[i]} adım"
            ccol = GREEN
        else:
            cnt = f"{counts[i]} adım"
            ccol = GREY
        wcnt = d.textlength(cnt, font=F_S)
        d.text((W - 60 - wcnt, y0 - 58), cnt, font=F_S, fill=ccol)
        for j, v in enumerate(states[i]):
            h = v / N * (PANEL_H - 20)
            x = 60 + j * BAR_W
            col = CYAN
            if done[i]:
                col = GREEN
            elif active[i] and j in active[i]:
                col = AMBER
            d.rectangle([x + 1, y0 + PANEL_H - h, x + BAR_W - 2, y0 + PANEL_H], fill=col)
    if frame >= TOTAL - int(5 * FPS):
        center(d, 1780, "Kodla Görelim", F_L, CYAN)
    pipe.stdin.write(img.tobytes())
pipe.stdin.close()
pipe.wait()

# ---------------- karisim ----------------
sfx_mono_l, sfx_mono_r = sfx[:, 0], sfx[:, 1]
mus = music * 0.9
# anlatim varken muzigi kis (basit ducking)
duck = np.ones(mix_len, dtype=np.float32)
vabs = np.abs(voice)
win = int(0.15 * SR)
env = np.convolve((vabs > 0.02).astype(np.float32), np.ones(win) / win, mode="same")
duck = 1.0 - 0.55 * np.clip(env * 3, 0, 1)
left = mus * duck + sfx_mono_l * 1.0 + voice * 1.1
right = mus * duck + sfx_mono_r * 1.0 + voice * 1.1
fade = np.ones(mix_len, dtype=np.float32)
nf = int(1.5 * SR)
fade[-nf:] = np.linspace(1, 0, nf)
stereo = np.stack([left * fade, right * fade], axis=1)
peak = np.max(np.abs(stereo))
stereo = stereo / max(1.0, peak / 0.9)
pcm = (stereo * 32767).astype(np.int16)
with wave.open(str(TMP / "mix.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(TMP / "v.mp4"), "-i", str(TMP / "mix.wav"),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                "-movflags", "+faststart", str(OUT / "video.mp4")], check=True)
print("bitti", OUT / "video.mp4", "sure", round(TOTAL / FPS, 1), "sn")
