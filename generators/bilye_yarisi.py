"""60 bilye, 3 boy: kim once bitirir? (Kodla Gorelim, video 4)
Kullanim: python bilye_yarisi.py <cikti_klasoru>
Fizik: bilye_sim.py. Gerekenler: numpy, pillow, ffmpeg, piper-tts (tools/tts.py)."""
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import bilye_sim as S  # noqa: E402
from tts import synth  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/bilye"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
SIMFPS = 60
OPEN_T = 1.8
SLOW = 0.5           # yaris kismi yavas cekim
SIM_T = 9.6
V_END = OPEN_T + (SIM_T - OPEN_T) / SLOW      # yaris bitis (video sn)
TOTAL = V_END + 9.0
NFR = int(TOTAL * FPS)

frames, rad, kinds, ft, events, pegs = S.simulate(SIM_T, SIMFPS, OPEN_T)
n = len(rad)
fin_order = [i for i in np.argsort(np.where(np.isnan(ft), 1e9, ft)) if not np.isnan(ft[i])]
nfin = len(fin_order)
cnt_fin = [int(np.sum(~np.isnan(ft) & (kinds == k))) for k in range(3)]
cnt_all = [int(np.sum(kinds == k)) for k in range(3)]
top10 = [int(np.sum(kinds[fin_order[:10]] == k)) for k in range(3)]
stuck = [cnt_all[k] - cnt_fin[k] for k in range(3)]
first_kind = int(kinds[fin_order[0]])
print("bitiren", cnt_fin, "ilk10", top10, "sikisan", stuck, "ilk", first_kind)

def v2sim(v):
    return v if v < OPEN_T else OPEN_T + (v - OPEN_T) * SLOW
def sim2v(t):
    return t if t < OPEN_T else OPEN_T + (t - OPEN_T) / SLOW

# ---------------- gorsel ----------------
BG = (13, 17, 32)
PANEL = (22, 28, 50)
COL = [(56, 189, 248), (251, 191, 36), (244, 63, 120)]      # kucuk, orta, buyuk
NAMES = ["küçük", "orta", "büyük"]
WHITE = (241, 245, 249); GREY = (120, 132, 160)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
F_BIG, F_MID, F_SM, F_XS = font(104), font(54), font(42), font(34, False)

def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)

bg = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(bg)
d.rounded_rectangle((S.XL - 14, S.GATE_Y - 520, S.XR + 14, S.FINISH_Y + 16), 28, fill=PANEL)
for (px, py) in pegs:
    d.ellipse((px - S.PEG_R, py - S.PEG_R, px + S.PEG_R, py + S.PEG_R), fill=(120, 132, 170))
# bitis cizgisi (damali)
for i in range(0, int(S.XR - S.XL), 28):
    d.rectangle((S.XL + i, S.FINISH_Y, S.XL + i + 14, S.FINISH_Y + 14), fill=WHITE if (i // 28) % 2 == 0 else (60, 66, 90))
d.text((S.XL + 6, S.FINISH_Y + 22), "BİTİŞ ÇİZGİSİ", font=F_XS, fill=GREY)

def draw_ball(dr, x, y, r, c):
    dr.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=tuple(int(v * 0.55) for v in c), width=max(2, int(r / 9)))
    hr = r * 0.32
    dr.ellipse((x - r * 0.45 - hr * 0.6, y - r * 0.45 - hr * 0.6, x - r * 0.45 + hr, y - r * 0.45 + hr), fill=tuple(min(255, int(v * 0.5 + 140)) for v in c))

def render(v):
    img = bg.copy(); d = ImageDraw.Draw(img)
    simt = min(v2sim(v), SIM_T - 1.0 / SIMFPS)
    fi = int(simt * SIMFPS)
    pos = frames[fi]
    # baslik
    center(d, 60, "60 BİLYE, 3 BOY", F_BIG, WHITE)
    center(d, 190, "Hangisi önce bitirir?", F_MID, (200, 210, 235))
    # gosterge
    xs = [150, 420, 700]
    for k in range(3):
        draw_ball(d, xs[k], 318, [11, 17, 25][k], COL[k])
        d.text((xs[k] + 40, 295), NAMES[k], font=F_SM, fill=COL[k])
    # bilyeler
    for i in range(n):
        x, y = pos[i]
        if x < -1000:
            continue
        draw_ball(d, x, y, rad[i], COL[kinds[i]])
    # kapi
    if v < OPEN_T:
        d.rectangle((S.XL, S.GATE_Y, S.XR, S.GATE_Y + 8), fill=WHITE)
    elif v < OPEN_T + 1.0:
        center(d, S.GATE_Y - 150 + 0, "", F_MID, WHITE)
    # siralama seridi
    fin_now = [i for i in fin_order if ft[i] <= simt]
    cx = S.XL + 12
    for i in fin_now:
        r = [7, 10, 13][kinds[i]]
        draw_ball(d, cx + r, 1432, r, COL[kinds[i]])
        cx += 24
    # sayaclar
    cf = [int(sum(1 for i in fin_now if kinds[i] == k)) for k in range(3)]
    for k in range(3):
        d.text((S.XL + 10 + k * 300, 1480), f"{NAMES[k]}: {cf[k]}", font=F_SM, fill=COL[k])
    # sonuc paneli
    if v >= V_END + 0.4:
        a = min(1.0, (v - V_END - 0.4) / 0.4)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((40, 560, 960, 1230), 34, fill=(8, 11, 24, int(235 * a)))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)
        if a > 0.5:
            center(d, 600, "SONUÇ", F_BIG, WHITE, 40, 960)
            center(d, 740, f"İlk 10'un {top10[0]}'u küçük", F_MID, COL[0], 40, 960)
            center(d, 810, f"{top10[1]}'u orta, {top10[2]}'u büyük", F_MID, (200, 210, 235), 40, 960)
            center(d, 930, f"Büyüklerin {stuck[2]} / {cnt_all[2]}'i", F_MID, COL[2], 40, 960)
            center(d, 1000, "dar geçitte sıkıştı", F_MID, COL[2], 40, 960)
        if v >= V_END + 3.2:
            center(d, 1110, "Büyük bilye kazanabilir mi?", font(46), (255, 236, 160), 40, 960)
            center(d, 1166, "Tahminin yorumlarda!", font(46), (255, 236, 160), 40, 960)
    return img

