"""'13 satir Python ile fizik' (Kodla Gorelim, video 5): kod ekranda yazilir,
simulasyon gosterilen kodun kendisiyle calisir. Sesli (TTS fahrettin) + ozgun muzik.
Kullanim: python python_bilye.py <cikti_klasoru>"""
import math
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
TMP = Path("/tmp/pybilye")
TMP.mkdir(exist_ok=True)

W, H, FPS, SR = 1080, 1920, 30, 44100
BG = (15, 23, 42)
PANEL = (22, 32, 56)
CYAN = (56, 189, 248)
AMBER = (245, 158, 11)
GREEN = (52, 211, 153)
WHITE = (241, 245, 249)
GREY = (100, 116, 139)
FD = "/usr/share/fonts/truetype/dejavu/"
F_T = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 66)
F_S = ImageFont.truetype(FD + "DejaVuSans.ttf", 36)
F_C = ImageFont.truetype(FD + "DejaVuSansMono-Bold.ttf", 33)
F_B = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 44)

# ------------------------------------------------------------------ kod
# (asama, metin). Asama k'dan itibaren gorunur. "N" satiri 5. asamada degisir.
CODE = [
    (1, "import numpy as np"),
    (1, "n = {N}"),
    (1, "x = np.random.rand(n) * 10"),
    (1, "y = np.random.rand(n) * 4 + 4"),
    (1, "vx = np.random.randn(n) * 3"),
    (1, "vy = np.zeros(n)"),
    (1, "for adim in range(1800):"),
    (2, "    vy -= 9.8 / 60"),
    (1, "    x += vx / 60"),
    (1, "    y += vy / 60"),
    (3, "    vy[y < 0] *= -0.9"),
    (3, "    y[y < 0] = 0"),
    (4, "    vx[(x < 0) | (x > 10)] *= -1"),
]
KW = ("import", "as", "for", "in")
STAGE_T = [0.0, 9.0, 15.0, 21.0, 27.0, 36.0]     # 1..5 baslangic, 5. asama sonu = 36 sn
T_END = 43.0
TOTAL = int(T_END * FPS)

def stage_at(t):
    s = 1
    for i, st in enumerate(STAGE_T[:5]):
        if t >= st:
            s = i + 1
    return s

def visible_code(stage, t):
    """Gorunen satirlar, yeni eklenen satirlar ve daktilo etkisi icin ilerleme."""
    lines = []
    for k, (st, text) in enumerate(CODE):
        if st <= stage:
            n = 300 if stage >= 5 else 1
            lines.append((k, st, text.replace("{N}", str(n))))
    return lines

# ------------------------------------------------------------------ simulasyon (gosterilen kodun birebir karsiligi)
class Sim:
    def __init__(self, stage, seed):
        self.stage = stage
        r = np.random.default_rng(seed)
        self.n = 300 if stage >= 5 else 1
        n = self.n
        self.x = r.random(n) * 10
        self.y = r.random(n) * 4 + 4
        self.vx = r.standard_normal(n) * 3
        self.vy = np.zeros(n)
        self.hits = 0

    def step(self):
        s = self.stage
        if s >= 2:
            self.vy -= 9.8 / 60
        self.x += self.vx / 60
        self.y += self.vy / 60
        if s >= 3:
            m = self.y < 0
            self.hits += int(m.sum())
            self.vy[m] *= -0.9
            self.y[m] = 0
        if s >= 4:
            m = (self.x < 0) | (self.x > 10)
            self.hits += int(m.sum())
            self.vx[m] *= -1

# ------------------------------------------------------------------ anlatim
lines_tts = [
    (0.4, "Bu bilyeleri sadece on üç satır Python yönetiyor. Hadi satır satır kuralım."),
    (5.6, "Önce bir top: konum ve hız."),
    (9.4, "Yerçekimi ekleyince top düşüyor."),
    (15.4, "Zemin ekleyince zıplıyor."),
    (21.4, "Duvar ekleyince kutudan kaçamıyor."),
    (27.4, "Şimdi tek satırı değiştiriyoruz: top sayısı üç yüz."),
    (36.6, "On üç satır, bütün fizik bu. Sence bin top olsa bilgisayar dayanır mı?"),
]

def load44(p):
    o = TMP / (p.stem + "_44.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", str(o)], check=True)
    with wave.open(str(o)) as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return raw.astype(np.float32) / 32768.0

