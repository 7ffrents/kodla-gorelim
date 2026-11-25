"""5 tekerlek, ayni yokus: hangisi once iner? (Kodla Gorelim, video 7)
Yuvarlanma fizigi: a = g*sin(t) / (1 + k), k = I/(m r^2). Zaman adimli sayisal entegrasyon (numpy),
her tekerlegin eylemsizlik momenti tanimindan hesaplanir. Ses ozgun sentez + TTS (tools/tts.py).
Renkler yalnizca tekerlek TURUNU gosterir, sonuctan bagimsizdir.
Kullanim: python tekerlek_yarisi.py <cikti_klasoru>"""
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
TMP = Path("/tmp/tekerlek"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100

# ---------------- fizik ----------------
# k = I / (m r^2)  (kutle 1, yaricap 1 birimlerinde)
K_SOLID = 0.5                                   # dolu disk
K_THIN = 1.0                                    # ince halka
K_THICK = 0.5 * (1 + 0.6 ** 2)                  # kalin halka, ic yaricap 0.6 R
K_CORE = 0.9 * 0.5 * 0.4 ** 2 + 0.1 * 0.5       # kutlenin %90'i yaricapin %40'inda dolu cekirdek, %10'u dis disk
RACERS = [  # (ad, ikinci satir, tur, k, yaricap px, renk)
    ("İnce halka", "tüm ağırlık kenarda", "thin", K_THIN, 45, (14, 165, 233)),
    ("Ağır göbekli", "ağırlığın %90'ı ortada", "core", K_CORE, 45, (219, 39, 119)),
    ("Dolu disk (büyük)", "2× büyük, 4× ağır", "solid", K_SOLID, 90, (22, 163, 74)),
    ("Dolu disk (küçük)", "aynı malzeme", "solid", K_SOLID, 45, (22, 163, 74)),
    ("Kalın halka", "içi yarı boş", "thick", K_THICK, 45, (234, 120, 8)),
]
NR = len(RACERS)
THETA = math.atan(0.2)
U = np.array([math.cos(THETA), math.sin(THETA)])           # yokus yonu (sag-asagi)
NRM = np.array([math.sin(THETA), -math.cos(THETA)])        # yukari normal
X0 = 110.0                                                  # baslangic x (merkez)
LEN = 650.0 / math.cos(THETA)                               # kat edilecek yol (px)
ROW0, ROW_DY = 545.0, 225.0
A_BASE = 2 * LEN * (1 + K_CORE) / 5.0 ** 2                  # g sin(t) (px/s^2): cekirdekli tekerlek ~5 sn'de iner
T0 = 1.0                                                    # yaris baslangici (videoda sn)
DT = 1.0 / 480
NSTEP = int(14.0 / DT)
s = np.zeros(NR); vv = np.zeros(NR)
S_HIST = np.zeros((NSTEP, NR))
finish = np.full(NR, np.nan)
kk = np.array([r[3] for r in RACERS])
for i in range(NSTEP):
    acc = A_BASE / (1 + kk)
    vv += acc * DT
    s += vv * DT
    S_HIST[i] = s
    t = (i + 1) * DT
    done = (s >= LEN) & np.isnan(finish)
    finish[done] = t
assert not np.isnan(finish).any()
# analitik kontrol: t = sqrt(2 L (1+k) / A)
ana = np.sqrt(2 * LEN * (1 + kk) / A_BASE)
assert np.allclose(finish, ana, atol=0.01), (finish, ana)
assert abs(finish[2] - finish[3]) < 1e-9
print("bitis sureleri:", np.round(finish, 2).tolist())
order = np.argsort(finish)
rank = [int(1 + np.sum(finish < finish[i] - 1e-6)) for i in range(NR)]
print("siralama:", rank)
winner = int(np.argmin(finish))
fwd_pct = [round(100 / (1 + k)) for k in kk]
print("ilerleme enerjisi %:", fwd_pct)

# ---------------- gorsel ----------------
BG = (238, 242, 247)
INK = (23, 30, 52)
SLAB = (46, 56, 86)
AMBER = (217, 119, 6)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
F_BIG, F_MID, F_SM, F_XS = font(104), font(50), font(34), font(26)
def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)

