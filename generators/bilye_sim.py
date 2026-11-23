"""Bilye yarisi fizik cekirdegi (numpy). 60 bilye, 3 boy, esit yogunluk."""
import numpy as np

W, H = 1080, 1920
GATE_Y = 560            # kapi (acilana kadar bilyeleri tutar)
FINISH_Y = 1340
XL, XR = 40, 960
R = {0: 11.0, 1: 19.0, 2: 29.0}   # kucuk, orta, buyuk
G = 900.0
REST = 0.45


def make_pegs(seed=3):
    rng = np.random.default_rng(seed)
    pegs = []
    y = 650
    row = 0
    while y < FINISH_Y - 50:
        # dar bolge (filtre): orta kisim, buyuklere zor
        narrow = 850 < y < 1090
        sp = 62.0 if narrow else 104.0
        off = (sp / 2) if row % 2 else 0
        x = XL + 20 + off
        while x < XR - 20:
            # dar bolgede tek bir genis gecit (buyukler de gecebilsin)
            if not (narrow and 700 < x < 790):
                pegs.append((x, y))
            x += sp
        y += 78
        row += 1
    pegs = np.array(pegs)
    return pegs


PEG_R = 7.0


def init_balls(seed=11, per=20):
    rng = np.random.default_rng(seed)
    radii = np.array([R[k] for k in range(3) for _ in range(per)])
    kinds = np.array([k for k in range(3) for _ in range(per)])
    order = rng.permutation(len(radii))
    radii, kinds = radii[order], kinds[order]
    n = len(radii)
    pos = np.zeros((n, 2))
    # yigin: gece ustunde satirlara diz
    x, y, rowmax = XL + 40, GATE_Y - 90, 0
    for i in range(n):
        r = radii[i]
        if x + r > XR - 20:
            x = XL + 40
            y -= rowmax * 2 + 6
            rowmax = 0
        pos[i] = (x + r + rng.uniform(-3, 3), y - r - rng.uniform(0, 40))
        x += 2 * r + 6
        rowmax = max(rowmax, r)
    vel = np.zeros((n, 2))
    return pos, vel, radii, kinds


def simulate(total_t, fps, open_t, seed=11, per=20):
    pegs = make_pegs()
    pos, vel, rad, kinds = init_balls(seed, per)
    n = len(rad)
    mass = rad ** 2
    finish_time = np.full(n, np.nan)
    act = np.ones(n, dtype=bool)
    sub = 8
    dt = 1.0 / fps / sub
    frames = []
    events = []   # (t, kind, strength)
    t = 0.0
    iu = np.triu_indices(n, 1)
    for f in range(int(round(total_t * fps))):
        frames.append(pos.copy())
        for s in range(sub):
            t += dt
            vel[act, 1] += G * dt
            pos += vel * dt
            # kapi
            if t < open_t:
                hit = act & (pos[:, 1] + rad > GATE_Y) & (vel[:, 1] > 0)
                pos[hit, 1] = GATE_Y - rad[hit]
                vel[hit, 1] *= -REST * 0.5
            # duvarlar
            m = act & (pos[:, 0] - rad < XL)
            pos[m, 0] = XL + rad[m]; vel[m, 0] *= -REST
            m = act & (pos[:, 0] + rad > XR)
            pos[m, 0] = XR - rad[m]; vel[m, 0] *= -REST
            # kazik carpismasi
            d = pos[:, None, :] - pegs[None, :, :]
            dist = np.linalg.norm(d, axis=2)
            pen = rad[:, None] + PEG_R - dist
            bi, pj = np.nonzero(pen > 0)
            for b, p in zip(bi, pj):
                nrm = d[b, p] / max(dist[b, p], 1e-6)
                pos[b] += nrm * pen[b, p]
                vn = vel[b] @ nrm
                if vn < 0:
                    vel[b] -= (1 + REST) * vn * nrm
                    if -vn > 120 and s == 0:
                        events.append((t, int(kinds[b]), min(1.0, -vn / 900)))
            # bilye-bilye
            dx = pos[iu[1]] - pos[iu[0]]
            dd = np.linalg.norm(dx, axis=1)
            pen = rad[iu[0]] + rad[iu[1]] - dd
            idx = np.nonzero(pen > 0)[0]
            for k in idx:
                a, b = iu[0][k], iu[1][k]
                nrm = dx[k] / max(dd[k], 1e-6)
                ma, mb = mass[a], mass[b]
                tot = ma + mb
                pos[a] -= nrm * pen[k] * mb / tot
                pos[b] += nrm * pen[k] * ma / tot
                rv = (vel[b] - vel[a]) @ nrm
                if rv < 0:
                    if -rv > 150 and s == 0:
                        events.append((t, int(kinds[a if rad[a] < rad[b] else b]), min(1.0, -rv / 900)))
                    j = -(1 + REST) * rv / (1 / ma + 1 / mb)
                    vel[a] -= j / ma * nrm
                    vel[b] += j / mb * nrm
            # bitis
            fin = np.isnan(finish_time) & (pos[:, 1] > FINISH_Y)
            finish_time[fin] = t
            act[fin] = False
            for q in np.nonzero(fin)[0]:
                pos[q] = (-5000 - 60 * q, -5000); vel[q] = 0
        vel *= (1 - 0.15 * (1.0 / fps))
    return np.array(frames), rad, kinds, finish_time, events, pegs


if __name__ == "__main__":
    import sys
    fr, rad, kinds, ft, ev, pegs = simulate(40, 30, 1.8)
    order = np.argsort(np.where(np.isnan(ft), 1e9, ft))
    print("bitiren", np.sum(~np.isnan(ft)), "/", len(ft))
    print("ilk 10 boyutlari", kinds[order[:10]], "ilk", ft[order[0]])
    for k in range(3):
        m = kinds == k
        print("boy", k, "bitiren", np.sum(~np.isnan(ft[m])), "ort", np.nanmean(ft[m]) if np.any(~np.isnan(ft[m])) else None)