mix_len = int((T_END + 1.0) * SR)
voice = np.zeros(mix_len, dtype=np.float32)
cursor = 0.0
for i, (t, text) in enumerate(lines_tts):
    p = TMP / f"v{i}.wav"
    synth(text, p, "fahrettin")
    clip = load44(p)
    start = max(t, cursor + 0.2)
    s = int(start * SR)
    voice[s:s + len(clip)] += clip
    cursor = start + len(clip) / SR
    print(f"anlatim {i}: {start:.1f}-{cursor:.1f} {text}")
assert cursor < T_END, "anlatim videodan uzun"

# ------------------------------------------------------------------ muzik + sfx
def tone(f, d, kind="tri", vol=1.0, a=0.01, r=0.08):
    n = int(d * SR)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * f * t) if kind == "sine" else 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))
    env = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    env[:na] = np.linspace(0, 1, na)
    env[-nr:] *= np.linspace(1, 0, nr)
    return (w * env * vol).astype(np.float32)

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)

music = np.zeros(mix_len, dtype=np.float32)
bpm = 104
beat = 60 / bpm
chords = [(60, 64, 67), (57, 60, 64), (53, 57, 60), (55, 59, 62)]   # C Am F G
tpos, bar = 0.0, 0
while tpos < T_END + 1:
    ch = chords[bar % 4]
    for m in ch:
        p = tone(mtof(m - 12), beat * 4, "sine", 0.09, a=0.3, r=0.6)
        s = int(tpos * SR); e = min(mix_len, s + len(p))
        music[s:e] += p[:e - s]
    for k in range(8):
        m = ch[k % 3] + (12 if k % 4 == 3 else 0)
        p = tone(mtof(m), beat * 0.5, "tri", 0.09, a=0.005, r=0.1)
        s = int((tpos + k * beat / 2) * SR); e = min(mix_len, s + len(p))
        if s < mix_len:
            music[s:e] += p[:e - s]
    b = tone(mtof(ch[0] - 24), beat * 2, "sine", 0.16, a=0.01, r=0.3)
    for off in (0, 2):
        s = int((tpos + off * beat) * SR); e = min(mix_len, s + len(b))
        if s < mix_len:
            music[s:e] += b[:e - s]
    tpos += beat * 4
    bar += 1

sfx = np.zeros(mix_len, dtype=np.float32)
PENTA = [72, 74, 76, 79, 81, 84]
rng_a = np.random.default_rng(3)
def blip(t, loud=1.0):
    p = tone(mtof(PENTA[int(rng_a.integers(len(PENTA)))]), 0.09, "sine", 0.05 * loud, a=0.003, r=0.07)
    s = int(t * SR); e = min(mix_len, s + len(p))
    if 0 <= s < mix_len:
        sfx[s:e] += p[:e - s]

# ------------------------------------------------------------------ ciz
def hl(line):
    """Basit sozdizim renklendirme: (parca, renk) listesi."""
    import re
    out = []
    code, _, com = line.partition("#")
    for tok in re.findall(r"\s+|\w+|[^\w\s]", code):
        if tok in KW:
            c = AMBER
        elif tok.replace(".", "").isdigit():
            c = CYAN
        else:
            c = WHITE
        out.append((tok, c))
    return out

BOX_X, BOX_Y, BOX_W, BOX_H = 90, 1000, 900, 720        # dunya: 10 x 8 birim -> 90 px/birim
SC = 90.0
def wpix(x, y):
    return BOX_X + x * SC, BOX_Y + BOX_H - y * SC

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
       "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
       "-pix_fmt", "yuv420p", str(TMP / "v.mp4")]
pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)

