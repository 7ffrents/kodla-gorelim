"""220 top, 11 kutu: hepsi ortadan birakilinca hangi kutu dolar? (Kodla Gorelim, video 6)
Galton tahtasi / plinko simulasyonu: top-civi ve top-top carpismalari numpy ile, ses ozgun sentez.
Kullanim: python plinko.py <cikti_klasoru>
Gerekenler: numpy, pillow, ffmpeg, piper-tts (tools/tts.py)."""
import math
import os
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
TMP = Path("/tmp/plinko"); TMP.mkdir(exist_ok=True)
W, H, FPS, SR = 1080, 1920, 30, 44100

# ---------------- fizik ----------------
N = 220
R = 11.0
CX = 540.0
XL, XR = 100.0, 980.0
SP = 80.0
ROWS = 10
ROW_Y0, ROW_DY = 520.0, 60.0
PEG_R = 8.0
DIV_TOP, FLOOR = 1100.0, 1560.0
SPAWN_Y = 380.0
G = 2300.0
SUB = 4                      # alt adim / video karesi (dt = 1/(FPS*SUB*...))
SIMFPS = 60
SIM_END = 24.0
dt = 1.0 / (SIMFPS * 2)
REST = float(os.environ.get('REST', 0.55))
FRIC = float(os.environ.get('FRIC', 0.45))
DRAG = float(os.environ.get('DRAG', 2.5))

pegs = []
for i in range(1, ROWS + 1):
    for j in range(i):
        pegs.append((CX + (j - (i - 1) / 2) * SP, ROW_Y0 + (i - 1) * ROW_DY, PEG_R))
div_x = [CX + (k - 4.5) * SP for k in range(10)]
for x in div_x:
    pegs.append((x, DIV_TOP, 4.0))          # bolme duvarlarinin ustu (yuvarlak kapak)
PG = np.array(pegs)
EDGES = np.array([XL] + div_x + [XR])        # 12 sinir, 11 kutu

rng = np.random.default_rng(11)
spawn_t = 0.05 + 15.0 * (np.arange(N) / N) ** 0.6
spawn_x = CX + rng.uniform(-5, 5, N)

pos = np.zeros((N, 2)); vel = np.zeros((N, 2))
alive = np.zeros(N, bool)
frames = []
events = []                # (t, tip, siddet, x)
nsteps = int(SIM_END / dt)
iu = None

def bin_of(x):
    return np.clip(np.searchsorted(EDGES, x) - 1, 0, 10)

