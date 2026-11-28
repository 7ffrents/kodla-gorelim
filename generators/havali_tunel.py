"""Bolum 10: Dunya tunelinde HAVA var (Kodla Gorelim, video 10)
Bolum 8'in devami: ayni 5 tunel, ayni homojen Dunya; bu kez top havadan geciyor.
Fizik: a = -(g0/R) x - c v|v|, c = g0 / vt^2 (vt = ucus hizi, topun serbest dususte ulasabilecegi en yuksek hiz).
Hava yogunlugu yeryuzundeki gibi HER YERDE sabit (basitlestirme). RK4, dt = 1 sn; dt = 0,5 ile ayni sonuc (sim_check).
Olcut (sonuctan ONCE belirlendi): topun tunelin ortasina (x = 0) ilk varis suresi. Karsi uca cikan olursa ayrica sayilir.
Renkler yalnizca tuneli ayirir, sonuctan bagimsizdir. Havasiz hayalet toplar analitik (x = -L cos(wt)).
Kullanim: python havali_tunel.py <cikti_klasoru> [frames]"""
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
TMP = Path("/tmp/havali"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
BOLUM = 10

# ---------------- fizik ----------------
R_KM = 6371.0
G0 = 9.81e-3                                   # km/s^2
OMEGA = math.sqrt(G0 / R_KM)
T_HALF = math.pi / OMEGA                       # havasiz yari periyot (sn)
VT_MS = 55.0                                   # ucus hizi (m/s, ~200 km/sa)
VT = VT_MS / 1000.0
CDRAG = G0 / VT ** 2
D_RATIO = [0.90, 0.55, 0.0, -0.40, -0.80]
NT = len(D_RATIO)
HALF_LEN = np.array([R_KM * math.sqrt(1 - d * d) for d in D_RATIO])
LEN_KM = 2 * HALF_LEN
DT = 1.0

def acc(x, v):
    return -OMEGA ** 2 * x - CDRAG * v * np.abs(v)

x = -HALF_LEN.copy(); v = np.zeros(NT)
cross = np.full(NT, np.nan)
XS = [x.copy()]; VS = [v.copy()]
prog_at_half = None
i = 0
while True:
    k1x = v; k1v = acc(x, v)
    k2x = v + .5 * DT * k1v; k2v = acc(x + .5 * DT * k1x, k2x)
    k3x = v + .5 * DT * k2v; k3v = acc(x + .5 * DT * k2x, k3x)
    k4x = v + DT * k3v; k4v = acc(x + DT * k3x, k4x)
    xn = x + DT / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
    vn = v + DT / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
    t0_, t1_ = i * DT, (i + 1) * DT
    hit = (xn >= 0) & np.isnan(cross)
    cross[hit] = t0_ + DT * (-x[hit]) / (xn[hit] - x[hit])
    if prog_at_half is None and t1_ >= T_HALF:
        prog_at_half = (xn + HALF_LEN).copy()
    x, v = xn, vn
    XS.append(x.copy()); VS.append(v.copy())
    i += 1
    if not np.isnan(cross).any() and t1_ > cross.max() + 3600:
        break
X_HIST = np.array(XS); V_HIST = np.array(VS)
NSTEP = len(X_HIST)
T_END = (NSTEP - 1) * DT
# kontroller: kimse karsiya cikmadi, ortaya varis siralamasi hesaplandi
assert (X_HIST / HALF_LEN).max() < 0.05, "biri karsiya yaklasti"
order = np.argsort(cross)
print("ortaya varis (saat):", np.round(cross / 3600, 2).tolist(), "sira (tunel indeksi):", order.tolist())
print("havasiz yari periyot dk:", round(T_HALF / 60, 2), "42 dk'da yol km:", np.round(prog_at_half).astype(int).tolist())
print("karsi uca en yakin oran:", round(float((X_HIST / HALF_LEN).max()), 3), "tepe hiz m/s:", np.round(np.abs(V_HIST).max(axis=0) * 1000, 1).tolist())
assert order[0] == 0, "beklenen: en kisa tunel once varir"       # analitik: sure ~ sqrt(yari uzunluk)
assert cross.max() / 3600 > 40
# analitik kontrol: ucus hizinda yol: t = 2 sqrt(R L)/vt
ana = 2 * np.sqrt(R_KM * HALF_LEN) / VT
assert np.allclose(cross, ana, rtol=0.03), (cross / 3600, ana / 3600)

def sim_vac(s):
    """havasiz hayalet topun konumu (km): ucta durur."""
    s = np.minimum(s, T_HALF)
    return -HALF_LEN * np.cos(OMEGA * s)

# ---------------- gorsel ----------------
INK = (236, 240, 252)
AMBER = (251, 191, 36)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)
def fmt(xv, nd=1):
    return f"{xv:.{nd}f}".replace(".", ",")
