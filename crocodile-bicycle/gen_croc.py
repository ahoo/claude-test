#!/usr/bin/env python3
"""Generate an animated SVG: a crocodile riding a bicycle (SMIL animation).

Legs are solved with two-bone inverse kinematics so the feet stay on the pedals.
"""
import math
import sys
import xml.etree.ElementTree as ET

OUT = sys.argv[1] if len(sys.argv) > 1 else "croc_bike.svg"
TAU = 2 * math.pi
W, HT = 800, 520

# ---------- palette ----------
GREEN = "#6bbf59"
GREEN_D = "#2d5a27"
GREEN_DD = "#3f8a3a"
GREEN_FAR = "#4f9a43"
BELLY = "#e9f7b9"
FRAME = "#ff7f3f"
FRAME_D = "#b9501f"
TIRE = "#22232b"
HELMET = "#3a86ff"
HELMET_D = "#1f4fb3"
SCARF = "#ff5d8f"
SCARF_D = "#b8325e"
SADDLE = "#1d1f26"
INK = "#1c2a1a"
TEETH = "#fffdf2"

# ---------- rig geometry (px) ----------
RH = (230, 384)      # rear hub
FH = (530, 384)      # front hub
BB = (355, 402)      # bottom bracket
SEAT = (302, 240)    # seat tube top
HTOP = (478, 262)    # head tube top
HBOT = (486, 296)    # head tube bottom
STEM = (484, 228)    # steerer top
GRIP = (524, 210)    # handlebar grip centre
SHO = (372, 152)     # shoulder
HIP = (291, 242)     # hip, sitting on the saddle
CRANK = 44
L_THIGH, L_SHIN = 106, 96
ARM_UP, ARM_FORE = 88, 84
EYE = (430, 114)
SUN = (690, 96)
N = 48               # frames per pedal revolution

# ---------- math helpers ----------