for s in range(nsteps):
    t = s * dt
    new = (~alive) & (spawn_t <= t)
    if new.any():
        idx = np.where(new)[0]
        pos[idx, 0] = spawn_x[idx]; pos[idx, 1] = SPAWN_Y
        vel[idx] = (0, 0)
        alive[idx] = True
    a = np.where(alive)[0]
    if len(a):
        p = pos[a]; v = vel[a]
        v[:, 1] += G * dt
        v[:, 0] *= 1 - DRAG * dt
        p += v * dt
        # civiler
        dx = p[:, None, 0] - PG[None, :, 0]
        dy = p[:, None, 1] - PG[None, :, 1]
        dist = np.hypot(dx, dy)
        hit = dist < (R + PG[None, :, 2])
        bi, pj = np.where(hit)
        for b, k in zip(bi, pj):
            d = dist[b, k] + 1e-9
            nx, ny = dx[b, k] / d, dy[b, k] / d
            pen = R + PG[k, 2] - d
            p[b, 0] += nx * pen; p[b, 1] += ny * pen
            vn = v[b, 0] * nx + v[b, 1] * ny
            if vn < 0:
                tx, ty = -ny, nx
                vt = v[b, 0] * tx + v[b, 1] * ty
                vt *= 1 - FRIC
                vn2 = -vn * REST
                v[b, 0] = vn2 * nx + vt * tx
                v[b, 1] = vn2 * ny + vt * ty
                if -vn > 120 and PG[k, 2] > 5:
                    events.append((t, 0, min(1.0, -vn / 900), PG[k, 0]))
        # duvarlar, bolmeler, zemin
        for side, lim in ((0, XL + R), (1, XR - R)):
            m = (p[:, 0] < lim) if side == 0 else (p[:, 0] > lim)
            p[m, 0] = lim; v[m, 0] *= -0.3
        inb = p[:, 1] > DIV_TOP
        for x in div_x:
            m = inb & (np.abs(p[:, 0] - x) < R + 3.0)
            left = p[:, 0] < x
            p[m & left, 0] = x - R - 3.0
            p[m & ~left, 0] = x + R + 3.0
            v[m, 0] *= -0.25
        m = p[:, 1] > FLOOR - R
        if m.any():
            snd = m & (v[:, 1] > 150)
            for b in np.where(snd)[0]:
                events.append((t, 1, min(1.0, v[b, 1] / 1200), p[b, 0]))
        p[m, 1] = FLOOR - R
        v[m, 1] *= -0.12
        v[m, 0] *= 0.9
        # top-top
        n = len(a)
        if n > 1 and not os.environ.get('NOBB'):
            for _ in range(3):
                ddx = p[:, None, 0] - p[None, :, 0]
                ddy = p[:, None, 1] - p[None, :, 1]
                dd = np.hypot(ddx, ddy)
                ii, jj = np.where(np.triu(dd < 2 * R, 1))
                if len(ii) == 0:
                    break
                for i, j in zip(ii, jj):
                    d = dd[i, j] + 1e-9
                    nx, ny = ddx[i, j] / d, ddy[i, j] / d
                    pen = (2 * R - d) / 2
                    p[i, 0] += nx * pen; p[i, 1] += ny * pen
                    p[j, 0] -= nx * pen; p[j, 1] -= ny * pen
                    rvn = (v[i, 0] - v[j, 0]) * nx + (v[i, 1] - v[j, 1]) * ny
                    if rvn < 0:
                        imp = -(1 + 0.25) * rvn / 2
                        v[i, 0] += imp * nx; v[i, 1] += imp * ny
                        v[j, 0] -= imp * nx; v[j, 1] -= imp * ny
        # kutu icinde sonumleme
        inb = p[:, 1] > DIV_TOP + 10
        v[inb] *= 0.985
        slow = inb & (np.hypot(v[:, 0], v[:, 1]) < 25)
        v[slow] = 0
        pos[a] = p; vel[a] = v
    if s % 2 == 0:
        fr = np.full((N, 2), -9999.0)
        fr[alive] = pos[alive]
        frames.append(fr)

frames = np.array(frames)            # (kare, N, 2) @ 60 fps
import os
if os.environ.get('SIMONLY'):
    f=frames[-1]; print(np.bincount(bin_of(f[:,0]),minlength=11).tolist()); sys.exit()
final = frames[-1]
fbin = bin_of(final[:, 0])
counts = np.bincount(fbin, minlength=11)
print("kutular", counts.tolist(), "toplam", counts.sum())
assert counts.sum() == N
# yerlesmis mi: son 1 sn'de hareket
mv = np.abs(frames[-1] - frames[-60]).max()
print("son 1 sn en buyuk hareket px:", round(float(mv), 2))
top_y = np.array([final[fbin == b, 1].min() - R if (fbin == b).any() else FLOOR for b in range(11)])
print("kutu tepe y:", top_y.round(0).tolist())
assert top_y.min() > DIV_TOP - 40, "kutu tasti"
best = int(counts.argmax())
edge2 = int(counts[0] + counts[10])

settle_t = float(spawn_t[-1] + 4.5)
TOTAL = settle_t + 11.5
NFR = int(TOTAL * FPS)
V_RES = settle_t + 0.6            # sonuc paneli

# ---------------- gorsel ----------------
BG = (12, 15, 30)
PANEL = (20, 26, 48)
WHITE = (241, 245, 249); GREY = (120, 132, 160); AMBER = (251, 191, 36)
FD = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)
F_BIG, F_MID, F_SM, F_XS = font(100), font(52), font(40), font(30)
def center(d, y, text, f, fill, x0=0, x1=W):
    w = d.textlength(text, font=f)
    d.text(((x0 + x1) / 2 - w / 2, y), text, font=f, fill=fill)