# ---------------- anlatim ----------------
t_first = sim2v(ft[fin_order[0]])
lines = [
    (0.3, "Altmış bilye, üç boy. Hangisi önce bitirir?"),
    (t_first + 0.1, f"İlk bitiren {NAMES[first_kind]} bilye."),
    (sim2v(5.0), "Büyükler dar geçitte sıkışıyor."),
    (V_END + 0.6, f"İlk on bitirenin {top10[0]} tanesi küçük. Büyüklerin {stuck[2]} tanesi sıkıştı."),
    (V_END + 5.0, "Peki büyük bir bilye hiç kazanabilir mi? Tahminini yaz."),
]
def load_wav(p):
    out = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0

mix_len = int((TOTAL + 0.5) * SR)
voice = np.zeros(mix_len, dtype=np.float32)
cursor = 0.0
spans = []
for i, (t, text) in enumerate(lines):
    wp = TMP / f"v{i}.wav"
    synth(text, wp, "fahrettin")
    clip = load_wav(wp)
    start = max(t, cursor + 0.25)
    s = int(start * SR)
    voice[s:s + len(clip)] += clip
    cursor = start + len(clip) / SR
    spans.append((start, cursor))
    print(f"anlatim {i}: {start:.1f}-{cursor:.1f}  {text}")
assert cursor < TOTAL - 0.3, "anlatim videodan uzun"

# ---------------- ses (ozgun sentez) ----------------
def pluck(freq, dur, vol, decay=14.0):
    nn = int(dur * SR); t = np.arange(nn) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 10)
    env = np.exp(-t * decay); env[:40] *= np.linspace(0, 1, 40)
    return (w * env * vol).astype(np.float32)

def place(buf, t, clip):
    s = int(t * SR)
    if s < 0 or s >= len(buf):
        return
    e = min(len(buf), s + len(clip))
    buf[s:e] += clip[:e - s]

PENT = [0, 2, 4, 7, 9]
def note(base, k):
    return base + 12 * (k // 5) + PENT[k % 5]
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

sfx = np.zeros(mix_len, dtype=np.float32)
rng = np.random.default_rng(5)
last = {0: -1, 1: -1, 2: -1}
for (t, kind, strength) in events:
    v = sim2v(t)
    if v - last[kind] < 0.04:
        continue
    last[kind] = v
    base = [84, 72, 55][kind]
    m = note(base, int(rng.integers(0, 5)))
    place(sfx, v, pluck(mtof(m), 0.25, 0.05 + 0.07 * strength, decay=[22, 16, 11][kind]))
# bitis zilleri: bitis sirasi arttikca yukselen pentatonik
for idx, i in enumerate(fin_order):
    v = sim2v(ft[i])
    m = note(72, min(idx // 2, 9))
    place(sfx, v, pluck(mtof(m), 0.5, 0.09, decay=7.0))
# kapi acilis: kisa gurultu patlamasi
nz = (rng.standard_normal(int(0.25 * SR)) * np.exp(-np.arange(int(0.25 * SR)) / SR * 14) * 0.12).astype(np.float32)
place(sfx, OPEN_T, nz)
# final akoru
for m in (60, 64, 67, 72):
    place(sfx, V_END + 0.4, pluck(mtof(m), 1.6, 0.07, decay=2.5))

# hafif muzik: majör pentatonik, 120 bpm
music = np.zeros(mix_len, dtype=np.float32)
beat = 0.5
prog = [0, -3, -5, -2]
t = 0.0; bar = 0
while t < TOTAL:
    root = 48 + prog[bar % 4]
    place(music, t, pluck(mtof(root), 1.0, 0.09, decay=4.0))
    for k in range(8):
        m = root + 12 + [0, 4, 7, 12, 7, 4, 9, 7][k]
        place(music, t + k * beat / 2, pluck(mtof(m), 0.35, 0.035, decay=12.0))
    t += beat * 4; bar += 1
# anlatim sirasinda muzigi kis
duck = np.ones(mix_len, dtype=np.float32)
for a, b in spans:
    duck[int(max(0, a - 0.1) * SR):int((b + 0.2) * SR)] = 0.35
duck = np.convolve(duck, np.ones(2205) / 2205, mode="same")
mix = voice * 1.0 + sfx * (0.8 + 0.2 * (1 - duck)) + music * duck
mix = np.tanh(mix * 1.1) * 0.95
mix[int(TOTAL * SR):] = 0
wavp = TMP / "mix.wav"
with wave.open(str(wavp), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix[:int(TOTAL * SR)] * 32767).astype(np.int16).tobytes())

# ---------------- video ----------------
silent = TMP / "silent.mp4"
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                       "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
for f in range(NFR):
    ff.stdin.write(render(f / FPS).tobytes())
    if f % 150 == 0:
        print("kare", f, "/", NFR, flush=True)
ff.stdin.close(); ff.wait()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wavp), "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT / "video.mp4")], check=True)
print("tamam", round(TOTAL, 1), "sn")