def fmt(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s in ("-0", "-0.0"):
        s = "0"
    return s


def P(p):
    return f"{fmt(p[0])} {fmt(p[1])}"


def poly(pts):
    return "M" + " L".join(P(p) for p in pts) + " Z"


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(a):
    l = math.hypot(a[0], a[1]) or 1e-9
    return (a[0] / l, a[1] / l)


def pol(c, r, a):
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def capsule(A, B, ra, rb, n=6):
    """Tapered limb as a closed polygon with a fixed point count (animatable)."""
    u = unit(sub(B, A))
    nrm = (-u[1], u[0])
    pts = []
    for i in range(n):
        phi = math.pi * i / (n - 1)
        v = add(mul(nrm, math.cos(phi)), mul(u, math.sin(phi)))
        pts.append(add(B, mul(v, rb)))
    for i in range(n):
        phi = math.pi * i / (n - 1)
        w = add(mul(nrm, -math.cos(phi)), mul(u, -math.sin(phi)))
        pts.append(add(A, mul(w, ra)))
    return pts


def ribbon(center, widths):
    """Tapered strip along a centre line (fixed point count)."""
    n = len(center)
    left, right = [], []
    for i in range(n):
        a = center[max(i - 1, 0)]
        b = center[min(i + 1, n - 1)]
        d = unit(sub(b, a))
        nrm = (-d[1], d[0])
        w = widths[i] / 2
        left.append(add(center[i], mul(nrm, w)))
        right.append(add(center[i], mul(nrm, -w)))
    return left + right[::-1]


def two_bone(Hp, T, L1, L2, pick):
    """Two-segment IK. Returns (joint, end). `pick(c1, c2)` True -> c1."""
    d = dist(Hp, T)
    d_c = min(max(d, abs(L1 - L2) + 0.5), L1 + L2 - 0.5)
    u = unit(sub(T, Hp))
    end = add(Hp, mul(u, d_c))
    a = (L1 * L1 - L2 * L2 + d_c * d_c) / (2 * d_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    base = add(Hp, mul(u, a))
    n = (-u[1], u[0])
    c1 = add(base, mul(n, h))
    c2 = add(base, mul(n, -h))
    return (c1 if pick(c1, c2) else c2), end


def bez(Pts, t):
    mt = 1 - t
    return (mt ** 3 * Pts[0][0] + 3 * mt * mt * t * Pts[1][0] + 3 * mt * t * t * Pts[2][0] + t ** 3 * Pts[3][0],
            mt ** 3 * Pts[0][1] + 3 * mt * mt * t * Pts[1][1] + 3 * mt * t * t * Pts[2][1] + t ** 3 * Pts[3][1])


def bez_d(Pts, t):
    mt = 1 - t
    return (3 * (mt * mt * (Pts[1][0] - Pts[0][0]) + 2 * mt * t * (Pts[2][0] - Pts[1][0]) + t * t * (Pts[3][0] - Pts[2][0])),
            3 * (mt * mt * (Pts[1][1] - Pts[0][1]) + 2 * mt * t * (Pts[2][1] - Pts[1][1]) + t * t * (Pts[3][1] - Pts[2][1])))


def bez_y_at_x(Pts, x):
    best = None
    for i in range(801):
        bx, by = bez(Pts, i / 800)
        if best is None or abs(bx - x) < abs(best[0] - x):
            best = (bx, by)
    return best[1]


# ---------- SVG helpers ----------

def line(a, b, col, w, extra=""):
    return (f'<line x1="{fmt(a[0])}" y1="{fmt(a[1])}" x2="{fmt(b[0])}" y2="{fmt(b[1])}" '
            f'stroke="{col}" stroke-width="{fmt(w)}" stroke-linecap="round" {extra}/>')


def anim_rot(cx, cy, a0, a1, dur):
    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{a0} {cx} {cy}" to="{a1} {cx} {cy}" dur="{dur}" repeatCount="indefinite"/>')


def anim_trans(x0, y0, x1, y1, dur):
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'from="{x0} {y0}" to="{x1} {y1}" dur="{dur}" repeatCount="indefinite"/>')


def anim_d(frames, dur):
    n = len(frames)
    kt = ";".join(f"{i / (n - 1):.4f}" for i in range(n))
    vals = ";".join(frames)
    return (f'<animate attributeName="d" dur="{dur}" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{kt}" values="{vals}"/>')


# ---------- scenery ----------

def cloud(x, y, s):
    return (f'<g transform="translate({fmt(x)} {fmt(y)}) scale({s})" fill="#ffffff" opacity="0.95">'
            '<circle cx="0" cy="0" r="16"/><circle cx="20" cy="-10" r="22"/>'
            '<circle cx="44" cy="-2" r="17"/><ellipse cx="22" cy="6" rx="42" ry="12"/></g>')


def hill(base, a1, k1, a2, k2, ph2, bottom, color):
    pts = []
    x = -W
    while x <= 2 * W:
        y = base - a1 * math.sin(TAU * k1 * x / W) - a2 * math.sin(TAU * k2 * x / W + ph2)
        pts.append((x, y))
        x += 8
    d = "M" + " L".join(P(p) for p in pts) + f" L{2 * W} {bottom} L{-W} {bottom} Z"
    return f'<path d="{d}" fill="{color}"/>'


TREES = [(30, 'p', 1.0), (115, 'b', 1.0), (200, 'p', 0.8), (300, 'b', 1.2), (385, 'p', 1.1),
         (470, 'b', 0.9), (560, 'p', 0.9), (660, 'b', 1.1), (745, 'p', 1.0)]


def tree(x, kind, s):
    base = 456
    if kind == 'p':
        return (f'<path d="M{fmt(x - 24 * s)} {base} L{fmt(x)} {fmt(base - 52 * s)} L{fmt(x + 24 * s)} {base} Z" fill="#4f9e5f"/>'
                f'<path d="M{fmt(x - 17 * s)} {fmt(base - 30 * s)} L{fmt(x)} {fmt(base - 84 * s)} '
                f'L{fmt(x + 17 * s)} {fmt(base - 30 * s)} Z" fill="#5fae68"/>')
    return (f'<circle cx="{fmt(x - 10 * s)}" cy="{fmt(base - 6 * s)}" r="{fmt(12 * s)}" fill="#7cc26d"/>'
            f'<circle cx="{fmt(x + 6 * s)}" cy="{fmt(base - 10 * s)}" r="{fmt(16 * s)}" fill="#7cc26d"/>'
            f'<circle cx="{fmt(x + 20 * s)}" cy="{fmt(base - 4 * s)}" r="{fmt(11 * s)}" fill="#7cc26d"/>')


# ---------- bicycle ----------

def tube(a, b, w):
    return line(a, b, FRAME_D, w + 3.5) + line(a, b, FRAME, w)


def wheel(hub, cog=False):
    hx, hy = hub
    sp = []
    for i in range(16):
        a = TAU * i / 16
        sp.append(line(pol(hub, 8, a), pol(hub, 58, a), "#dfe5ec", 1.1))
    if cog:
        sp.append(f'<circle cx="{hx}" cy="{hy}" r="11" fill="none" stroke="#6b7483" '
                  f'stroke-width="5" stroke-dasharray="2.5 2.2"/>')
    sp.append(f'<circle cx="{hx}" cy="{hy}" r="7" fill="#8a95a3"/>')
    sp.append(f'<circle cx="{hx}" cy="{hy}" r="2.5" fill="#2b2e36"/>')
    tread = (f'<circle cx="{hx}" cy="{hy}" r="70" fill="none" stroke="#434853" '
             f'stroke-width="3" stroke-dasharray="5 7"/>')
    spokes = "".join(sp)
    return (f'<circle cx="{hx}" cy="{hy}" r="70" fill="none" stroke="{TIRE}" stroke-width="10"/>'
            f'<circle cx="{hx}" cy="{hy}" r="60" fill="none" stroke="#aab4c0" stroke-width="2.5"/>'
            f'<g>{tread}{spokes}{anim_rot(hx, hy, 0, 360, "1s")}</g>')


def crank_group(far):
    a0, a1 = (180, 540) if far else (0, 360)
    arm = line(BB, (BB[0] + CRANK, BB[1]), "#4c525c", 6)
    pedal = (f'<circle cx="{BB[0] + CRANK}" cy="{BB[1]}" r="6.5" fill="#2b2e36" '
             f'stroke="#8a929c" stroke-width="1.5"/>')
    return (f'<g>{arm}{pedal}'
            f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{a0} {BB[0]} {BB[1]}" to="{a1} {BB[0]} {BB[1]}" dur="1s" repeatCount="indefinite"/></g>')


def chainring_svg():
    ring = (f'<circle cx="{BB[0]}" cy="{BB[1]}" r="20" fill="none" stroke="#9aa4b1" '
            f'stroke-width="3.5" stroke-dasharray="5 4"/>')
    return (f'<g>{ring}{anim_rot(BB[0], BB[1], 0, 360, "1s")}</g>'
            f'<circle cx="{BB[0]}" cy="{BB[1]}" r="6" fill="#444b57"/>')


# ---------- crocodile ----------

TORSO_D = ("M262 236 C252 200 270 150 318 132 C340 122 372 116 392 122 "
           "C412 128 420 150 414 172 C410 196 396 214 372 226 "
           "C352 238 330 262 298 266 C282 268 268 258 262 236 Z")

HEAD_D = ("M366 116 C382 98 418 90 452 96 C480 100 500 110 524 120 "
          "C534 124 534 134 518 138 C482 152 430 160 386 152 "
          "C368 148 362 130 366 116 Z")

MOUTH_BEZ = [(386, 152), (430, 160), (482, 152), (518, 138)]
MOUTH_D = "M386 152 C430 160 482 152 518 138"

JAW_D = ("M386 152 C430 160 482 152 518 138 C526 142 524 152 512 160 "
         "C478 172 430 174 392 164 C384 160 382 156 386 152 Z")

TAIL_C = [(268, 252), (222, 272), (158, 278), (96, 236)]


def leg_pose(th):
    p = pedal_pos(th)
    ankle_t = (p[0] - 6, p[1] - 14)
    knee, ankle = two_bone(HIP, ankle_t, L_THIGH, L_SHIN, pick=lambda c1, c2: c1[0] >= c2[0])
    toe = (p[0] + 16, p[1] - 4)
    return knee, ankle, toe


def pedal_pos(th):
    return pol(BB, CRANK, th)


def leg_paths(far):
    off = math.pi if far else 0.0
    thigh, shin, foot = [], [], []
    for k in range(N + 1):
        th = TAU * k / N + off
        knee, ankle, toe = leg_pose(th)
        thigh.append(poly(capsule(HIP, knee, 17, 13)))
        shin.append(poly(capsule(knee, ankle, 13, 9)))
        foot.append(poly(capsule(ankle, toe, 9, 7)))
    fill = GREEN_FAR if far else GREEN
    out = []
    for frames in (thigh, shin, foot):
        out.append(f'<path d="{frames[0]}" fill="{fill}" stroke="{GREEN_D}" stroke-width="2.6" '
                   f'stroke-linejoin="round">{anim_d(frames, "1s")}</path>')
    return "".join(out)


def tail_svg():
    center = [bez(TAIL_C, i / 24) for i in range(25)]
    widths = [3 + 25 * (1 - i / 24) ** 1.1 for i in range(25)]
    parts = [f'<path d="{poly(ribbon(center, widths))}" fill="{GREEN}" stroke="{GREEN_D}" '
             f'stroke-width="2.6" stroke-linejoin="round"/>']
    for t in (0.22, 0.42, 0.62, 0.8):
        c = bez(TAIL_C, t)
        d = unit(bez_d(TAIL_C, t))
        n = (-d[1], d[0])
        w = (3 + 25 * (1 - t) ** 1.1) / 2 * 0.85
        parts.append(line(add(c, mul(n, w)), sub(c, mul(n, w)), GREEN_DD, 2.6))
    return (f'<g>{"".join(parts)}'
            f'<animateTransform attributeName="transform" type="rotate" '
            f'values="-4 268 252;6 268 252;-4 268 252" dur="1.6s" repeatCount="indefinite"/></g>')


def torso_svg():
    s = [f'<path d="{TORSO_D}" fill="{GREEN}"/>',
         '<g clip-path="url(#torsoClip)">',
         f'<path d="M378 110 L446 110 L446 280 L330 286 C352 262 372 240 388 216 '
         f'C404 192 414 170 412 150 C410 132 396 118 378 110 Z" fill="{BELLY}"/>',
         '</g>',
         f'<path d="{TORSO_D}" fill="none" stroke="{GREEN_D}" stroke-width="3" stroke-linejoin="round"/>']
    # sheen along the top of the back and a few scale marks
    s.append('<path d="M300 150 C310 136 330 128 352 124" fill="none" stroke="#d9f5bd" '
             'stroke-width="4" stroke-linecap="round" opacity="0.6"/>')
    for (x, y) in [(300, 190), (322, 176), (340, 198), (296, 222), (320, 218), (346, 224)]:
        s.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{GREEN_D}" opacity="0.28"/>')
    seg0 = ((262, 236), (252, 200), (270, 150), (318, 132))
    for t in (0.18, 0.34, 0.5, 0.66, 0.82):
        B = bez(seg0, t)
        D = unit(bez_d(seg0, t))
        o = (D[1], -D[0])               # outward (away from the body)
        b1 = add(B, mul(D, 5.5))
        b2 = add(B, mul(D, -5.5))
        ap = add(B, mul(o, 8))
        s.append(f'<path d="{poly([b2, ap, b1])}" fill="{GREEN_DD}" stroke="{GREEN_D}" '
                 f'stroke-width="1.5" stroke-linejoin="round"/>')
    return "".join(s)


def scarf_svg():
    # scarf streams back from the neck, above the shoulders, and flutters
    frames = []
    for k in range(9):
        ph = TAU * k / 8
        center = []
        for i in range(9):
            x = 380 - i * 17
            y = 124 - i * 2.2 + 8 * (i / 8) * math.sin(ph - i * 0.8)
            center.append((x, y))
        widths = [10.5 - i * 0.8 for i in range(9)]
        frames.append(poly(ribbon(center, widths)))
    return (f'<path d="{frames[0]}" fill="{SCARF}" stroke="{SCARF_D}" stroke-width="1.5" '
            f'stroke-linejoin="round">{anim_d(frames, "1.2s")}</path>')


def arm_svg():
    elbow, _ = two_bone(SHO, GRIP, ARM_UP, ARM_FORE, pick=lambda c1, c2: c1[1] >= c2[1])
    wrist = (GRIP[0] - 7, GRIP[1] + 1)
    return (f'<path d="{poly(capsule(SHO, elbow, 11, 9))}" fill="{GREEN}" stroke="{GREEN_D}" '
            f'stroke-width="2.6" stroke-linejoin="round"/>'
            f'<path d="{poly(capsule(elbow, wrist, 9, 7.5))}" fill="{GREEN}" stroke="{GREEN_D}" '
            f'stroke-width="2.6" stroke-linejoin="round"/>'
            f'<circle cx="{GRIP[0] + 2}" cy="{GRIP[1] + 1}" r="9" fill="{GREEN}" '
            f'stroke="{GREEN_D}" stroke-width="2.4"/>')


def tooth(x, y, down):
    if down:
        pts = [(x - 3.6, y - 2), (x, y + 7), (x + 3.6, y - 2)]
    else:
        pts = [(x - 3.6, y + 2), (x, y - 7), (x + 3.6, y + 2)]
    return (f'<path d="{poly(pts)}" fill="{TEETH}" stroke="{INK}" stroke-width="0.9" '
            f'stroke-linejoin="round"/>')


def head_svg():
    ex, ey = EYE
    s = [
        f'<path d="{HEAD_D}" fill="{GREEN}" stroke="{GREEN_D}" stroke-width="3" stroke-linejoin="round"/>',
        f'<path d="{JAW_D}" fill="#cdeaa6" stroke="{GREEN_D}" stroke-width="3" stroke-linejoin="round"/>',
        '<path d="M404 128 C424 120 446 120 468 126" fill="none" stroke="#ffffff" '
        'stroke-width="3" stroke-linecap="round" opacity="0.35"/>',
        f'<path d="{MOUTH_D}" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>',
    ]
    for x in (446, 464, 482, 500):
        s.append(tooth(x, bez_y_at_x(MOUTH_BEZ, x), down=True))
    for x in (455, 473, 491, 508):
        s.append(tooth(x, bez_y_at_x(MOUTH_BEZ, x), down=False))
    s.append(f'<path d="M414 104 Q430 95 447 103" fill="none" stroke="{GREEN_D}" '
             f'stroke-width="3" stroke-linecap="round"/>')
    s.append(
        f'<circle cx="{ex}" cy="{ey}" r="9" fill="#fff3a0" stroke="{INK}" stroke-width="1.5"/>'
        f'<circle cx="{ex}" cy="{ey}" r="6.5" fill="#f5a300"/>'
        f'<ellipse cx="{ex}" cy="{ey}" rx="2.2" ry="6" fill="#0d0d0d"/>'
        f'<circle cx="{ex + 2.5}" cy="{ey - 3}" r="1.5" fill="#ffffff"/>'
        f'<ellipse cx="{ex}" cy="{ey}" rx="10" ry="0" fill="{GREEN}">'
        f'<animate attributeName="ry" values="0;0;10;0;0" keyTimes="0;0.9;0.94;0.98;1" '
        f'dur="3.4s" repeatCount="indefinite"/></ellipse>')
    s.append(f'<circle cx="515" cy="123" r="2.6" fill="{INK}"/>')
    s.append(
        f'<path d="M356 128 C352 96 382 72 418 72 C444 72 458 88 462 102 L448 104 '
        f'C436 98 414 96 398 104 C384 110 374 120 368 136 Z" fill="{HELMET}" stroke="{HELMET_D}" '
        f'stroke-width="2.5" stroke-linejoin="round"/>'
        f'<path d="M368 110 C386 88 420 82 448 92" fill="none" stroke="#ffffff" stroke-width="4" '
        f'stroke-linecap="round" opacity="0.85"/>'
        f'<path d="M364 130 C366 142 376 150 388 152" fill="none" stroke="{HELMET_D}" '
        f'stroke-width="3" stroke-linecap="round"/>')
    body = "".join(s)
    return (f'<g>{body}'
            f'<animateTransform attributeName="transform" type="rotate" '
            f'values="-1.5 380 150;1.5 380 150;-1.5 380 150" dur="1.6s" repeatCount="indefinite"/></g>')


# ---------- assembly ----------

def build():
    out = []
    A = out.append

    A(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {HT}" width="{W}" height="{HT}">')
    A('<title>鳄鱼骑自行车</title>')
    A('<defs>'
      '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#5fc3ff"/><stop offset="0.7" stop-color="#cdf0ff"/>'
      '<stop offset="1" stop-color="#f1fbff"/></linearGradient>'
      '<linearGradient id="road" x1="0" y1="0" x2="0" y2="1">'
      '<stop offset="0" stop-color="#4a5366"/><stop offset="1" stop-color="#2d3442"/></linearGradient>'
      f'<clipPath id="torsoClip"><path d="{TORSO_D}"/></clipPath>'
      '</defs>')

    # sky + sun
    A(f'<rect width="{W}" height="{HT}" fill="url(#sky)"/>')
    rays = "".join(line(pol(SUN, 46, a), pol(SUN, 62, a), "#ffd23f", 4)
                   for a in [TAU * i / 12 for i in range(12)])
    A(f'<circle cx="{SUN[0]}" cy="{SUN[1]}" r="60" fill="#fff3b0" opacity="0.5"/>')
    A(f'<g>{rays}{anim_rot(SUN[0], SUN[1], 0, 360, "16s")}</g>')
    A(f'<circle cx="{SUN[0]}" cy="{SUN[1]}" r="34" fill="#ffd23f"/>')

    # clouds (seamless loop)
    cl = []
    for k in (-1, 0, 1, 2):
        for (x, y, s) in [(120, 84, 1.0), (360, 50, 0.8), (600, 150, 0.7)]:
            cl.append(cloud(x + W * k, y, s))
    A(f'<g>{"".join(cl)}{anim_trans(0, 0, -W, 0, "24s")}</g>')

    # distant hills, nearer hills (parallax)
    A(f'<g>{hill(386, 16, 1, 8, 3, 1.2, 480, "#a9e0b0")}{anim_trans(0, 0, -W, 0, "13s")}</g>')
    A(f'<g>{hill(414, 10, 2, 6, 5, 0.6, 480, "#8fd182")}{anim_trans(0, 0, -W, 0, "8s")}</g>')

    # trees / bushes
    tr = []
    for k in (-1, 0, 1, 2):
        for (x, kind, s) in TREES:
            tr.append(tree(x + W * k, kind, s))
    A(f'<g>{"".join(tr)}{anim_trans(0, 0, -W, 0, "5s")}</g>')

    # grass strip, road, lane dashes
    A('<rect x="0" y="452" width="800" height="10" fill="#86cf6e"/>')
    A(f'<rect x="0" y="460" width="800" height="60" fill="url(#road)"/>')
    A('<rect x="0" y="460" width="800" height="3" fill="#dfe5ec"/>')
    dashes = "".join(f'<rect x="{i * 113}" y="492" width="56" height="6" rx="3" fill="#ffd23f"/>'
                     for i in range(-1, 9))
    A(f'<g>{dashes}{anim_trans(0, 0, -113, 0, "0.25s")}</g>')

    # ground shadow
    A('<ellipse cx="330" cy="468" rx="215" ry="8" fill="#151a24" opacity="0.28"/>')

    # speed lines (behind rider)
    for (x, y, L, b) in [(40, 196, 70, 0), (70, 236, 50, 0.12), (30, 276, 90, 0.25),
                         (90, 318, 56, 0.4), (50, 372, 74, 0.18), (120, 420, 44, 0.32)]:
        A(f'<g transform="translate({x} {y})"><line x1="0" y1="0" x2="{L}" y2="0" stroke="#ffffff" '
          f'stroke-width="3" stroke-linecap="round" opacity="0">'
          f'<animate attributeName="opacity" values="0;0.85;0" keyTimes="0;0.3;1" dur="0.5s" '
          f'begin="{b}s" repeatCount="indefinite"/>'
          f'<animateTransform attributeName="transform" type="translate" from="0 0" to="-70 0" '
          f'dur="0.5s" begin="{b}s" repeatCount="indefinite"/></line></g>')

    # dust puffs behind the rear wheel
    for b in (0, 0.23, 0.46):
        A(f'<circle cx="176" cy="455" r="3" fill="#dfe6ee">'
          f'<animate attributeName="r" values="3;17" dur="0.7s" begin="{b}s" repeatCount="indefinite"/>'
          f'<animate attributeName="opacity" values="0.9;0" dur="0.7s" begin="{b}s" repeatCount="indefinite"/>'
          f'<animate attributeName="cx" values="176;140" dur="0.7s" begin="{b}s" repeatCount="indefinite"/>'
          f'</circle>')

    # ---------- the rig ----------
    A('<g id="rig">')
    A(tail_svg())                                   # tail (behind everything)
    A(crank_group(far=True))                        # far crank
    A(leg_paths(far=True))                          # far leg
    A(tube(BB, RH, 8) + tube(SEAT, RH, 6) + tube(BB, SEAT, 9)
      + tube(SEAT, HTOP, 9) + tube(BB, HBOT, 10) + tube(HTOP, HBOT, 14))
    A(wheel(RH, cog=True))                          # rear wheel
    A(line((BB[0], BB[1] - 20), (RH[0], RH[1] - 12), "#2b2e36", 2.4)
      + line((BB[0], BB[1] + 20), (RH[0], RH[1] + 12), "#2b2e36", 2.4))   # chain
    A(wheel(FH))                                    # front wheel
    A(tube(HBOT, FH, 9) + tube(HTOP, STEM, 7))      # fork + steerer
    A(f'<path d="M{STEM[0]} {STEM[1]} Q494 204 516 206 L530 211" fill="none" stroke="#2b2e36" '
      f'stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>')
    A(line((516, 206), (534, 214), "#15161a", 9))  # grip
    A(f'<path d="M280 238 C288 228 320 226 332 234 C336 240 326 248 302 249 C290 250 279 245 280 238 Z" '
      f'fill="{SADDLE}"/>')                          # saddle
    A(chainring_svg())
    A(crank_group(far=False))                       # near crank
    A(scarf_svg())                                  # scarf (behind torso, flies out above the back)
    A(torso_svg())                                  # torso
    A(arm_svg())                                    # near arm + hand
    A(head_svg())                                   # head with helmet
    A(leg_paths(far=False))                         # near leg (on top)
    A('</g>')

    # musical notes floating up
    A(f'<text x="468" y="62" font-size="26" fill="#2f6fd6" font-family="Arial, sans-serif" opacity="0">'
      '♪<animate attributeName="y" values="62;22" dur="2.4s" repeatCount="indefinite"/>'
      '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.7;1" dur="2.4s" '
      'repeatCount="indefinite"/></text>')
    A(f'<text x="500" y="46" font-size="22" fill="#ff5d8f" font-family="Arial, sans-serif" opacity="0">'
      '♫<animate attributeName="y" values="46;6" dur="2.4s" begin="1.2s" repeatCount="indefinite"/>'
      '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.7;1" dur="2.4s" '
      'begin="1.2s" repeatCount="indefinite"/></text>')

    A('</svg>')
    return "\n".join(out)


if __name__ == "__main__":
    svg = build()
    ET.fromstring(svg.encode("utf-8"))   # sanity: well-formed XML
    with open(OUT, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(svg)
        f.write("\n")
    print(f"wrote {OUT} ({len(svg)} bytes)")