def hsv(h, s=0.75, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))
BCOL = [hsv(0.55 + 0.45 * (b / 10) if b / 10 < 0.5 else 0.55 + 0.45 * (b / 10), 0.7, 1.0) for b in range(11)]
BCOL = [hsv((0.55 + b * 0.09) % 1.0, 0.72, 1.0) for b in range(11)]   # gokkusagi benzeri

bg = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(bg)
d.rounded_rectangle((XL - 16, 330, XR + 16, FLOOR + 20), 26, fill=PANEL)
for (px, py, pr) in pegs[:-10]:
    d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(150, 162, 200))
for x in div_x:
    d.rectangle((x - 3, DIV_TOP, x + 3, FLOOR + 6), fill=(110, 122, 160))
    d.ellipse((x - 4, DIV_TOP - 4, x + 4, DIV_TOP + 4), fill=(110, 122, 160))
d.rectangle((XL - 6, DIV_TOP, XL, FLOOR + 6), fill=(110, 122, 160))
d.rectangle((XR, DIV_TOP, XR + 6, FLOOR + 6), fill=(110, 122, 160))
d.rectangle((XL - 6, FLOOR + 6, XR + 6, FLOOR + 14), fill=(110, 122, 160))
for b in range(11):
    cx = (EDGES[b] + EDGES[b + 1]) / 2
    center(d, FLOOR + 30, str(b + 1), F_XS, (150, 160, 190), cx - 40, cx + 40)

def draw_ball(dr, x, y, c):
    dr.ellipse((x - R, y - R, x + R, y + R), fill=c, outline=tuple(int(v * 0.55) for v in c), width=2)
    dr.ellipse((x - R * 0.55, y - R * 0.6, x - R * 0.1, y - R * 0.15), fill=tuple(min(255, int(v * 0.5 + 140)) for v in c))

def curve_pts():
    xs = [(EDGES[b] + EDGES[b + 1]) / 2 for b in range(11)]
    ys = [min(top_y[b], FLOOR - 4) for b in range(11)]
    pts = []
    for k in range(10):
        for u in np.linspace(0, 1, 12, endpoint=False):
            s = u * u * (3 - 2 * u)
            pts.append((xs[k] + (xs[k + 1] - xs[k]) * u, ys[k] + (ys[k + 1] - ys[k]) * s))
    pts.append((xs[10], ys[10]))
    return pts
CURVE = curve_pts()

def render(v):
    img = bg.copy(); d = ImageDraw.Draw(img)
    fi = min(int(v * SIMFPS), len(frames) - 1)
    pos_ = frames[fi]
    center(d, 70, "220 TOP, 11 KUTU", F_BIG, WHITE)
    center(d, 200, "Hepsi tam ortadan bırakılıyor", F_MID, (200, 210, 235))
    center(d, 262, "Hangi kutu kazanır?", F_MID, AMBER)
    live = np.zeros(11, int)
    for i in range(N):
        x, y = pos_[i]
        if x < -1000:
            continue
        if y > DIV_TOP + 5:
            live[bin_of(np.array([x]))[0]] += 1
        draw_ball(d, x, y, BCOL[fbin[i]])
    # kutu sayaclari (uste yazilir, kutu dolarken)
    for b in range(11):
        if live[b] > 0:
            cx = (EDGES[b] + EDGES[b + 1]) / 2
            c = AMBER if (v >= settle_t and b == best) else (180, 190, 215)
            center(d, DIV_TOP - 52, str(live[b]), font(30), c, cx - 40, cx + 40)
    if v >= V_RES:
        a = min(1.0, (v - V_RES) / 0.5)
        k = int(len(CURVE) * a)
        if k > 2:
            d.line(CURVE[:k], fill=AMBER, width=7, joint="curve")
        if a >= 1.0:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            od.rounded_rectangle((90, 420, 990, 800), 30, fill=(8, 10, 22, 225))
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
            d = ImageDraw.Draw(img)
            center(d, 450, f"{best + 1}. kutu: {counts[best]} top", F_BIG, AMBER, 90, 990)
            center(d, 590, f"En uçtaki iki kutu: sadece {edge2} top", F_MID, WHITE, 90, 990)
            center(d, 665, "Bu şekle çan eğrisi deniyor", F_MID, (200, 210, 235), 90, 990)
            if v >= V_RES + 4.0:
                center(d, 730, "Topları sağdan bıraksam?", font(44), (255, 236, 160), 90, 990)
    return img

