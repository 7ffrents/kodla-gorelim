"""Dunya'yi delip 5 top birakiyoruz (Kodla Gorelim, video 8)
Fizik: homojen yogunluklu Dunya'nin icinde yercekimi ivmesi g(r) = g0 * r / R (merkeze dogru).
Bir tunel (kiris) boyunca bilesen: a = -(g0/R) * x  -> basit harmonik hareket, w = sqrt(g0/R).
Yari periyot = pi / w ~ 42,2 dk, tunelin uzunlugundan BAGIMSIZ. Burada leapfrog ile sayisal
entegrasyon yapilir, analitik cozumle dogrulanir. Hava yok, Dunya homojen (basitlestirme).
Renkler yalnizca tuneli ayirir, sonuctan bagimsizdir.
Kullanim: python dunya_tunel.py <cikti_klasoru> [frames]"""
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
from tts import synth  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/dunya"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100

# ---------------- fizik ----------------
R_KM = 6371.0
G0 = 9.81e-3                                   # km/s^2
OMEGA = math.sqrt(G0 / R_KM)
T_HALF = math.pi / OMEGA                       # saniye
D_RATIO = [0.90, 0.55, 0.0, -0.40, -0.80]      # tunelin merkeze uzakligi / R
NT = len(D_RATIO)
HALF_LEN = np.array([R_KM * math.sqrt(1 - d * d) for d in D_RATIO])    # km
LEN_KM = 2 * HALF_LEN
DT = 1.0                                       # sim saniyesi
NSTEP = int(T_HALF / DT) + 400
x = -HALF_LEN.copy(); v = np.zeros(NT)
X_HIST = np.zeros((NSTEP, NT)); V_HIST = np.zeros((NSTEP, NT))
a = -OMEGA ** 2 * x
finish = np.full(NT, np.nan)
for i in range(NSTEP):
    v += 0.5 * DT * a
    x += DT * v
    a = -OMEGA ** 2 * x
    v += 0.5 * DT * a
    X_HIST[i] = x; V_HIST[i] = v
    t = (i + 1) * DT
    done = (v <= 0) & (t > 60) & np.isnan(finish)          # varis: hiz isaret degistirir (karsi uc)
    finish[done] = t
assert not np.isnan(finish).any()
assert np.allclose(finish, T_HALF, atol=3.0), (finish, T_HALF)       # hepsi ayni anda (<=1 adim)
vmax = OMEGA * HALF_LEN
assert np.allclose(np.abs(V_HIST).max(axis=0), vmax, rtol=0.01)
print("yari periyot dk:", round(T_HALF / 60, 2), "bitis dk:", np.round(finish / 60, 2).tolist())
print("tunel km:", np.round(LEN_KM).astype(int).tolist(), "tepe hiz km/s:", np.round(vmax, 2).tolist())
T_RACE = 14.0                                  # videoda sn
SCALE = T_HALF / T_RACE                        # sim sn / video sn
T0 = 1.2

# ---------------- gorsel ----------------
INK = (236, 240, 252)
AMBER = (251, 191, 36)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
F_BIG, F_MID, F_SM = font(100), font(48), font(32)
def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)
def fmt(xv, nd=1):
    return f"{xv:.{nd}f}".replace(".", ",")
def km_txt(k):
    return f"{int(round(k)):,}".replace(",", ".") + " km"

CX, CY, RP = 540, 960, 420.0
KPX = RP / R_KM
COLS = [(56, 189, 248), (244, 114, 182), (250, 204, 21), (74, 222, 128), (251, 146, 60)]

rng = np.random.default_rng(8)
bg = Image.new("RGBA", (W, H), (7, 10, 24, 255)); bd = ImageDraw.Draw(bg)
for _ in range(220):
    sx, sy = int(rng.integers(0, W)), int(rng.integers(0, H)); b = int(rng.integers(90, 230)); sz = int(rng.integers(1, 4))
    bd.ellipse((sx, sy, sx + sz, sy + sz), fill=(b, b, min(255, b + 20)))