sim = None
sim_stage = 0
sim_t0 = 0.0
seed = 100
prev_vis = 0
for frame in range(TOTAL):
    t = frame / FPS
    stage = min(5, stage_at(t))
    # simulasyon: asama basinda ve (kacan topu olan asamalarda) periyodik yeniden baslat
    started = t >= (5.0 if stage == 1 else STAGE_T[stage - 1])
    restart_every = {1: 3.0, 2: 3.0, 3: 4.5, 4: None, 5: None}[stage]
    if started:
        if sim is None or sim_stage != stage or (restart_every and t - sim_t0 >= restart_every):
            seed += 1
            sim = Sim(stage, seed)
            sim_stage = stage
            sim_t0 = t
        for _ in range(2):
            sim.step()
        hits_now = sim.hits
        if hits_now > prev_vis and stage >= 3:
            for j in range(min(3, hits_now - prev_vis)):
                blip(t + j * 0.02)
        prev_vis = hits_now if sim_stage == stage else 0
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # baslik
    title = "13 satır Python"
    w = d.textlength(title, font=F_T)
    d.text(((W - w) / 2, 70), title, font=F_T, fill=WHITE)
    sub = "ile mini fizik motoru yapıyoruz"
    w = d.textlength(sub, font=F_S)
    d.text(((W - w) / 2, 150), sub, font=F_S, fill=CYAN)
    # kod paneli
    d.rounded_rectangle([60, 230, W - 60, 960], radius=24, fill=PANEL)
    d.text((90, 245), "fizik.py", font=F_S, fill=GREY)
    vis = visible_code(stage, t)
    stage_start = STAGE_T[stage - 1]
    ly = 292
    shown_chars_budget = None
    for idx, (k, st, text) in enumerate(vis):
        is_new = (st == stage and stage > 1) or (stage == 5 and k == 1)
        if stage == 1:
            # daktilo: satir satir belirir
            appear = 0.5 + idx * 0.5
            if t < appear:
                continue
        if is_new:
            d.rounded_rectangle([75, ly - 4, W - 75, ly + 46], radius=8, fill=(30, 60, 62))
            d.rectangle([75, ly - 4, 82, ly + 46], fill=GREEN)
        x = 100
        for tok, col in hl(text):
            d.text((x, ly), tok, font=F_C, fill=col)
            x += d.textlength(tok, font=F_C)
        ly += 48
    # simulasyon kutusu
    d.rounded_rectangle([BOX_X - 14, BOX_Y - 14, BOX_X + BOX_W + 14, BOX_Y + BOX_H + 14], radius=14, fill=(18, 26, 46))
    if stage >= 3:
        d.line([BOX_X - 14, BOX_Y + BOX_H, BOX_X + BOX_W + 14, BOX_Y + BOX_H], fill=GREEN, width=6)
    if stage >= 4:
        d.line([BOX_X, BOX_Y - 14, BOX_X, BOX_Y + BOX_H], fill=GREEN, width=6)
        d.line([BOX_X + BOX_W, BOX_Y - 14, BOX_X + BOX_W, BOX_Y + BOX_H], fill=GREEN, width=6)
    if started and sim is not None:
        rad = 13 if sim.n == 1 else 7
        for i in range(sim.n):
            px, py = wpix(sim.x[i], sim.y[i])
            if BOX_X - 200 < px < BOX_X + BOX_W + 200 and BOX_Y - 100 < py < BOX_Y + BOX_H + 200:
                col = AMBER if (i % 3 == 0) else CYAN
                d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=col)
        d.text((BOX_X, BOX_Y + BOX_H + 28), f"top: {sim.n}", font=F_S, fill=GREY)
    if t > T_END - 6.5:
        q = "Bin top olsa dayanır mı? 👇"
        q = "Bin top olsa dayanır mı?"
        w = d.textlength(q, font=F_B)
        d.text(((W - w) / 2, 1790), q, font=F_B, fill=AMBER)
    pipe.stdin.write(img.tobytes())
pipe.stdin.close()
pipe.wait()

# ------------------------------------------------------------------ karisim
vabs = np.abs(voice)
win = int(0.15 * SR)
env = np.convolve((vabs > 0.02).astype(np.float32), np.ones(win) / win, mode="same")
duck = 1.0 - 0.55 * np.clip(env * 3, 0, 1)
mono = music * duck + sfx * 1.0 + voice * 1.1
fade = np.ones(mix_len, dtype=np.float32)
nf = int(1.5 * SR)
fade[-nf:] = np.linspace(1, 0, nf)
mono *= fade
mono = mono / max(1.0, np.max(np.abs(mono)) / 0.9)
pcm = (np.stack([mono, mono], axis=1) * 32767).astype(np.int16)
with wave.open(str(TMP / "mix.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(TMP / "v.mp4"), "-i", str(TMP / "mix.wav"),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                str(OUT / "video.mp4")], check=True)
print("bitti", OUT / "video.mp4", T_END, "sn")