def row_point(i, sdist):
    p0 = np.array([X0, ROW0 + ROW_DY * i])
    return p0 + sdist * U

SS = 3
def make_sprite(kind, r, col):
    n = int(2 * r * SS)
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = n / 2; R = r * SS
    dark = tuple(int(v * 0.55) for v in col)
    light = tuple(min(255, int(v * 0.45 + 140)) for v in col)
    def disc(rad, fill, outline=None, w=0):
        d.ellipse((c - rad, c - rad, c + rad, c + rad), fill=fill, outline=outline, width=w)
    if kind == "solid":
        disc(R, col, dark, 5 * SS // 2)
        disc(R * 0.62, light)
        disc(R * 0.62, None, dark, 2 * SS)
    elif kind == "thin":
        disc(R, col); disc(R * 0.88, (0, 0, 0, 0))
        d.ellipse((c - R * 0.88, c - R * 0.88, c + R * 0.88, c + R * 0.88), fill=(0, 0, 0, 0))
        # sifir alfa ile ic kismi ac
        mask = Image.new("L", (n, n), 0); md = ImageDraw.Draw(mask)
        md.ellipse((c - R, c - R, c + R, c + R), fill=255)
        md.ellipse((c - R * 0.88, c - R * 0.88, c + R * 0.88, c + R * 0.88), fill=0)
        im = Image.new("RGBA", (n, n), col + (0,)); im.putalpha(mask)
        d = ImageDraw.Draw(im)
    elif kind == "thick":
        mask = Image.new("L", (n, n), 0); md = ImageDraw.Draw(mask)
        md.ellipse((c - R, c - R, c + R, c + R), fill=255)
        md.ellipse((c - R * 0.6, c - R * 0.6, c + R * 0.6, c + R * 0.6), fill=0)
        im = Image.new("RGBA", (n, n), col + (0,)); im.putalpha(mask)
        d = ImageDraw.Draw(im)
        d.ellipse((c - R, c - R, c + R, c + R), outline=dark, width=4 * SS // 2)
        d.ellipse((c - R * 0.6, c - R * 0.6, c + R * 0.6, c + R * 0.6), outline=dark, width=3 * SS // 2)
    elif kind == "core":
        disc(R, tuple(int(v * 0.35 + 255 * 0.65) for v in col), col, 3 * SS)      # hafif dis disk
        disc(R * 0.4, col, dark, 3 * SS)                                           # agir cekirdek
    # donusu gosteren isaret
    if kind == "thin":
        d.ellipse((c + R * 0.94 - 7 * SS, c - 7 * SS, c + R * 0.94 + 7 * SS, c + 7 * SS), fill=INK)
    else:
        d.line((c, c, c + R * 0.9, c), fill=INK, width=4 * SS)
        d.ellipse((c + R * 0.8 - 6 * SS, c - 6 * SS, c + R * 0.8 + 6 * SS, c + 6 * SS), fill=INK)
    return im

SPR = [make_sprite(k[2], k[4], k[5]) for k in RACERS]

def paste_rot(img, spr, cx, cy, ang_deg, r):
    rot = spr.rotate(-ang_deg, resample=Image.BICUBIC)
    sz = int(2 * r)
    rot = rot.resize((sz, sz), Image.LANCZOS)
    img.paste(rot, (int(round(cx - r)), int(round(cy - r))), rot)

def slab_label(text, sub):
    txt = Image.new("RGBA", (560, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    d.text((6, 4), text, font=font(25), fill=(255, 255, 255))
    w = d.textlength(text, font=font(25))
    d.text((6 + w + 14, 8), sub, font=font(20, False), fill=(190, 200, 230))
    return txt

# sabit zemin
bg = Image.new("RGBA", (W, H), BG + (255,))
bd = ImageDraw.Draw(bg)
for i in range(NR):
    p_a = row_point(i, -40) + NRM * -2
    p_b = row_point(i, LEN + 70) + NRM * -2
    th = 44
    n_dn = -NRM
    poly = [tuple(p_a), tuple(p_b), tuple(p_b + n_dn * th), tuple(p_a + n_dn * th)]
    bd.polygon([(x + 5, y + 8) for x, y in poly], fill=(205, 212, 226))
    bd.polygon(poly, fill=SLAB)
    # 40 px'te bir isaret (tik sesleri bu isaretlerden gecerken)
    for m in range(0, int(LEN) + 1, 40):
        q = row_point(i, m) - NRM * 4
        q2 = q - NRM * 14
        bd.line((tuple(q), tuple(q2)), fill=(120, 134, 176), width=3)
    # bitis cizgisi
    q = row_point(i, LEN)
    bd.line((tuple(q - NRM * 120), tuple(q + NRM * 4 * -1)), fill=(220, 38, 38), width=0)
    # ad yazisi egik zeminde
    lab = slab_label(RACERS[i][0], RACERS[i][1])
    lab = lab.rotate(-math.degrees(THETA), resample=Image.BICUBIC, expand=True)
    pos = row_point(i, 120) - NRM * 36
    # etiket sol-ust kosesini yokus yuzeyinin altina oturt
    bg.alpha_composite(lab, (int(pos[0] - 4), int(pos[1] - 6)))
# bitis seridi (tum satirlar icin dikey kesikli cizgi)
fx0 = row_point(0, LEN)[0]
for y in range(ROW0 - 110 if False else 450, 1600, 28):
    bd.line((fx0, y, fx0, y + 14), fill=(220, 38, 38), width=5)

def text_fit_center(d, y, text, f, fill, x0, x1):
    center(d, y, text, f, fill, x0, x1)

# ---------------- anlatim (once sesler, sonra gorsel zamanlari) ----------------
t_first = T0 + float(finish.min())
t_tie = T0 + float(finish[2])
t_last = T0 + float(finish.max())
def load_wav(p):
    out = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0

TEXTS = [
    "Beş tekerlek, aynı yokuş. Hangisi önce iner?",
    "Kazanan, ağırlığını göbeğinde toplamış olan.",
    "Küçük dolu disk de, dört kat ağır olan büyüğü de aynı anda geldi. Ağırlık hiçbir şeyi değiştirmedi.",
    "Önemli olan ağırlık değil, ağırlığın nerede durduğu. Kenardaysa enerjinin yarısı sadece dönmeye gider.",
    "Peki yokuşa bir de kayan kutu koysak? Sürtünme yok, dönme yok. Sence kim kazanırdı? Yaz bakalım.",
]
clips = []
for i, tx in enumerate(TEXTS):
    wp = TMP / f"v{i}.wav"
    synth(tx, wp, "fahrettin")
    clips.append(load_wav(wp))
dur = [len(c) / SR for c in clips]
starts = []
cursor = 0.0
want = [0.3, t_first - 0.3, t_tie + 0.2, 0.0, 0.0]
for i in range(len(TEXTS)):
    st = max(want[i], cursor + (0.3 if i else 0.0))
    if i in (3, 4):
        st = cursor + 0.5
    starts.append(st); cursor = st + dur[i]
    print(f"anlatim {i}: {st:.1f}-{cursor:.1f}  {TEXTS[i]}")
V_PANEL = starts[3] - 0.2          # enerji paneli
V_Q = starts[4] - 0.2              # soru karti
TOTAL = cursor + 2.2
NFR = int(TOTAL * FPS)
print("toplam", round(TOTAL, 1), "sn")

# ---------------- kare cizimi ----------------
def race_state(v):
    tr = v - T0
    if tr <= 0:
        return np.zeros(NR)
    idx = min(int(tr / DT), NSTEP - 1)
    return np.minimum(S_HIST[idx], LEN)

def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def fmt_t(x):
    return f"{x:.1f}".replace(".", ",") + " sn"

def render(v):
    img = bg.copy(); d = ImageDraw.Draw(img)
    center(d, 56, "5 TEKERLEK", F_BIG, INK)
    center(d, 188, "Aynı yokuş, aynı anda bırakıldı", F_MID, (60, 72, 110))
    center(d, 256, "Hangisi önce iner?", F_MID, AMBER)
    sd = race_state(v)
    for i in range(NR):
        r = RACERS[i][4]
        c = row_point(i, sd[i]) + NRM * r
        ang = math.degrees(sd[i] / r)
        paste_rot(img, SPR[i], c[0], c[1], ang, r)
    d = ImageDraw.Draw(img)
    # sayac
    tr = v - T0
    if 0 < tr:
        shown = min(tr, float(finish.max()))
        center(d, 340, f"{shown:.1f}".replace(".", ",") + " sn", font(56), INK, 0, W)
    # bitis rozetleri (sira + sure), yalniz o tekerlek bitirince
    for i in range(NR):
        if tr >= finish[i]:
            c = row_point(i, LEN) + NRM * RACERS[i][4]
            bx, by = 885, c[1]
            a = ease((tr - finish[i]) / 0.25)
            rad = int(34 * a)
            if rad > 2:
                fill = AMBER if rank[i] == 1 else (80, 92, 130)
                d.ellipse((bx - rad, by - rad, bx + rad, by + rad), fill=fill)
                if a > 0.8:
                    center(d, by - 24, str(rank[i]), font(44), (255, 255, 255), bx - 40, bx + 40)
                    center(d, by + 40, fmt_t(finish[i]).replace(" sn", ""), font(24, True), INK, bx - 50, bx + 50)
    # esitlik damgasi
    if t_tie <= v < t_tie + 2.6:
        a = ease((v - t_tie) / 0.2) * (1 - ease((v - t_tie - 2.0) / 0.5))
        if a > 0.05:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            od.rounded_rectangle((90, 1010, 700, 1210), 30, fill=(255, 255, 255, int(235 * a)), outline=(217, 119, 6, int(255 * a)), width=6)
            img = Image.alpha_composite(img.convert("RGBA"), ov); d = ImageDraw.Draw(img)
            col = (int(AMBER[0]), int(AMBER[1]), int(AMBER[2]))
            center(d, 1030, "AYNI ANDA!", font(76), col if a > 0.9 else tuple(int(255 - (255 - c_) * a) for c_ in col), 90, 700)
            center(d, 1130, "4× ağır olması işe yaramadı", font(32), INK if a > 0.9 else (170, 175, 190), 90, 700)
    # enerji paneli
    if v >= V_PANEL:
        a = ease((v - V_PANEL) / 0.4)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.rounded_rectangle((30, 420, 1050, 1620), 36, fill=(15, 20, 40, int(246 * a)))
        img = Image.alpha_composite(img.convert("RGBA"), ov); d = ImageDraw.Draw(img)
        if a > 0.6 and v < V_Q:
            center(d, 450, "Enerjinin kaçı ilerlemeye gidiyor?", font(40), (255, 255, 255), 30, 1050)
            d.rectangle((90, 515, 118, 543), fill=(251, 191, 36)); d.text((130, 510), "ilerleme", font=font(28, False), fill=(235, 240, 255))
            d.rectangle((330, 515, 358, 543), fill=(104, 116, 156)); d.text((370, 510), "dönme", font=font(28, False), fill=(235, 240, 255))
            for i in range(NR):
                yc = 640 + 190 * i
                nm, sub = RACERS[i][0], RACERS[i][1]
                d.text((70, yc - 54), nm, font=font(30), fill=(255, 255, 255))
                d.text((70, yc - 14), sub, font=font(23, False), fill=(170, 182, 220))
                bx0, bw = 430, 470
                g = ease((v - V_PANEL - 0.5 - 0.35 * i) / 0.9)
                fw = bw * (fwd_pct[i] / 100) * g
                d.rounded_rectangle((bx0, yc - 40, bx0 + bw, yc + 40), 14, fill=(104, 116, 156))
                if fw > 4:
                    d.rounded_rectangle((bx0, yc - 40, bx0 + fw, yc + 40), 14, fill=(251, 191, 36))
                if g > 0.95:
                    d.text((bx0 + 14, yc - 25), f"%{fwd_pct[i]}", font=font(46), fill=(15, 20, 40) if fwd_pct[i] > 30 else (255, 255, 255))
        if v >= V_Q:
            b = ease((v - V_Q) / 0.4)
            ov2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od2 = ImageDraw.Draw(ov2)
            od2.rounded_rectangle((30, 420, 1050, 1620), 36, fill=(15, 20, 40, int(255 * b)))
            img = Image.alpha_composite(img.convert("RGBA"), ov2); d = ImageDraw.Draw(img)
            if b > 0.5:
                center(d, 560, "Peki yokuşa", font(64), (255, 255, 255), 30, 1050)
                center(d, 650, "bir de KUTU koysak?", font(76), (251, 191, 36), 30, 1050)
                # kutu cizimi
                d.polygon([(330, 960), (750, 1020), (750, 1040), (330, 980)], fill=(104, 116, 156))
                ang_ = math.atan2(60, 420); ux_, uy_ = math.cos(ang_), math.sin(ang_)
                bx_, by_ = 330 + 160 * ux_, 960 + 160 * uy_            # egimin ustunde bir nokta
                nx_, ny_ = uy_, -ux_
                pts_ = [(bx_ - 70 * ux_, by_ - 70 * uy_), (bx_ + 70 * ux_, by_ + 70 * uy_)]
                pts_ += [(pts_[1][0] + 140 * nx_, pts_[1][1] + 140 * ny_), (pts_[0][0] + 140 * nx_, pts_[0][1] + 140 * ny_)]
                d.polygon(pts_, fill=(244, 114, 182), outline=(131, 24, 67))
                center(d, 1090, "Sürtünme yok, dönme yok", font(40), (200, 210, 235), 30, 1050)
                center(d, 1180, "Sence kim kazanır?", font(60), (255, 255, 255), 30, 1050)
                center(d, 1280, "Tahminini yorumlara yaz", font(42), (251, 191, 36), 30, 1050)
    return img.convert("RGB")

# ---------------- ses (ozgun sentez) ----------------
def pluck(freq, dur_, vol, decay=14.0):
    nn = int(dur_ * SR); t = np.arange(nn) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 10)
    env = np.exp(-t * decay); env[:40] *= np.linspace(0, 1, 40)
    return (w * env * vol).astype(np.float32)

def blip(freq, dur_, vol):
    """kare dalga, 8-bit tadinda"""
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
PENT = [0, 2, 4, 7, 9]

mix_len = int((TOTAL + 0.5) * SR)
voice = np.zeros(mix_len, dtype=np.float32)
spans = []
for st, c in zip(starts, clips):
    place(voice, st, c)
    spans.append((st, st + len(c) / SR))

sfx = np.zeros(mix_len, dtype=np.float32)
# her tekerlek 40 px yol aldikca bir tik (hizlandikca tempo artar), satira gore nota
for i in range(NR):
    marks = np.arange(40, LEN + 1, 40)
    for m in marks:
        idx = np.searchsorted(S_HIST[:, i], m)
        if idx >= NSTEP:
            continue
        tt = T0 + idx * DT
        place(sfx, tt, blip(mtof(72 + PENT[i] + (12 if i == 4 else 0)), 0.09, 0.028))
# bitis cinlamalari
for i in range(NR):
    tf = T0 + float(finish[i])
    base = 76 + (0 if rank[i] == 1 else -5)
    place(sfx, tf, pluck(mtof(base + 7 * 0), 0.8, 0.10 if rank[i] == 1 else 0.06, decay=5))
    place(sfx, tf, pluck(mtof(base + 12), 0.8, 0.05 if rank[i] == 1 else 0.03, decay=6))
place(sfx, t_tie, pluck(mtof(88), 0.9, 0.05, decay=4))
place(sfx, V_PANEL, pluck(mtof(60), 1.2, 0.06, decay=3))
place(sfx, V_Q, pluck(mtof(64), 1.2, 0.06, decay=3))

music = np.zeros(mix_len, dtype=np.float32)
beat = 60.0 / 112
prog = [0, -3, -7, -5]          # C - Am - F - G (kok)
t = 0.0; bar = 0
while t < TOTAL:
    root = 48 + prog[bar % 4]
    for q in range(4):
        place(music, t + q * beat, blip(mtof(root), 0.22, 0.05) if q % 2 == 0 else blip(mtof(root + 12), 0.16, 0.025))
    for q in range(4):
        for ch in (4, 7, 12):
            if q % 2 == 1:
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

# ---------------- video ----------------
if len(sys.argv) > 2 and sys.argv[2] == "frames":
    for tt in [0.1, 3.0, t_first + 0.6, t_tie + 0.6, t_last + 1.0, V_PANEL + 2.5, V_Q + 1.0]:
        render(tt).save(TMP / f"f_{tt:.1f}.png")
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
print("tamam", round(TOTAL, 1), "sn", "bitis", np.round(finish, 2).tolist())