# ---------------- anlatim ----------------
ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
def words(n):
    return (TENS[n // 10] + " " + ONES[n % 10]).strip() if n else "sıfır"
ORD = ["", "birinci", "ikinci", "üçüncü", "dördüncü", "beşinci", "altıncı", "yedinci", "sekizinci", "dokuzuncu", "onuncu", "on birinci"]
lines = [
    (0.3, "İki yüz yirmi top, hepsi tam ortadan düşüyor. Hangi kutu kazanır?"),
    (5.5, "Her çivide top yazı tura atıyor: sağa mı, sola mı?"),
    (10.5, "Ortadaki kutular doluyor, kenarlar boş kalıyor."),
    (V_RES + 0.3, f"Kazanan {ORD[best + 1]} kutu, {words(int(counts[best]))} top. En uçtaki iki kutuda sadece {words(edge2)} top var."),
    (V_RES + 6.2, "Peki topları en sağdan bıraksam ne olur? Tahminini yaz."),
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
    w = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 10)
    env = np.exp(-t * decay); env[:40] *= np.linspace(0, 1, 40)
    return (w * env * vol).astype(np.float32)

def place(buf, t, clip):
    s = int(t * SR)
    if s < 0 or s >= len(buf):
        return
    e = min(len(buf), s + len(clip))
    buf[s:e] += clip[:e - s]

PENT = [0, 2, 4, 7, 9]
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def note_for_x(x, base=72):
    k = int(round((x - XL) / SP))          # 0..11
    k = max(0, min(11, k))
    return base + 12 * (k // 5) + PENT[k % 5]

sfx = np.zeros(mix_len, dtype=np.float32)
last_t = -1.0
last_floor = -1.0
for (t, kind, st, x) in sorted(events):
    if kind == 0:
        if t - last_t < 0.035:
            continue
        last_t = t
        place(sfx, t, pluck(mtof(note_for_x(x)), 0.28, 0.030 + 0.05 * st, decay=18))
    else:
        if t - last_floor < 0.05:
            continue
        last_floor = t
        place(sfx, t, pluck(mtof(note_for_x(x, 48)), 0.22, 0.05 + 0.05 * st, decay=24))
for m in (60, 64, 67, 72):
    place(sfx, V_RES, pluck(mtof(m), 1.8, 0.07, decay=2.2))

music = np.zeros(mix_len, dtype=np.float32)
beat = 0.5
prog = [0, -3, -5, -2]
t = 0.0; bar = 0
while t < TOTAL:
    root = 45 + prog[bar % 4]
    place(music, t, pluck(mtof(root), 1.0, 0.08, decay=4.0))
    for k in range(8):
        m = root + 12 + [0, 4, 7, 12, 7, 4, 9, 7][k]
        place(music, t + k * beat / 2, pluck(mtof(m), 0.3, 0.03, decay=12.0))
    t += beat * 4; bar += 1
duck = np.ones(mix_len, dtype=np.float32)
for a_, b_ in spans:
    duck[int(max(0, a_ - 0.1) * SR):int((b_ + 0.2) * SR)] = 0.35
duck = np.convolve(duck, np.ones(2205) / 2205, mode="same")
mix = voice * 1.0 + sfx * (0.85 + 0.15 * (1 - duck)) + music * duck
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
print("tamam", round(TOTAL, 1), "sn", "kutular", counts.tolist())