# Dunya: kabuk halkasi + kayac + ince halkalar
bd.ellipse((CX - RP - 10, CY - RP - 10, CX + RP + 10, CY + RP + 10), fill=(30, 110, 160))
bd.ellipse((CX - RP, CY - RP, CX + RP, CY + RP), fill=(92, 58, 42))
for f_ in (0.8, 0.6, 0.4, 0.2):
    rr = RP * f_
    bd.ellipse((CX - rr, CY - rr, CX + rr, CY + rr), outline=(104, 68, 50), width=3)
# tuneller
for i in range(NT):
    y = CY - D_RATIO[i] * RP
    hw = HALF_LEN[i] * KPX
    bd.rounded_rectangle((CX - hw, y - 11, CX + hw, y + 11), 11, fill=(24, 16, 14))
    lab = km_txt(LEN_KM[i])
    ff = font(26)
    bd.text((CX - bd.textlength(lab, font=ff) / 2, y - 48), lab, font=ff, fill=(255, 236, 214))
bd.line((CX - 6, CY - 6, CX + 6, CY + 6), fill=(255, 255, 255), width=0)

def ease(x_):
    x_ = max(0.0, min(1.0, x_)); return x_ * x_ * (3 - 2 * x_)

# ---------------- anlatim ----------------
t_end_race = T0 + T_RACE
def load_wav(p):
    out = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0

TEXTS = [
    "Dünya'yı delip beş tünel açtım. Beş topu aynı anda bıraktım. Hangisi önce karşıya çıkar?",
    "Uzun tünelde top müthiş hızlanıyor. Kısa tünelde ise yavaş kalıyor.",
    "Ve hepsi tam aynı anda çıktı. Kırk iki dakika.",
    "Uzun yol, daha çok hızlanma demek. İkisi tam dengeleniyor. Tünel nereden geçerse geçsin, süre aynı.",
    "Peki tünelde hava olsaydı, hangisi kazanırdı? Yaz bakalım.",
]
clips = []
for i, tx in enumerate(TEXTS):
    wp = TMP / f"v{i}.wav"
    synth(tx, wp, "fahrettin")
    clips.append(load_wav(wp))
dur = [len(c) / SR for c in clips]
want = [0.3, T0 + 6.4, t_end_race - 0.9, 0.0, 0.0]
starts = []; cursor = 0.0
for i in range(len(TEXTS)):
    st = max(want[i], cursor + (0.3 if i else 0.0))
    if i in (3, 4):
        st = cursor + 0.45
    starts.append(st); cursor = st + dur[i]
    print(f"anlatim {i}: {st:.1f}-{cursor:.1f}  {TEXTS[i]}")
V_SAME = max(t_end_race - 0.2, 0)
V_Q = starts[4] - 0.2
TOTAL = cursor + 2.0
NFR = int(TOTAL * FPS)
print("toplam", round(TOTAL, 1), "sn")

# ---------------- kare ----------------
def sim_idx(vt):
    tr = vt - T0
    if tr <= 0:
        return -1
    return min(int(tr * SCALE / DT) - 1, NSTEP - 1)

