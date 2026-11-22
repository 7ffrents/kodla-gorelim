"""Cift sarkac kaosu: 6 sarkac, baslangic farki 0,001 derece. Cikti: video.mp4 (1080x1920, 40 sn, sessiz)."""
import math
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
W, H, FPS, DUR = 1080, 1920, 30, 40
N = 6
EPS = math.radians(0.001)
G, L1, L2 = 9.81, 1.0, 1.0
BG = (11, 14, 24)
COLORS = [(255, 107, 107), (255, 169, 77), (255, 224, 102), (105, 219, 124), (77, 171, 247), (190, 130, 255)]
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
f_title = ImageFont.truetype(FB, 84)
f_sub = ImageFont.truetype(FB, 52)
f_cap = ImageFont.truetype(FB, 56)
f_small = ImageFont.truetype(FR, 34)
f_axis = ImageFont.truetype(FR, 30)

# ---- simulasyon (RK4, vektorlestirilmis) ----
def deriv(s):
    t1, t2, w1, w2 = s
    d = t1 - t2
    den = 2 - np.cos(2 * d)  # m1=m2=1, L1=L2=1
    a1 = (-G * 3 * np.sin(t1) - G * np.sin(t1 - 2 * t2) - 2 * np.sin(d) * (w2**2 * L2 + w1**2 * L1 * np.cos(d))) / (L1 * den)
    a2 = (2 * np.sin(d) * (w1**2 * L1 * 2 + 2 * G * np.cos(t1) + w2**2 * L2 * np.cos(d))) / (L2 * den)
    return np.array([w1, w2, a1, a2])

def rk4(s, h):
    k1 = deriv(s); k2 = deriv(s + h / 2 * k1); k3 = deriv(s + h / 2 * k2); k4 = deriv(s + h * k3)
    return s + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

s = np.zeros((4, N))
s[0] = 1.0 + EPS * np.arange(N)
s[1] = 2.0
sub = 20
h = 1.0 / FPS / sub
frames_state = []
for f in range(FPS * DUR + 1):
    frames_state.append(s.copy())
    for _ in range(sub):
        s = rk4(s, h)
st = np.array(frames_state)  # (F,4,N)
x1 = L1 * np.sin(st[:, 0]); y1 = L1 * np.cos(st[:, 0])
x2 = x1 + L2 * np.sin(st[:, 1]); y2 = y1 + L2 * np.cos(st[:, 1])
sep = np.hypot(x2[:, -1] - x2[:, 0], y2[:, -1] - y2[:, 0])
sep = np.maximum(sep, 1e-9)
print("baslangic ayrim", sep[0], "maks", sep.max(), "kat", sep.max() / sep[1])

PX = 235.0
PIV = (540, 760)
def P(x, y):
    return (PIV[0] + x * PX, PIV[1] + y * PX)

# alt grafik alani
GX0, GX1, GY0, GY1 = 140, 1000, 1330, 1640
LO, HI = -5.0, 1.0  # log10 aralik

def blend(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))

def center_text(d, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)

def caption(t):
    if t < 3.5: return ["Altı çift sarkaç, aynı yerden bırakıldı.", "Aralarındaki fark: sadece 0,001°"]
    if t < 11: return ["Şimdilik hepsi aynı yolda…", "göz ayırt edemiyor."]
    if t < 21: return ["Ama fark her saniye", "katlanarak büyüyor."]
    if t < 31: return ["Artık hiçbiri ötekini", "takip etmiyor."]
    return ["Küçük bir fark, büyük bir sonuç:", "buna kaos denir."]

TRAIL = 70
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
tip = [[P(x2[f, k], y2[f, k]) for k in range(N)] for f in range(len(x2))]
for f in range(FPS * DUR):
    t = f / FPS
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    center_text(d, 110, "ÇİFT SARKAÇ", f_title, (240, 244, 255))
    center_text(d, 215, "Kaosun en yalın hâli", f_sub, (150, 165, 200))
    # izler
    for k in range(N):
        c = COLORS[k]
        a0 = max(0, f - TRAIL)
        for i in range(a0, f):
            a = 0.10 + 0.9 * (i - a0) / TRAIL
            d.line([tip[i][k], tip[i + 1][k]], fill=blend(c, a * 0.9), width=5)
    # sarkaclar
    for k in range(N):
        c = COLORS[k]
        p0 = PIV; p1 = P(x1[f, k], y1[f, k]); p2 = tip[f][k]
        d.line([p0, p1, p2], fill=blend(c, 0.55), width=4)
        d.ellipse([p1[0] - 8, p1[1] - 8, p1[0] + 8, p1[1] + 8], fill=blend(c, 0.8))
        d.ellipse([p2[0] - 13, p2[1] - 13, p2[0] + 13, p2[1] + 13], fill=c)
    d.ellipse([PIV[0] - 10, PIV[1] - 10, PIV[0] + 10, PIV[1] + 10], fill=(240, 244, 255))
    # zaman
    d.text((70, 1215), f"t = {t:4.1f} sn", font=f_sub, fill=(200, 210, 235))
    # grafik
    d.text((GX0, 1280), "Sarkaçlar arası uzaklık (logaritmik)", font=f_small, fill=(150, 165, 200))
    d.rectangle([GX0, GY0, GX1, GY1], outline=(60, 70, 100), width=2)
    for e in range(-5, 2):
        y = GY1 - (e - LO) / (HI - LO) * (GY1 - GY0)
        d.line([GX0, y, GX1, y], fill=(30, 36, 56), width=1)
        d.text((GX0 - 12, y - 17), f"10{'⁻' if e<0 else ''}{'⁰¹²³⁴⁵⁶⁷⁸⁹'[abs(e)]}", font=f_axis, fill=(120, 135, 170), anchor="rt")
    pts = []
    for i in range(0, f + 1):
        xx = GX0 + (i / (FPS * DUR)) * (GX1 - GX0)
        yy = GY1 - (np.log10(sep[i]) - LO) / (HI - LO) * (GY1 - GY0)
        pts.append((xx, min(max(yy, GY0), GY1)))
    if len(pts) > 1:
        d.line(pts, fill=(255, 224, 102), width=5)
    d.ellipse([pts[-1][0] - 9, pts[-1][1] - 9, pts[-1][0] + 9, pts[-1][1] + 9], fill=(255, 224, 102))
    d.text((GX1, GY1 + 12), "zaman →", font=f_axis, fill=(120, 135, 170), anchor="rt")
    # altyazi
    lines = caption(t)
    for i, ln in enumerate(lines):
        center_text(d, 1715 + i * 70, ln, f_cap, (255, 255, 255))
    # son kart
    if t > 37:
        center_text(d, 1855, "Kodla Görelim", f_small, (150, 165, 200))
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
