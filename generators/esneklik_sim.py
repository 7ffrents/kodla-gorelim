"""Zipalama yarisi fizik cekirdegi (numpy): ayni boy bilyeler, 6 farkli esneklik (restitution).
Her seviyeden 10 bilye. Esneklik carpismalarda (kazik, duvar, bilye) kullanilir; bilye-bilye icin ikisinin ortalamasi."""
import numpy as np

W, H = 1080, 1920
GATE_Y = 470
FINISH_Y = 1430
XL, XR = 40, 960
RAD = 15.0
G = 900.0
PEG_R = 8.0
LEVELS = [0.15, 0.35, 0.55, 0.75, 0.90, 0.98]
PER = 10


def make_pegs():
    pegs = []
    y = 570
    row = 0
    sp = 92.0
    while y < FINISH_Y - 60:
        off = (sp / 2) if row % 2 else 0
        x = XL + 30 + off
        while x < XR - 25:
            pegs.append((x, y))
            x += sp
        y += 80
        row += 1
    return np.array(pegs)


def init_balls(seed):
    rng = np.random.default_rng(seed)
    lev = np.array([k for k in range(len(LEVELS)) for _ in range(PER)])
    lev = lev[rng.permutation(len(lev))]
    n = len(lev)
    pos = np.zeros((n, 2))
    x, y = XL + 20, GATE_Y - 40
    for i in range(n):
        if x + RAD > XR - 15:
            x = XL + 20
            y -= 2 * RAD + 4
        pos[i] = (x + RAD + rng.uniform(-2, 2), y - RAD)
        x += 2 * RAD + 4
    return pos, np.zeros((n, 2)), lev


def simulate(total_t, fps, open_t, seed=1):
    pegs = make_pegs()
    pos, vel, lev = init_balls(seed)
    n = len(lev)
    e = np.array(LEVELS)[lev]
    finish = np.full(n, np.nan)
    act = np.ones(n, dtype=bool)
    sub = 8
    dt = 1.0 / fps / sub
    frames, events = [], []
    t = 0.0
    iu = np.triu_indices(n, 1)
    for f in range(int(round(total_t * fps))):
        frames.append(pos.copy())
        for s in range(sub):
            t += dt
            vel[act, 1] += G * dt
            pos += vel * dt
            if t < open_t:
                hit = act & (pos[:, 1] + RAD > GATE_Y) & (vel[:, 1] > 0)
                pos[hit, 1] = GATE_Y - RAD
                vel[hit, 1] *= -0.2
            m = act & (pos[:, 0] - RAD < XL)
            pos[m, 0] = XL + RAD; vel[m, 0] *= -e[m]
            m = act & (pos[:, 0] + RAD > XR)
            pos[m, 0] = XR - RAD; vel[m, 0] *= -e[m]
            d = pos[:, None, :] - pegs[None, :, :]
            dist = np.linalg.norm(d, axis=2)
            pen = RAD + PEG_R - dist
            bi, pj = np.nonzero(pen > 0)
            for b, p in zip(bi, pj):
                nrm = d[b, p] / max(dist[b, p], 1e-6)
                pos[b] += nrm * pen[b, p]
                vn = vel[b] @ nrm
                if vn < 0:
                    vel[b] -= (1 + e[b]) * vn * nrm
                    if -vn > 150 and s == 0:
                        events.append((t, int(lev[b]), min(1.0, -vn / 900)))
            dx = pos[iu[1]] - pos[iu[0]]
            dd = np.linalg.norm(dx, axis=1)
            pen = 2 * RAD - dd
            for k in np.nonzero(pen > 0)[0]:
                a, b = iu[0][k], iu[1][k]
                nrm = dx[k] / max(dd[k], 1e-6)
                pos[a] -= nrm * pen[k] / 2
                pos[b] += nrm * pen[k] / 2
                rv = (vel[b] - vel[a]) @ nrm
                if rv < 0:
                    eb = 0.5 * (e[a] + e[b])
                    j = -(1 + eb) * rv / 2
                    vel[a] -= j * nrm
                    vel[b] += j * nrm
            fin = np.isnan(finish) & (pos[:, 1] > FINISH_Y)
            finish[fin] = t
            act[fin] = False
            for q in np.nonzero(fin)[0]:
                pos[q] = (-5000 - 60 * q, -5000); vel[q] = 0
        vel *= (1 - 0.1 * (1.0 / fps))
    return np.array(frames), lev, finish, events, pegs


if __name__ == "__main__":
    import sys
    seeds = [int(a) for a in sys.argv[1:]] or [1]
    for sd in seeds:
        fr, lev, ft, ev, pegs = simulate(30, 60, 1.5, seed=sd)
        print("seed", sd, "bitiren", int(np.sum(~np.isnan(ft))), "/", len(ft))
        for k, ee in enumerate(LEVELS):
            m = lev == k
            v = ft[m]
            print(f"  e={ee:.2f} bitiren {np.sum(~np.isnan(v))}/{m.sum()} ort {np.nanmean(v):.2f} min {np.nanmin(v):.2f}")