def arrow(d, p0, p1, col, w=3):
    d.line((p0, p1), fill=col, width=w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s_ in (-0.5, 0.5):
        q = (p1[0] - 13 * math.cos(ang + s_), p1[1] - 13 * math.sin(ang + s_))
        d.line((p1, q), fill=col, width=w)

def render(vt):
    img = bg.copy(); d = ImageDraw.Draw(img)
    center(d, 50, "DÜNYAYI DELDİM", F_BIG, INK)
    center(d, 175, "5 tünel, 5 top, aynı anda bırakıldı", F_MID, (170, 184, 222))
    center(d, 240, "Hangisi önce çıkar?", F_MID, AMBER)
    idx = sim_idx(vt)
    sim_t = 0.0 if idx < 0 else min((idx + 1) * DT, T_HALF)
    # saat
    center(d, 330, "geçen süre: " + fmt(sim_t / 60) + " dk", font(50), (255, 255, 255))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for i in range(NT):
        y = CY - D_RATIO[i] * RP
        xi = -HALF_LEN[i] if idx < 0 else min(X_HIST[idx, i], HALF_LEN[i])
        vi = 0.0 if idx < 0 else abs(V_HIST[idx, i])
        bx = CX + xi * KPX
        # iz
        x_start = CX - HALF_LEN[i] * KPX
        od.rounded_rectangle((x_start, y - 6, max(bx, x_start + 2), y + 6), 6, fill=COLS[i] + (120,))
        # merkeze cekim oku
        rr = math.hypot(xi * KPX, y - CY) if True else 0
        if rr > 8 and sim_t < T_HALF - 1:
            ux, uy = (CX - bx) / rr, (CY - y) / rr
            ln = 95 * (rr / RP)
            arrow(od, (bx, y), (bx + ux * ln, y + uy * ln), (255, 255, 255, 170), 3)
        od.ellipse((bx - 19, y - 19, bx + 19, y + 19), fill=COLS[i] + (255,), outline=(255, 255, 255, 255), width=3)
    img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
    # hiz yazilari (topun ustunde)
    for i in range(NT):
        y = CY - D_RATIO[i] * RP
        xi = -HALF_LEN[i] if idx < 0 else min(X_HIST[idx, i], HALF_LEN[i])
        vi = 0.0 if idx < 0 else abs(V_HIST[idx, i])
        if vt >= T0 + 0.4 and sim_t < T_HALF - 1:
            bx = CX + xi * KPX
            t_ = fmt(vi) + " km/s"
            ff = font(24)
            wtx = d.textlength(t_, font=ff)
            tx_ = min(max(bx - wtx / 2, 20), W - 20 - wtx)
            d.rounded_rectangle((tx_ - 8, y + 24, tx_ + wtx + 8, y + 56), 10, fill=(10, 14, 30))
            d.text((tx_, y + 26), t_, font=ff, fill=COLS[i])
    # alt panel: ayni anda
    if V_SAME <= vt < V_Q:
        a_ = ease((vt - V_SAME) / 0.3)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((60, 1430, 1020, 1690), 30, fill=(250, 204, 21, int(245 * a_)))
        img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
        if a_ > 0.8:
            center(d, 1450, "HEPSİ AYNI ANDA!", font(76), (24, 20, 8))
            center(d, 1545, fmt(T_HALF / 60) + " dakika", font(64), (24, 20, 8))
            center(d, 1630, f"en hızlı {fmt(vmax.max())} km/s · en yavaş {fmt(vmax.min())} km/s", font(30, False), (60, 46, 10))
    # soru karti
    if vt >= V_Q:
        b = ease((vt - V_Q) / 0.4)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((30, 400, 1050, 1640), 36, fill=(7, 10, 24, int(250 * b)))
        img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
        if b > 0.5:
            center(d, 560, "Tünelde HAVA", font(84), (255, 255, 255), 30, 1050)
            center(d, 670, "olsaydı?", font(84), AMBER, 30, 1050)
            center(d, 840, "Hangi top kazanırdı?", font(60), (255, 255, 255), 30, 1050)
            for i in range(NT):
                xx = 200 + i * 170
                d.ellipse((xx - 28, 1000 - 28, xx + 28, 1000 + 28), fill=COLS[i], outline=(255, 255, 255), width=3)
                center(d, 1040, km_txt(LEN_KM[i]).replace(" km", ""), font(24), (190, 200, 230), xx - 70, xx + 70)
            center(d, 1140, "Tahminini yorumlara yaz", font(46), AMBER, 30, 1050)
            center(d, 1300, "Basitleştirme: Dünya her yerde aynı yoğunlukta", font(27, False), (150, 164, 205), 30, 1050)
    else:
        center(d, 1740, "Dünya her yerde aynı yoğunlukta, hava yok (basitleştirme)", font(24, False), (130, 144, 185))
    return img.convert("RGB")

# ---------------- ses ----------------
def pluck(freq, dur_, vol, decay=14.0):
    nn = int(dur_ * SR); t = np.arange(nn) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 10)
    env = np.exp(-t * decay); env[:40] *= np.linspace(0, 1, 40)
    return (w * env * vol).astype(np.float32)

