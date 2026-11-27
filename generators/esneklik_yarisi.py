"""Bolum 9: Zipalayan bilye mi, zipalamayan mi? (Kodla Gorelim, video 9)
60 bilye, ayni boy; 6 esneklik seviyesi x 10 bilye. Fizik: esneklik_sim.py.
Renk = esneklik seviyesi (baslangictan beri bilinir, sonuctan bagimsiz). Sonuc canli sayac + 8 farkli dizilis ortalamasi.
Kullanim: python esneklik_yarisi.py <cikti_klasoru> [frames]"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import esneklik_sim as S  # noqa: E402
from tts import synth  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/esneklik"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100
SIMFPS = 60
OPEN_T = 1.2
CUT = 8.0                    # canli sayacin gosterildigi sure (kapi acildiktan sonra) sn
CUT_SIM = OPEN_T + CUT
SIM_T = 14.0
NLEV = len(S.LEVELS)
SEED_SHOW = 1
SEEDS_ALL = list(range(1, 9))

# ---- ana yaris + 8 dizilis ortalamasi ----
# Olcut: her seviyedeki 10 bilyenin YARISI (5. bilye) kapi acildiktan kac sn sonra indi. Sabit bir kesme saati yok.
frames = lev = ft = events = pegs = None
T5 = []
for sd in SEEDS_ALL:
    fr, lv, f_, ev, pg = S.simulate(SIM_T, SIMFPS, OPEN_T, seed=sd)
    t5 = []
    for k in range(NLEV):
        arr = np.sort(np.where(np.isnan(f_[lv == k]), 1e9, f_[lv == k]))
        t5.append(float(arr[4] - OPEN_T))
    T5.append(t5)
    if sd == SEED_SHOW:
        frames, lev, ft, events, pegs = fr, lv, f_, ev, pg
T5 = np.array(T5)
avg = T5.mean(0)
shown = T5[SEEDS_ALL.index(SEED_SHOW)]
print("gosterilen yaris t5:", np.round(shown, 2).tolist())
print("8 dizilis ortalamasi t5:", np.round(avg, 2).tolist())
print("en hizli seviye (dizilis basina):", [int(np.argmin(r)) for r in T5])
assert shown.max() < CUT - 0.2, "kesme saati cok erken"
assert shown[0] < shown[-1] - 2 and avg[0] < avg[-1] - 1.5, "beklenen egilim yok"
# yukari hareket orani (gosterilen yaris): kapi acildiktan sonra, hareketli karelerde dy < 0
dy = np.diff(frames[:, :, 1], axis=0)
okm = (frames[1:, :, 1] > -1000) & (frames[:-1, :, 1] > -1000) & (np.arange(len(frames) - 1)[:, None] / SIMFPS > OPEN_T)
UP = []
for k in range(NLEV):
    dd_ = dy[:, lev == k][okm[:, lev == k]]
    UP.append(float(np.mean(dd_ < -0.5)) * 100)
UP = np.array(UP)
print("yukari giden zaman %:", np.round(UP, 1).tolist())
assert UP[-1] > 3 * UP[0]

def fmt1(x):
    return f"{x:.1f}".replace(".", ",")
ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def tr_int(n):
    n = int(n)
    if n == 0:
        return "sıfır"
    return (TENS[n // 10] + " " + ONES[n % 10]).strip()
def say_num(x):
    r = round(x, 1)
    ip = int(r); fp = int(round((r - ip) * 10))
    return tr_int(ip) if fp == 0 else f"{tr_int(ip)} virgül {tr_int(fp)}"

# ---------------- anlatim ----------------
TEXTS = [
    "Altmış bilye düşüyor. Zıplayanlar mı önce iner, zıplamayanlar mı?",
    "Mavi hiç zıplamıyor. Kırmızı sekmeye bayılıyor. Bakalım çivilerde kim ne yapacak.",
    f"Zıplamayanlar önde! Mavilerin yarısı {say_num(shown[0])} saniyede indi, kırmızıların yarısı {say_num(shown[-1])}.",
    f"Neden? Çünkü zıplayan bilye çiviye çarpıp yukarı seker. Kırmızılar zamanlarının yüzde {tr_int(round(UP[-1]))} kadarını yukarı giderek geçirdi. Mavilerde bu yalnızca yüzde {tr_int(round(UP[0]))}.",
    f"Sekiz farklı dizilişin ortalaması da aynı yönde: mavi {say_num(avg[0])} saniye, kırmızı {say_num(avg[-1])} saniye.",
    "Sence çivi olmasaydı kim kazanırdı? Yorumlara yaz. Yarın sabah altıda, Bölüm on: Dünya tüneline hava koyuyoruz.",
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
starts = [0.15]
starts.append(starts[0] + dur[0] + 0.35)
starts.append(max(starts[1] + dur[1] + 0.25, CUT_SIM - 0.3))
for i in range(3, len(TEXTS)):
    starts.append(starts[i - 1] + dur[i - 1] + 0.4)
for i in range(len(TEXTS)):
    print(f"anlatim {i}: {starts[i]:.1f}-{starts[i] + dur[i]:.1f}  {TEXTS[i]}")
V_RES, V_WHY, V_AVG, V_Q = starts[2] - 0.1, starts[3] - 0.1, starts[4] - 0.1, starts[5] - 0.1
TOTAL = starts[5] + dur[5] + 1.8
NFR = int(TOTAL * FPS)
print("toplam", round(TOTAL, 1), "sn; V_RES", round(V_RES, 1))

# ---------------- gorsel ----------------
BG = (12, 16, 30)
PANEL = (22, 28, 50)
INK = (241, 245, 249); GREY = (130, 142, 172); AMB = (251, 191, 36)
COLS = [(56, 189, 248), (45, 212, 191), (163, 230, 53), (250, 204, 21), (251, 146, 60), (244, 63, 94)]
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

BOARD_TOP = 300
bg = Image.new("RGB", (W, H), BG)
bd = ImageDraw.Draw(bg)
bd.rounded_rectangle((S.XL - 14, BOARD_TOP, S.XR + 14, S.FINISH_Y + 16), 28, fill=PANEL)
for (px, py) in pegs:
    bd.ellipse((px - S.PEG_R, py - S.PEG_R, px + S.PEG_R, py + S.PEG_R), fill=(120, 132, 170))
for i in range(0, int(S.XR - S.XL), 28):
    bd.rectangle((S.XL + i, S.FINISH_Y, S.XL + i + 14, S.FINISH_Y + 14), fill=INK if (i // 28) % 2 == 0 else (60, 66, 90))
# sabit ust bant (seri kimligi)
bd.rounded_rectangle((300, 36, 780, 92), 28, fill=(30, 41, 80), outline=AMB, width=3)
center(bd, 46, "KODLA GÖRELİM · BÖLÜM 9", font(31), AMB)
center(bd, 112, "Zıplayan mı?", font(84), INK)
center(bd, 208, "Zıplamayan mı?", font(84), (56, 189, 248))

def draw_ball(dr, x, y, r, c):
    dr.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=tuple(int(v * 0.5) for v in c), width=2)
    hr = r * 0.32
    dr.ellipse((x - r * 0.45 - hr * 0.6, y - r * 0.45 - hr * 0.6, x - r * 0.45 + hr, y - r * 0.45 + hr),
               fill=tuple(min(255, int(v * 0.5 + 140)) for v in c))

LABEL = [f"%{round(e * 100)}" for e in S.LEVELS]

def counts_at(sim_t):
    return [int(np.sum((lev == k) & (ft <= sim_t))) for k in range(NLEV)]

def render(v):
    img = bg.copy(); d = ImageDraw.Draw(img)
    simt = min(v, SIM_T - 1.0 / SIMFPS)
    pos = frames[int(simt * SIMFPS)]
    for i in range(len(lev)):
        x, y = pos[i]
        if y > -1000:
            draw_ball(d, x, y, S.RAD, COLS[lev[i]])
    # kapi
    if v < OPEN_T:
        d.rectangle((S.XL, S.GATE_Y, S.XR, S.GATE_Y + 6), fill=AMB)
    # sure sayaci
    clk = max(0.0, min(CUT, v - OPEN_T))
    bd2 = f"{clk:.1f}".replace(".", ",")
    if v < V_RES:
        d.rounded_rectangle((690, 316, 950, 380), 18, fill=(30, 41, 80))
        d.text((708, 322), f"SÜRE {bd2}", font=font(42), fill=AMB)
    # alt satir: esneklik seviyeleri + bitiren sayisi
    cnt = counts_at(min(simt, CUT_SIM))
    d.text((60, 1455), "Şu ana kadar bitiren (10 bilyeden)", font=font(30), fill=GREY)
    colw = (S.XR - S.XL) / NLEV
    for k in range(NLEV):
        x0 = S.XL + colw * k
        cx = x0 + colw / 2
        d.ellipse((cx - 14, 1506, cx + 14, 1534), fill=COLS[k])
        center(d, 1538, LABEL[k], font(30), INK, x0, x0 + colw)
        center(d, 1572, str(cnt[k]), font(64), COLS[k], x0, x0 + colw)
    center(d, 1648, "renk = zıplama gücü (yarıştan önce verildi)", font(24, False), GREY)

    # --- paneller ---
    def panel(a):
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((30, 330, 1050, 1420), 36, fill=(10, 14, 30, int(244 * a)))
        return Image.alpha_composite(img.convert("RGBA"), ov)

    def bars(img, t0, title, sub, vals, vmax, lab, best_low=False, foot=""):
        d = ImageDraw.Draw(img)
        center(d, 375, title, font(48), INK, 30, 1050)
        center(d, 445, sub, font(32, False), GREY, 30, 1050)
        best = int(np.argmin(vals)) if best_low else -1
        for k in range(NLEV):
            yc = 590 + k * 118
            g = ease((v - t0 - 0.3 - 0.15 * k) / 0.6)
            d.ellipse((80, yc - 18, 116, yc + 18), fill=COLS[k])
            d.text((135, yc - 24), LABEL[k], font=font(44), fill=INK)
            bx0, bw = 330, 520
            d.rounded_rectangle((bx0, yc - 32, bx0 + bw, yc + 32), 14, fill=(40, 48, 78))
            fw = bw * min(1.0, vals[k] / vmax) * g
            if fw > 6:
                d.rounded_rectangle((bx0, yc - 32, bx0 + fw, yc + 32), 14, fill=COLS[k])
            if g > 0.9:
                d.text((bx0 + min(fw, bw) + 14, yc - 28), lab(vals[k]), font=font(50), fill=AMB if k == best else INK)
        if foot:
            center(d, 1325, foot, font(28, False), GREY, 30, 1050)
        return img

    if V_RES <= v < V_Q:
        t0 = max(t_ for t_ in (V_RES, V_WHY, V_AVG) if t_ <= v)
        a = ease((v - t0) / 0.3) if t0 == V_RES else 1.0
        img = panel(a)
        if a > 0.6:
            if v < V_WHY:
                bars(img, V_RES, "Bilyelerin yarısı kaç saniyede indi?", "kısa süre = hızlı (kapı açıldıktan sonra)",
                     shown, 9.0, lambda x: fmt1(x) + " sn", best_low=True, foot="her renkten 10 bilye, hepsi aynı boy")
            elif v < V_AVG:
                bars(img, V_WHY, "Zamanın yüzde kaçı YUKARI gitti?", "bilye çiviye çarpınca yukarı seker",
                     UP, 40.0, lambda x: f"%{round(x)}", foot="yarıştaki 10 bilyenin hareket süresi")
            else:
                bars(img, V_AVG, "8 farklı dizilişin ortalaması", "her seferinde bilyeler başka sırada, bilyelerin yarısı inene kadar",
                     avg, 9.0, lambda x: fmt1(x) + " sn", best_low=True, foot="8 yarış, 480 bilye")
    if v >= V_Q:
        a = ease((v - V_Q) / 0.35)
        img = panel(a); d = ImageDraw.Draw(img)
        if a > 0.6:
            center(d, 440, "Sence çivi olmasaydı", font(60), INK, 30, 1050)
            center(d, 530, "kim kazanırdı?", font(76), AMB, 30, 1050)
            center(d, 650, "Yorumlara yaz", font(46), INK, 30, 1050)
            d.line((130, 790, 950, 790), fill=(60, 70, 110), width=3)
            center(d, 840, "YARIN SABAH 06:00", font(56), (56, 189, 248), 30, 1050)
            center(d, 930, "BÖLÜM 10", font(86), AMB, 30, 1050)
            center(d, 1050, "Dünya tüneline", font(54), INK, 30, 1050)
            center(d, 1120, "HAVA koyuyoruz", font(70), INK, 30, 1050)
            center(d, 1280, "Bölüm 8: Dünya'yı delip 5 top bıraktık", font(30, False), GREY, 30, 1050)
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
PENT = [0, 2, 4, 7, 9, 12]

mix_len = int((TOTAL + 0.5) * SR)
voice = np.zeros(mix_len, dtype=np.float32)
spans = []
for st, c in zip(starts, clips):
    place(voice, st, c); spans.append((st, st + len(c) / SR))
sfx = np.zeros(mix_len, dtype=np.float32)
last = -1.0
rng = np.random.default_rng(5)
for (t, k, strength) in sorted(events):
    if t > SIM_T - 1 or t - last < 0.03 or t > TOTAL - 4:
        continue
    last = t
    place(sfx, t, pluck(mtof(72 + PENT[k] + 12 * (rng.random() < 0.3)), 0.22, 0.014 + 0.03 * strength, decay=22))
for i in range(len(lev)):
    if ft[i] <= CUT_SIM:
        place(sfx, ft[i], blip(mtof(84 + PENT[lev[i]]), 0.12, 0.03))
place(sfx, OPEN_T, pluck(mtof(55), 0.5, 0.12, decay=6))
place(sfx, CUT_SIM, pluck(mtof(79), 1.0, 0.10, decay=4)); place(sfx, CUT_SIM, pluck(mtof(91), 1.0, 0.05, decay=5))
for tv in (V_RES, V_WHY, V_AVG, V_Q):
    place(sfx, tv, pluck(mtof(64), 1.2, 0.06, decay=3))
music = np.zeros(mix_len, dtype=np.float32)
beat = 60.0 / 116
prog = [0, -3, -7, -5]
t = 0.0; bar = 0
while t < TOTAL:
    root = 48 + prog[bar % 4]
    for q in range(4):
        place(music, t + q * beat, blip(mtof(root), 0.22, 0.05) if q % 2 == 0 else blip(mtof(root + 12), 0.16, 0.025))
        if q % 2 == 1:
            for ch in (4, 7, 12):
                place(music, t + q * beat + beat / 2, pluck(mtof(root + 12 + ch), 0.25, 0.012, decay=14))
    t += 4 * beat; bar += 1
duck = np.ones(mix_len, dtype=np.float32)
for a_, b_ in spans:
    duck[int(max(0, a_ - 0.1) * SR):int((b_ + 0.2) * SR)] = 0.35
duck = np.convolve(duck, np.ones(2205) / 2205, mode="same")
mix = voice * 1.0 + sfx * (0.8 + 0.2 * (1 - duck)) + music * duck
mix = np.tanh(mix * 1.1) * 0.95
mix[int(TOTAL * SR):] = 0
wavp = TMP / "mix.wav"
with wave.open(str(wavp), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix[:int(TOTAL * SR)] * 32767).astype(np.int16).tobytes())

if len(sys.argv) > 2 and sys.argv[2] == "frames":
    for tt in [0.1, 3.0, 6.0, CUT_SIM + 0.1, V_RES + 2.5, V_WHY + 2.5, V_AVG + 2.5, V_Q + 1.5]:
        render(tt).save(TMP / f"f_{tt:.1f}.png")
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