def km_txt(k):
    return f"{int(round(k)):,}".replace(",", ".") + " km"
def ease(x_):
    x_ = max(0.0, min(1.0, x_)); return x_ * x_ * (3 - 2 * x_)

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def tr_int(n):
    n = int(n)
    if n == 0:
        return "sıfır"
    out = []
    if n >= 1000:
        th = n // 1000
        out.append(("" if th == 1 else tr_int(th) + " ") + "bin"); n %= 1000
    if n >= 100:
        h = n // 100
        out.append(("" if h == 1 else ONES[h] + " ") + "yüz"); n %= 100
    if n >= 10:
        out.append(TENS[n // 10]); n %= 10
    if n:
        out.append(ONES[n])
    return " ".join(s.strip() for s in out if s.strip())

CX, CY, RP = 540, 930, 420.0
KPX = RP / R_KM
COLS = [(56, 189, 248), (244, 114, 182), (250, 204, 21), (74, 222, 128), (251, 146, 60)]
rng = np.random.default_rng(10)
bg = Image.new("RGBA", (W, H), (7, 10, 24, 255)); bd = ImageDraw.Draw(bg)
for _ in range(220):
    sx, sy = int(rng.integers(0, W)), int(rng.integers(0, H)); b = int(rng.integers(90, 230)); sz = int(rng.integers(1, 4))
    bd.ellipse((sx, sy, sx + sz, sy + sz), fill=(b, b, min(255, b + 20)))
bd.ellipse((CX - RP - 10, CY - RP - 10, CX + RP + 10, CY + RP + 10), fill=(30, 110, 160))
bd.ellipse((CX - RP, CY - RP, CX + RP, CY + RP), fill=(92, 58, 42))
for f_ in (0.8, 0.6, 0.4, 0.2):
    rr = RP * f_
    bd.ellipse((CX - rr, CY - rr, CX + rr, CY + rr), outline=(104, 68, 50), width=3)
for i in range(NT):
    y = CY - D_RATIO[i] * RP
    hw = HALF_LEN[i] * KPX
    bd.rounded_rectangle((CX - hw, y - 11, CX + hw, y + 11), 11, fill=(60, 44, 66))     # havayla dolu tunel (mor-gri)
    lab = km_txt(LEN_KM[i]); ff = font(26)
    bd.text((CX - bd.textlength(lab, font=ff) / 2, y - 48), lab, font=ff, fill=(255, 236, 214))
# seri kimligi
bd.rounded_rectangle((270, 36, 810, 92), 28, fill=(30, 41, 80), outline=AMBER, width=3)
center(bd, 46, f"KODLA GÖRELİM · BÖLÜM {BOLUM}", font(31), AMBER)

# ---------------- anlatim ----------------
MIN_V = round(T_HALF / 60)
H_FIRST = round(cross.min() / 3600); H_LAST = round(cross.max() / 3600)
KM_MAX = int(round(prog_at_half.max(), -1))
TEXTS = [
    f"Dünya tüneline hava koydum. {tr_int(MIN_V)} dakikalık yolculuk, {tr_int(H_FIRST)} saate çıktı. Ve kimse karşıya çıkamadı.",
    f"Havasızken beş top aynı anda çıkıyordu. Şimdi {tr_int(MIN_V)} dakika sonra toplar en fazla {tr_int(KM_MAX)} kilometre gitti.",
    f"Hızlandırıyorum. Ortaya ilk en kısa tünel vardı: {tr_int(H_FIRST)} saatte. Dünyanın tam içinden geçen tünel en sona kaldı: {tr_int(H_LAST)} saat.",
    "Neden? Hava topa hız sınırı koyuyor. Sınırda ilerleyince, yolu kısa olan önce varıyor. Sonra hepsi ortada kalıyor.",
    "Havayı yarıya indirsem, biri karşıya çıkar mıydı? Yorumlara yaz. Yarın sabah altıda, Bölüm on bir: domino.",
]
def load_wav(p):
    out = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0
clips = []
for i, tx in enumerate(TEXTS):
    wp = TMP / f"v{i}.wav"
    synth(tx, wp, "fahrettin")
    clips.append(load_wav(wp))
dur = [len(c) / SR for c in clips]

DUR_B = 12.0
a1_off = (cross.min() - T_HALF) / (T_END - T_HALF) * DUR_B
starts = [0.2]
starts.append(starts[0] + dur[0] + 0.3)
starts.append(starts[1] + dur[1] + 0.3)
PA0 = 0.4
PA1 = starts[1] + 3.4                                  # havasiz hayaletler bu anda karsida
PB0 = max(PA1 + 1.2, starts[2] + 5.0 - a1_off)
PB1 = PB0 + DUR_B
starts.append(max(starts[2] + dur[2] + 0.3, PB1 - 1.0))
starts.append(starts[3] + dur[3] + 0.35)
V_Q = starts[4] - 0.2
TOTAL = starts[4] + dur[4] + 1.8
NFR = int(TOTAL * FPS)
for i in range(len(TEXTS)):
    print(f"anlatim {i}: {starts[i]:.1f}-{starts[i] + dur[i]:.1f}")
print("PA", round(PA0, 1), round(PA1, 1), "PB", round(PB0, 1), round(PB1, 1), "toplam", round(TOTAL, 1), "sn")
assert TOTAL < 58

def sim_time(vt):
    if vt < PA0:
        return 0.0
    if vt < PA1:
        return T_HALF * (vt - PA0) / (PA1 - PA0)
    if vt < PB0:
        return T_HALF
    u = min(1.0, (vt - PB0) / DUR_B)
    return T_HALF + (T_END - T_HALF) * u

def state_at(s):
    ix = min(int(s / DT), NSTEP - 1)
    return X_HIST[ix], V_HIST[ix]

def arrow(d, p0, p1, col, w=3):
    d.line((p0, p1), fill=col, width=w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s_ in (-0.5, 0.5):
        q = (p1[0] - 13 * math.cos(ang + s_), p1[1] - 13 * math.sin(ang + s_))
        d.line((p1, q), fill=col, width=w)

def clock_txt(s):
    if s < 2 * 3600:
        return fmt(s / 60) + " dk"
    return fmt(s / 3600) + " saat"

def render(vt):
    img = bg.copy(); d = ImageDraw.Draw(img)
    center(d, 108, "TÜNELE HAVA KOYDUM", font(80), INK)
    center(d, 212, f"{MIN_V} dakika  →  {H_FIRST} saat", font(60), AMBER)
    s = sim_time(vt)
    center(d, 300, "geçen süre: " + clock_txt(s), font(50), (255, 255, 255))
    xa, va = state_at(s)
    xv = sim_vac(s)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for i in range(NT):
        y = CY - D_RATIO[i] * RP
        bx = CX + xa[i] * KPX
        x_start = CX - HALF_LEN[i] * KPX
        od.rounded_rectangle((x_start, y - 6, max(bx, x_start + 2), y + 6), 6, fill=COLS[i] + (130,))
        # havasiz hayalet (yalniz ilk evrede ve sonra karsi ucta)
        if vt >= PA0 - 0.2 and vt < PB0 + 0.6:
            gx = CX + xv[i] * KPX
            od.ellipse((gx - 17, y - 17, gx + 17, y + 17), outline=(255, 255, 255, 210), width=3)
        od.ellipse((bx - 19, y - 19, bx + 19, y + 19), fill=COLS[i] + (255,), outline=(255, 255, 255, 255), width=3)
    img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
    for i in range(NT):
        y = CY - D_RATIO[i] * RP
        bx = CX + xa[i] * KPX
        if vt >= PA0 + 0.4:
            t_ = fmt(abs(va[i]) * 1000) + " m/s"
            ff = font(24); wtx = d.textlength(t_, font=ff)
            tx_ = min(max(bx - wtx / 2, 20), W - 20 - wtx)
            d.rounded_rectangle((tx_ - 8, y + 24, tx_ + wtx + 8, y + 56), 10, fill=(10, 14, 30))
            d.text((tx_, y + 26), t_, font=ff, fill=COLS[i])
        if PA1 - 0.3 <= vt < PB0 + 0.8:
            pk = xa[i] + HALF_LEN[i]
            t_ = f"{int(round(pk))} km"
            ff = font(26); wtx = d.textlength(t_, font=ff)
            sp_w = d.textlength(fmt(abs(va[i]) * 1000) + " m/s", font=font(24))
            sx_ = min(max(bx - sp_w / 2, 20), W - 20 - sp_w) + sp_w + 26
            d.text((min(sx_, W - 40 - wtx), y + 24), "yol: " + t_, font=ff, fill=(255, 255, 255))
    if vt < PB0 + 0.6:
        d.text((60, 1470 + 150), "beyaz halka: havasız tünelde aynı top", font=font(24, False), fill=(170, 184, 222))
    # alt panel
    if PA1 <= vt < PB0 + 0.6 and vt < V_Q:
        a_ = ease((vt - PA1) / 0.3)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((50, 1395, 1030, 1610), 30, fill=(250, 204, 21, int(245 * a_)))
        img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
        if a_ > 0.8:
            center(d, 1410, f"{MIN_V} DAKİKA SONRA", font(56), (24, 20, 8))
            center(d, 1485, "havasız: hepsi karşı uçta", font(40), (24, 20, 8))
            center(d, 1540, f"havalı: yalnız {int(round(prog_at_half.min()))}–{int(round(prog_at_half.max()))} km yol", font(40), (24, 20, 8))
    elif vt >= PB0 + 0.6 and vt < V_Q:
        # sonuc tablosu: ortaya varis sirasi
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((50, 1385, 1030, 1640), 30, fill=(10, 14, 30, 235))
        img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
        d.text((80, 1393), "Ortaya varış sırası", font=font(28), fill=(170, 184, 222))
        rank = 0
        for j in order:
            if cross[j] <= s:
                yy = 1432 + rank * 42
                d.ellipse((84, yy + 6, 112, yy + 34), fill=COLS[j])
                d.text((130, yy), f"{rank + 1}.  {km_txt(LEN_KM[j])} tüneli", font=font(30), fill=INK)
                tt_ = fmt(cross[j] / 3600) + " saat"
                d.text((1000 - d.textlength(tt_, font=font(30)), yy), tt_, font=font(30), fill=AMBER)
                rank += 1
    if vt >= V_Q:
        b = ease((vt - V_Q) / 0.4)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((30, 400, 1050, 1640), 36, fill=(7, 10, 24, int(250 * b)))
        img = Image.alpha_composite(img, ov); d = ImageDraw.Draw(img)
        if b > 0.5:
            center(d, 470, "Havayı YARIYA", font(80), (255, 255, 255), 30, 1050)
            center(d, 575, "indirsem?", font(80), AMBER, 30, 1050)
            center(d, 740, "Biri karşıya çıkar mıydı?", font(56), (255, 255, 255), 30, 1050)
            center(d, 840, "Yorumlara yaz", font(46), AMBER, 30, 1050)
            d.line((130, 960, 950, 960), fill=(60, 70, 110), width=3)
            center(d, 1010, "YARIN SABAH 06:00", font(54), (56, 189, 248), 30, 1050)
            center(d, 1095, f"BÖLÜM {BOLUM + 1}", font(86), AMBER, 30, 1050)
            center(d, 1215, "Domino", font(70), INK, 30, 1050)
            center(d, 1340, f"Bölüm {BOLUM - 1}: Zıplayan bilye mi, zıplamayan mı?", font(28, False), (150, 164, 205), 30, 1050)
            center(d, 1385, "Basitleştirme: Dünya her yerde aynı yoğunlukta, hava her yerde aynı", font(24, False), (130, 144, 185), 30, 1050)
    else:
        center(d, 1735, "Dünya ve hava her yerde aynı yoğunlukta (basitleştirme)", font(24, False), (130, 144, 185))
    return img.convert("RGB")

# ---------------- ses (ozgun sentez) ----------------
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

sfx = np.zeros(mix_len, dtype=np.float32)
BASE = [60, 64, 67, 72, 76]
simt_arr = np.array([sim_time(float(q)) for q in tt[::441]])                # 100 Hz ornek
simt_full = np.interp(tt, tt[::441], simt_arr)
ixs = np.minimum((simt_full / DT).astype(int), NSTEP - 1)
env_air = np.clip((tt - PA0) / 0.3, 0, 1) * np.clip((PB1 + 0.5 - tt) / 0.6, 0, 1)
for i in range(NT):
    spd = np.abs(V_HIST[ixs, i]) / VT                                          # 0..~1 (ucus hizina gore)
    f = mtof(BASE[i]) * (1 + 0.35 * spd)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sfx += (np.sin(ph) * 0.020 + np.sin(2 * ph) * 0.005) * env_air.astype(np.float32)
    # havasiz hayalet: ayni akor bir oktav yukari, hizla perde degisir, yalniz ilk evre
    gv = np.abs(OMEGA * HALF_LEN[i] * np.sin(OMEGA * np.minimum(simt_full, T_HALF))) / (OMEGA * HALF_LEN.max())
    fg = mtof(BASE[i] + 12) * (1 + 0.45 * gv)
    pg = 2 * np.pi * np.cumsum(fg) / SR
    genv = np.clip((tt - PA0) / 0.3, 0, 1) * np.clip((PA1 + 0.2 - tt) / 0.3, 0, 1)
    sfx += (np.sin(pg) * 0.010).astype(np.float32) * genv.astype(np.float32)
for i in range(NT):
    place(sfx, PA1, pluck(mtof(BASE[i] + 12), 1.2, 0.04, decay=3.5))
for rk, j in enumerate(order):
    s_arr = cross[j]
    v_arr = PB0 + (s_arr - T_HALF) / (T_END - T_HALF) * DUR_B
    place(sfx, v_arr, pluck(mtof(BASE[rk] + 12), 1.0, 0.07, decay=4))
place(sfx, V_Q, pluck(mtof(64), 1.2, 0.06, decay=3))

music = np.zeros(mix_len, dtype=np.float32)
beat = 60.0 / 108
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
    for ts in [0.1, 2.0, PA1 + 0.5, PB0 + 3.0, PB0 + 9.0, PB1 + 0.3, V_Q + 1.0]:
        render(ts).save(TMP / f"f_{ts:.1f}.png")
    print("kareler kaydedildi"); sys.exit()
silent = TMP / "silent.mp4"
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                       "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
for f in range(NFR):
    ff.stdin.write(render(f / FPS).tobytes())
    if f % 150 == 0:
        print("kare", f, "/", NFR, flush=True)
ff.stdin.close(); ff.wait()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wavp), "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT / "video.mp4")], check=True)
print("tamam", round(TOTAL, 1), "sn")