def blip(freq, dur_, vol):
    nn = int(dur_ * SR); t = np.arange(nn) / SR
    w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.6 + 0.4 * np.sin(2 * np.pi * freq * t)
    env = np.exp(-t * 9); env[:30] *= np.linspace(0, 1, 30)
    return (w * env * vol).astype(np.float32)

def place(buf, t, clip):
    s0 = int(t * SR)
    if s0 < 0 or s0 >= len(buf):
        return
    e = min(len(buf), s0 + len(clip))
    buf[s0:e] += clip[:e - s0]

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

mix_len = int((TOTAL + 0.5) * SR)
tt = np.arange(mix_len) / SR
voice = np.zeros(mix_len, dtype=np.float32); spans = []
for st, c in zip(starts, clips):
    place(voice, st, c); spans.append((st, st + len(c) / SR))

# her top bir ses: perde, topun hizi ile yukselir ve alcalir; varista hepsi ayni anda cinlar
sfx = np.zeros(mix_len, dtype=np.float32)
BASE = [60, 64, 67, 72, 76]                       # C majör akoru (tunel sirasi)
tr_ = np.clip(tt - T0, 0, T_RACE)
sim_ = tr_ * SCALE
for i in range(NT):
    spd = np.abs(-OMEGA * HALF_LEN[i] * np.sin(OMEGA * sim_))        # analitik hiz (yalniz ses icin)
    spd = np.abs(OMEGA * HALF_LEN[i] * np.sin(OMEGA * sim_))
    f = mtof(BASE[i]) * (1 + 0.55 * spd / vmax.max())
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.clip((tt - T0) / 0.3, 0, 1) * np.clip((t_end_race + 0.4 - tt) / 0.6, 0, 1)
    sfx += (np.sin(ph) * 0.020 + np.sin(2 * ph) * 0.006) * env.astype(np.float32)
for i in range(NT):
    place(sfx, t_end_race, pluck(mtof(BASE[i] + 12), 1.4, 0.05, decay=3.5))
place(sfx, t_end_race, pluck(mtof(48), 1.6, 0.10, decay=3))
place(sfx, V_Q, pluck(mtof(64), 1.2, 0.06, decay=3))

music = np.zeros(mix_len, dtype=np.float32)
beat = 60.0 / 104
prog = [0, -4, -7, -2]
t = 0.0; bar = 0
while t < TOTAL:
    root = 41 + prog[bar % 4]
    for q in range(4):
        place(music, t + q * beat, blip(mtof(root), 0.3, 0.05) if q % 2 == 0 else blip(mtof(root + 12), 0.16, 0.02))
    for q in range(8):
        place(music, t + q * beat / 2, pluck(mtof(root + 24 + [0, 4, 7, 12][q % 4]), 0.22, 0.010, decay=16))
    t += 4 * beat; bar += 1
duck = np.ones(mix_len, dtype=np.float32)
for a_, b_ in spans:
    duck[int(max(0, a_ - 0.1) * SR):int((b_ + 0.2) * SR)] = 0.35
duck = np.convolve(duck, np.ones(2205) / 2205, mode="same")
mix = voice * 1.0 + sfx * (0.7 + 0.3 * (1 - duck)) + music * duck
mix = np.tanh(mix * 1.1) * 0.95
mix[int(TOTAL * SR):] = 0
wavp = TMP / "mix.wav"
with wave.open(str(wavp), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix[:int(TOTAL * SR)] * 32767).astype(np.int16).tobytes())

# ---------------- video ----------------
if len(sys.argv) > 2 and sys.argv[2] == "frames":
    for ts in [0.1, T0 + 3.0, T0 + 7.0, t_end_race - 0.5, t_end_race + 1.5, V_Q + 1.0]:
        render(ts).save(TMP / f"f_{ts:.1f}.png")
    print("kareler kaydedildi"); sys.exit()
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
