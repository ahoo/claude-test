#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Procedurally generate an animated SVG: a crocodile riding a bicycle."""
import math, os, random, sys

random.seed(11)

# ------------------------------------------------------------------ helpers
def n(x):
    s = f"{x:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s

def P(x, y):
    return f"{n(x)},{n(y)}"

def g(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")

def A_tr(values, dur, typ="translate", begin=None):
    b = f' begin="{begin}"' if begin is not None else ""
    return (f'<animateTransform attributeName="transform" type="{typ}" '
            f'values="{";".join(values)}" dur="{g(dur)}s" repeatCount="indefinite"{b}/>')

def A_rot(a0, a1, cx, cy, dur, begin=None):
    b = f' begin="{begin}"' if begin is not None else ""
    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{n(a0)} {n(cx)} {n(cy)}" to="{n(a1)} {n(cx)} {n(cy)}" '
            f'dur="{g(dur)}s" repeatCount="indefinite"{b}/>')

def A_d(ds, dur):
    return f'<animate attributeName="d" values="{";".join(ds)}" dur="{g(dur)}s" repeatCount="indefinite"/>'

def U(i, extra=""):
    return f'<use href="#{i}" xlink:href="#{i}" {extra}/>'

def cr_segments(points, closed):
    nn = len(points)
    segs = []
    rng = nn if closed else nn - 1
    for i in range(rng):
        p0 = points[(i - 1) % nn] if (closed or i > 0) else points[i]
        p1 = points[i]
        p2 = points[(i + 1) % nn]
        p3 = points[(i + 2) % nn] if (closed or i + 2 < nn) else points[(i + 1) % nn]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs

def cr_path(points, closed=False):
    segs = cr_segments(points, closed)
    d = "M" + P(*segs[0][0])
    for (_, c1, c2, p2) in segs:
        d += f"C{P(*c1)} {P(*c2)} {P(*p2)}"
    return d + ("Z" if closed else "")

def cr_sample(points, closed, per=12):
    out = []
    for (p1, c1, c2, p2) in cr_segments(points, closed):
        for k in range(per):
            t = k / per
            m = 1 - t
            out.append((m**3 * p1[0] + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t**3 * p2[0],
                        m**3 * p1[1] + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t**3 * p2[1]))
    if not closed:
        out.append(points[-1])
    return out

def poly(pts, close=True):
    return "M" + "L".join(P(*p) for p in pts) + ("Z" if close else "")

def ik(h, a, l1, l2, bend):
    dx, dy = a[0] - h[0], a[1] - h[1]
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    aa = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    hh = math.sqrt(max(l1 * l1 - aa * aa, 0))
    return (h[0] + aa * ux + bend * hh * uy, h[1] + aa * uy - bend * hh * ux)


def hl_seg(a, b, off, inset=0.2):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dy)
    nx, ny = dy / l, -dx / l
    a2 = (a[0] + dx * inset + nx * off, a[1] + dy * inset + ny * off)
    b2 = (b[0] - dx * inset + nx * off, b[1] - dy * inset + ny * off)
    return f"M{P(*a2)}L{P(*b2)}"

# ------------------------------------------------------------------ constants
W, H = 1200, 720
T = 1.6                     # crank period (s)
NF = 40                     # keyframes per crank cycle
TW = T / 2                  # wheel period (gear ratio 2:1)
R_TIRE = 102.0
V = 2 * math.pi * R_TIRE / TW   # ground speed px/s
FR = [k * T / NF for k in range(NF + 1)]

RW = (420, 500); FW = (800, 500); BB = (580, 522); CL = 56
THETA0 = 25.0
BIKE_DX = 40

C_OUT = "#1E5A39"      # croc outline
C_DARK = "#2A7048"
C_FAR = "#3E8F57"
SHOE_W = "#F7F4EA"

def theta(t): return THETA0 + 360.0 * t / T
def pedal_pos(th):
    r = math.radians(th)
    return (BB[0] + CL * math.cos(r), BB[1] + CL * math.sin(r))
def foot_ang(th): return 9.0 * math.sin(math.radians(th) + 0.5)
def bob(t): return 2.4 * math.sin(2 * math.pi * 2 * t / T - 1.2)
def bounce(t): return 1.0 * math.sin(2 * math.pi * 2 * t / T + 0.4)
def nod(t): return 1.8 * math.sin(2 * math.pi * 2 * t / T + 0.2)

H0 = (548, 314); FH0 = (538, 311)
S0 = (660, 262); FS0 = (646, 257)
GRIP = (790, 314); FGRIP = (782, 309)
L1, L2 = 128, 118
A1, A2 = 82, 80
ANK = (-14, -29)

# ------------------------------------------------------------------ defs
defs = []
defs.append('''
<linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#58B4E9"/><stop offset=".45" stop-color="#9ED8F2"/>
  <stop offset=".8" stop-color="#FCEBCB"/><stop offset="1" stop-color="#FFE2B5"/></linearGradient>
<radialGradient id="gSun"><stop offset="0" stop-color="#FFF8D6" stop-opacity="1"/>
  <stop offset=".3" stop-color="#FFE9A3" stop-opacity=".8"/><stop offset="1" stop-color="#FFD98A" stop-opacity="0"/></radialGradient>
<linearGradient id="gMtn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#A9CBE0"/><stop offset="1" stop-color="#D5E6EC"/></linearGradient>
<linearGradient id="gHill1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#93CDB9"/><stop offset="1" stop-color="#C5E4CF"/></linearGradient>
<linearGradient id="gHill2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6FBB9A"/><stop offset="1" stop-color="#A8D9B4"/></linearGradient>
<linearGradient id="gWater" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C9EDEF"/><stop offset="1" stop-color="#7CCBD2"/></linearGradient>
<linearGradient id="gRoad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F0D9AE"/><stop offset="1" stop-color="#D8B57C"/></linearGradient>
<linearGradient id="gBank" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9AD487"/><stop offset="1" stop-color="#6FB968"/></linearGradient>
<linearGradient id="gBody" gradientUnits="userSpaceOnUse" x1="0" y1="190" x2="0" y2="380">
  <stop offset="0" stop-color="#3B9A5A"/><stop offset=".6" stop-color="#5DB66E"/><stop offset="1" stop-color="#7ECB84"/></linearGradient>
<linearGradient id="gTail" gradientUnits="userSpaceOnUse" x1="0" y1="260" x2="0" y2="400">
  <stop offset="0" stop-color="#389657"/><stop offset="1" stop-color="#72C57D"/></linearGradient>
<linearGradient id="gHead" gradientUnits="userSpaceOnUse" x1="0" y1="-60" x2="0" y2="40">
  <stop offset="0" stop-color="#3C9C5B"/><stop offset=".7" stop-color="#5FB86F"/><stop offset="1" stop-color="#7CCA84"/></linearGradient>
<linearGradient id="gJaw" gradientUnits="userSpaceOnUse" x1="0" y1="10" x2="0" y2="46">
  <stop offset="0" stop-color="#7BC884"/><stop offset="1" stop-color="#EDE9A9"/></linearGradient>
<linearGradient id="gBelly" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F6F0BC"/><stop offset="1" stop-color="#E4DE9C"/></linearGradient>
<linearGradient id="gFrame" gradientUnits="userSpaceOnUse" x1="0" y1="360" x2="0" y2="530">
  <stop offset="0" stop-color="#F0605D"/><stop offset="1" stop-color="#D9414A"/></linearGradient>
<linearGradient id="gHelmet" gradientUnits="userSpaceOnUse" x1="0" y1="-88" x2="0" y2="10"><stop offset="0" stop-color="#FFB84A"/><stop offset="1" stop-color="#FF8A00"/></linearGradient>
<linearGradient id="gScarf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFE066"/><stop offset="1" stop-color="#FFC12E"/></linearGradient>
<radialGradient id="gVig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#2a1a05" stop-opacity=".22"/></radialGradient>
<linearGradient id="gFade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="fBlur" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="fBlur2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>
<pattern id="pScales" width="16" height="12" patternUnits="userSpaceOnUse">
  <path d="M0 6Q4 0 8 6Q12 0 16 6M-8 12Q-4 6 0 12Q4 6 8 12Q12 6 16 12Q20 6 24 12" fill="none" stroke="#1E5A39" stroke-width="1" opacity=".26"/></pattern>
<pattern id="pWeave" width="10" height="10" patternUnits="userSpaceOnUse">
  <path d="M0 0L10 10M10 0L0 10" stroke="#9A6A2E" stroke-width="1.6" opacity=".55"/><path d="M5 0V10" stroke="#F0C27A" stroke-width="1" opacity=".5"/></pattern>
''')

# ------------------------------------------------------------------ sky
def cloud(sc=1.0, op=1.0):
    return (f'<g transform="scale({sc})" opacity="{op}"><ellipse cx="2" cy="16" rx="92" ry="17" fill="#fff"/>'
            '<circle cx="-46" cy="2" r="25" fill="#fff"/><circle cx="-10" cy="-14" r="33" fill="#fff"/>'
            '<circle cx="32" cy="-5" r="27" fill="#fff"/><circle cx="64" cy="7" r="19" fill="#fff"/>'
            '<ellipse cx="4" cy="26" rx="74" ry="7" fill="#D4E8F5" opacity=".75"/></g>')

def moving_cloud(y, sc, speed, begin, op=1.0):
    dur = 1800 / speed
    return (f'<g transform="translate(0,{y})"><g>'
            f'<animateTransform attributeName="transform" type="translate" from="1400 0" to="-400 0" '
            f'dur="{g(dur)}s" begin="{begin}s" repeatCount="indefinite"/>{cloud(sc, op)}</g></g>')

def bird(x, y, sc, phase, speed):
    d1 = "M-14,0Q-7,-10 0,0Q7,-10 14,0"
    d2 = "M-14,-7Q-7,3 0,0Q7,3 14,-7"
    dur = 1500 / speed
    return (f'<g transform="translate(0,{y}) scale({sc})"><g>'
            f'<animateTransform attributeName="transform" type="translate" from="-120 0" to="1380 0" dur="{g(dur)}s" begin="{phase}s" repeatCount="indefinite"/>'
            f'<path d="{d1}" fill="none" stroke="#3E4C5E" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
            f'<animate attributeName="d" values="{d1};{d2};{d1}" dur="0.55s" repeatCount="indefinite"/></path></g></g>')

sky = []
sky.append('<rect width="1200" height="720" fill="url(#gSky)"/>')
# sun + slowly rotating rays
sun = ['<g transform="translate(930,168)">',
       '<circle r="190" fill="url(#gSun)"><animate attributeName="r" values="180;200;180" dur="6s" repeatCount="indefinite"/></circle>',
       '<g opacity=".17">' + A_rot(0, 360, 0, 0, 90)]
for i in range(14):
    a = i * 360 / 14
    sun.append(f'<path d="M0,0L-16,-175L16,-175Z" fill="#FFF2B0" transform="rotate({n(a)})"/>')
sun.append('</g><circle r="46" fill="#FFF4B8"/><circle r="38" fill="#FFFBDD" opacity=".85"/></g>')
sky.append("".join(sun))
sky.append(moving_cloud(96, 1.0, 22, -30))
sky.append(moving_cloud(176, 0.7, 14, -60, .9))
sky.append(moving_cloud(60, 0.55, 10, -110, .85))
sky.append(moving_cloud(258, 0.62, 17, -20, .8))
sky.append(bird(0, 118, 1.0, -9, 38) + bird(0, 146, 0.8, -13, 38) + bird(0, 100, 0.7, -5, 42))

# ------------------------------------------------------------------ parallax tiles
def ridge(base, comps, step=12, bottom=560):
    pts = []
    for x in range(0, 1201, step):
        y = base - sum(a * math.sin(2 * math.pi * k * x / 1200 + ph) for a, k, ph in comps)
        pts.append((x, y))
    d = f"M0,{n(bottom)}L" + "L".join(P(*p) for p in pts) + f"L1200,{n(bottom)}Z"
    return d, pts

def ridge_y(base, comps, x):
    return base - sum(a * math.sin(2 * math.pi * k * x / 1200 + ph) for a, k, ph in comps)

MTN = [(46, 1, 0.5), (30, 2, 1.9), (18, 3, 0.2), (11, 5, 2.5), (6, 8, 1.1)]
MTN2 = [(34, 1, 2.4), (22, 2, 0.4), (14, 4, 1.2), (7, 7, 0.3)]
HILL1 = [(22, 1, 2.0), (14, 2, 0.7), (9, 4, 1.3), (4, 9, 0.5)]
HILL2 = [(16, 1, 0.9), (10, 3, 2.2), (6, 5, 0.1)]

def tile_mountains():
    d1, _ = ridge(432, MTN, 10, 540)
    d2, _ = ridge(462, MTN2, 10, 540)
    return (f'<g id="tMtn"><path d="{d1}" fill="url(#gMtn)" opacity=".85"/>'
            f'<path d="{d2}" fill="#B6D6E2" opacity=".9"/></g>')

def lolli(x, y, s, col):
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})"><rect x="-1.5" y="-4" width="3" height="10" fill="#6E8E6A"/>'
            f'<circle cx="0" cy="-12" r="10" fill="{col}"/><circle cx="-3" cy="-15" r="4" fill="#fff" opacity=".12"/></g>')

def tile_hills():
    d1, _ = ridge(482, HILL1, 10, 540)
    d2, _ = ridge(500, HILL2, 10, 540)
    trees = []
    for i in range(14):
        x = 40 + i * 83 + random.uniform(-18, 18)
        y = ridge_y(482, HILL1, x) + 4
        trees.append(lolli(x, y, random.uniform(.7, 1.1), random.choice(["#74B79B", "#82C2A3", "#6CAE95"])))
    trees2 = []
    for i in range(10):
        x = 60 + i * 118 + random.uniform(-25, 25)
        y = ridge_y(500, HILL2, x) + 6
        trees2.append(lolli(x, y, random.uniform(.9, 1.3), random.choice(["#5DAA82", "#69B58B", "#55A07D"])))
    return (f'<g id="tHill"><path d="{d1}" fill="url(#gHill1)"/>{"".join(trees)}'
            f'<path d="{d2}" fill="url(#gHill2)"/>{"".join(trees2)}</g>')

def tile_water():
    out = ['<g id="tWater">']
    for i in range(34):
        x = random.uniform(20, 1130)
        y = random.uniform(512, 548)
        w = random.uniform(24, 70) * (0.6 + (y - 505) / 70)
        op = random.uniform(.35, .8)
        dur = random.uniform(1.6, 3.2)
        out.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="2.2" rx="1.1" fill="#fff" opacity="{n(op) if False else round(op,2)}">'
                   f'<animate attributeName="opacity" values="{round(op,2)};{round(op*.25,2)};{round(op,2)}" dur="{g(dur)}s" repeatCount="indefinite"/></rect>')
    out.append('</g>')
    return "".join(out)

def palm_symbol():
    fronds = []
    ang = [-168, -140, -112, -84, -52, -22, 10, 36]
    for i, a in enumerate(ang):
        s = 1.0 if i % 2 == 0 else 0.86
        flip = -1 if a < -90 else 1
        aa = a if flip == 1 else (-180 - a)
        leaf = ('M0,0C28,-34 78,-34 118,14C84,-8 40,-6 0,2Z')
        rib = 'M0,0C34,-22 80,-24 118,14'
        fronds.append(f'<g transform="scale({flip*s},{s}) rotate({aa})">'
                      f'<path d="{leaf}" fill="#4DA583"/><path d="{rib}" fill="none" stroke="#2F7D63" stroke-width="2" stroke-linecap="round"/></g>')
    sway = A_rot(-2.2, 2.2, 0, 0, 3.4)
    sway_vals = ""
    trunk = ('<path d="M-9,0C-4,-70 14,-128 30,-186L38,-184C23,-126 9,-70 9,0Z" fill="#A98463"/>'
             '<path d="M-9,0C-4,-70 14,-128 30,-186L33,-185C16,-128 0,-70 -3,0Z" fill="#8E6B4C" opacity=".6"/>')
    rings = "".join(f'<path d="M{n(-8+ i*0.1)},{-i*16}l16,-3" stroke="#6F5239" stroke-width="1.2" opacity=".5"/>' for i in range(1, 11))
    return (f'<g id="palm">{trunk}{rings}<g transform="translate(34,-186)"><g>'
            f'<animateTransform attributeName="transform" type="rotate" values="-2.5;2.5;-2.5" dur="3.6s" repeatCount="indefinite"/>'
            f'{"".join(fronds)}<circle r="6" fill="#7E5A3C"/></g></g></g>')

def bush(x, y, s, c1, c2):
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})"><circle cx="-18" cy="-6" r="16" fill="{c2}"/>'
            f'<circle cx="16" cy="-5" r="17" fill="{c2}"/><circle cx="0" cy="-16" r="21" fill="{c1}"/>'
            f'<circle cx="-6" cy="-22" r="7" fill="#fff" opacity=".13"/></g>')

def reed(x, y, h):
    sway = f'<animateTransform attributeName="transform" type="rotate" values="-3 {n(x)} {n(y)};3 {n(x)} {n(y)};-3 {n(x)} {n(y)}" dur="{g(random.uniform(2.2,3.4))}s" repeatCount="indefinite"/>'
    return (f'<g>{sway}<path d="M{n(x)},{n(y)}Q{n(x+3)},{n(y-h*.5)} {n(x+1)},{n(y-h)}" stroke="#4E9C55" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
            f'<rect x="{n(x-2.6)}" y="{n(y-h-4)}" width="6" height="22" rx="3" fill="#8A5A33"/></g>')

def tile_palms():
    out = ['<g id="tPalms">']
    xs = [110, 430, 790, 1040]
    for x, s in zip(xs, [1.0, 0.82, 1.1, 0.9]):
        out.append(f'<use href="#palm" xlink:href="#palm" transform="translate({x},560) scale({s})" opacity=".92"/>')
    for i in range(10):
        x = 40 + i * 120 + random.uniform(-25, 25)
        out.append(bush(x, 562, random.uniform(.8, 1.2), "#6DBE7B", "#58AA68"))
    out.append('</g>')
    return "".join(out)

def tile_bank():
    out = ['<g id="tBank">']
    for i in range(12):
        x = 30 + i * 98 + random.uniform(-20, 20)
        out.append(bush(x, 590, random.uniform(.75, 1.05), "#7FCB7E", "#66B868"))
    for i in range(9):
        x = random.uniform(40, 1150)
        out.append(reed(x, 584, random.uniform(34, 56)))
    for i in range(26):
        x = random.uniform(20, 1180)
        y = random.uniform(574, 596)
        col = random.choice(["#FFFFFF", "#FFD6E0", "#FFE88A"])
        out.append(f'<circle cx="{n(x)}" cy="{n(y)}" r="2.4" fill="{col}"/>')
    out.append('</g>')
    return "".join(out)

def tile_road_far():
    out = ['<g id="tRoadFar">']
    for i in range(46):
        x = random.uniform(15, 1185); y = random.uniform(592, 650)
        rx = random.uniform(2, 6); ry = rx * .55
        col = random.choice(["#C9A56E", "#E9CF9E", "#BF9A62", "#F8E8C4"])
        out.append(f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(rx)}" ry="{n(ry)}" fill="{col}" opacity=".7"/>')
    out.append('</g>')
    return "".join(out)

def tile_road_near():
    out = ['<g id="tRoadNear">']
    for i in range(40):
        x = random.uniform(15, 1185); y = random.uniform(650, 716)
        rx = random.uniform(3, 9); ry = rx * .5
        col = random.choice(["#C9A56E", "#E9CF9E", "#BF9A62", "#F8E8C4"])
        out.append(f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(rx)}" ry="{n(ry)}" fill="{col}" opacity=".75"/>')
    for i in range(8):
        x = i * 150 + 30
        out.append(f'<rect x="{x}" y="676" width="74" height="7" rx="3.5" fill="#FFF6DC" opacity=".8"/>')
    out.append('</g>')
    return "".join(out)

def tile_fore():
    out = ['<g id="tFore">']
    for i in range(34):
        x = 10 + i * 35 + random.uniform(-8, 8)
        h = random.uniform(22, 44)
        col = random.choice(["#3E9A52", "#2F8447", "#4BAA5E"])
        out.append(f'<path d="M{n(x-9)},724Q{n(x-3)},{n(724-h*.6)} {n(x-4)},{n(724-h)}Q{n(x+3)},{n(724-h*.5)} {n(x+9)},724Z" fill="{col}"/>')
    for i in range(10):
        x = random.uniform(30, 1170); y = random.uniform(696, 712)
        col = random.choice(["#FF7A93", "#FFFFFF", "#FFD23F", "#FF9F5A"])
        out.append(f'<g transform="translate({n(x)},{n(y)})"><path d="M0,10V22" stroke="#2F8447" stroke-width="2.2"/>'
                   + "".join(f'<circle cx="{n(5*math.cos(a))}" cy="{n(5*math.sin(a))}" r="3.6" fill="{col}"/>' for a in [i2 * math.pi * 2 / 5 for i2 in range(5)])
                   + '<circle r="2.6" fill="#FFF3A0"/></g>')
    out.append('</g>')
    return "".join(out)

defs.append(tile_mountains()); defs.append(tile_hills()); defs.append(tile_water())
defs.append(palm_symbol()); defs.append(tile_palms()); defs.append(tile_bank())
defs.append(tile_road_far()); defs.append(tile_road_near()); defs.append(tile_fore())

def scroll(tid, speed):
    dur = 1200.0 / speed
    return (f'<g><animateTransform attributeName="transform" type="translate" from="0 0" to="-1200 0" dur="{g(dur)}s" repeatCount="indefinite"/>'
            f'{U(tid)}{U(tid, "x=\"1200\"")}</g>')

scene = []
scene.append("".join(sky))
scene.append(scroll("tMtn", 12))
scene.append(scroll("tHill", 34))
scene.append('<rect x="0" y="507" width="1200" height="60" fill="url(#gWater)"/>')
scene.append(scroll("tWater", 70))
scene.append(scroll("tPalms", 150))
scene.append('<rect x="0" y="580" width="1200" height="140" fill="url(#gBank)"/>')
scene.append(scroll("tBank", 260))
# road
scene.append('<rect x="0" y="592" width="1200" height="140" fill="url(#gRoad)"/>')
scene.append('<rect x="0" y="592" width="1200" height="6" fill="#FFF1CC" opacity=".9"/>')
scene.append('<rect x="0" y="598" width="1200" height="3" fill="#B98F55" opacity=".25"/>')
scene.append(scroll("tRoadFar", V))
scene.append(scroll("tRoadNear", V * 1.35))

# ------------------------------------------------------------------ speed lines + shadow + dust
fx_back = []
for i, (y, w, sp, bg) in enumerate([(210, 150, 1500, 0), (300, 110, 1900, -.3), (390, 170, 1600, -.7), (470, 120, 2100, -.2), (140, 130, 1700, -.5), (350, 90, 2300, -.9)]):
    dur = 1500 / sp * 1.0 + 0.0
    fx_back.append(f'<g opacity=".5"><rect x="0" y="{y}" width="{w}" height="3" rx="1.5" fill="url(#gFade)">'
                   f'<animateTransform attributeName="transform" type="translate" from="1300 0" to="-300 0" dur="{g(1600/sp)}s" begin="{bg}s" repeatCount="indefinite"/></rect></g>')

shadow = (f'<g transform="translate({BIKE_DX},0)">'
          f'<ellipse cx="610" cy="606" rx="300" ry="9" fill="#5A3A12" opacity=".22" filter="url(#fBlur)"/>'
          f'<ellipse cx="420" cy="604" rx="86" ry="8" fill="#3E2807" opacity=".28" filter="url(#fBlur)"/>'
          f'<ellipse cx="800" cy="604" rx="86" ry="8" fill="#3E2807" opacity=".28" filter="url(#fBlur)"/></g>')

dust = []
for i in range(5):
    b = -i * 0.3
    dust.append(f'<g transform="translate({BIKE_DX + 412},596)"><g>'
                f'<animateTransform attributeName="transform" type="translate" from="0 0" to="-120 -26" dur="1.5s" begin="{g(b)}s" repeatCount="indefinite"/>'
                f'<circle r="9" fill="#F3E1BC"><animate attributeName="r" values="4;22" dur="1.5s" begin="{g(b)}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values=".7;0" dur="1.5s" begin="{g(b)}s" repeatCount="indefinite"/></circle></g></g>')

# ------------------------------------------------------------------ BIKE
def wheel(c):
    cx, cy = c
    s = []
    s.append(f'<circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="#2A2C36" stroke-width="12"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="89.5" fill="none" stroke="#F4E8CB" stroke-width="3"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="86" fill="none" stroke="#CDD3DA" stroke-width="4.5"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="83.3" fill="none" stroke="#8D97A3" stroke-width="1"/>')
    rot = ['<g>' + A_rot(0, 360, cx, cy, TW)]
    rot.append(f'<circle cx="{cx}" cy="{cy}" r="101.4" fill="none" stroke="#4B4F5E" stroke-width="2.4" stroke-dasharray="6 4.2"/>')
    spokes = []
    for i in range(12):
        a = math.radians(i * 30)
        x0, y0 = cx + 11 * math.cos(a), cy + 11 * math.sin(a)
        b = a + 0.34
        spokes.append(f'M{P(x0,y0)}L{P(cx+83*math.cos(b), cy+83*math.sin(b))}')
        a2 = math.radians(i * 30 + 15)
        x0, y0 = cx + 11 * math.cos(a2), cy + 11 * math.sin(a2)
        b2 = a2 - 0.34
        spokes.append(f'M{P(x0,y0)}L{P(cx+83*math.cos(b2), cy+83*math.sin(b2))}')
    rot.append(f'<path d="{"".join(spokes)}" stroke="#B9C1CA" stroke-width="1.15" fill="none"/>')
    for i in range(4):
        a = math.radians(i * 90 + 20)
        rx, ry = cx + 56 * math.cos(a), cy + 56 * math.sin(a)
        rot.append(f'<circle cx="{n(rx)}" cy="{n(ry)}" r="3.8" fill="#FF9F1C" stroke="#B35F00" stroke-width="1"/>'
                   f'<circle cx="{n(rx-1)}" cy="{n(ry-1)}" r="1.2" fill="#fff" opacity=".8"/>')
    rot.append('</g>')
    s.append("".join(rot))
    # static gloss on tire
    s.append(f'<path d="M{P(cx+99*math.cos(math.radians(-150)), cy+99*math.sin(math.radians(-150)))}A99,99 0 0 1 {P(cx+99*math.cos(math.radians(-108)), cy+99*math.sin(math.radians(-108)))}" stroke="#fff" stroke-opacity=".22" stroke-width="3.5" fill="none" stroke-linecap="round"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="12" fill="#E1E5EA" stroke="#8D97A3" stroke-width="2.4"/><circle cx="{cx}" cy="{cy}" r="5" fill="#6B7480"/>')
    return "".join(s)

def arc(c, r, a0, a1):
    x0, y0 = c[0] + r * math.cos(math.radians(a0)), c[1] + r * math.sin(math.radians(a0))
    x1, y1 = c[0] + r * math.cos(math.radians(a1)), c[1] + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{P(x0,y0)}A{r},{r} 0 {large} 1 {P(x1,y1)}"

bike = []

# --- far crank + far leg (behind everything)
def leg_data(far):
    out = []
    for t in FR:
        th = theta(t) + (180 if far else 0)
        p = pedal_pos(th)
        a = foot_ang(th)
        ar = math.radians(a)
        ax = p[0] + ANK[0] * math.cos(ar) - ANK[1] * math.sin(ar)
        ay = p[1] + ANK[0] * math.sin(ar) + ANK[1] * math.cos(ar)
        hip0 = FH0 if far else H0
        hip = (hip0[0], hip0[1] + bob(t))
        knee = ik(hip, (ax, ay), L1, L2, +1)
        out.append((hip, knee, (ax, ay), p, a))
    return out

LEG_N = leg_data(False)
LEG_F = leg_data(True)

def leg_svg(data, far):
    thigh = [f"M{P(*h)}L{P(*k)}" for (h, k, a, p, an) in data]
    shin = [f"M{P(*k)}L{P(*a)}" for (h, k, a, p, an) in data]
    full = [f"M{P(*h)}L{P(*k)}L{P(*a)}" for (h, k, a, p, an) in data]
    fill = C_FAR if far else "#5AB46C"
    fill2 = "#418F57" if far else "#4EA862"
    s = []
    s.append(f'<path fill="none" stroke="{C_OUT}" stroke-width="45" stroke-linecap="round">{A_d(thigh, T)}</path>')
    s.append(f'<path fill="none" stroke="{C_OUT}" stroke-width="33" stroke-linecap="round">{A_d(shin, T)}</path>')
    s.append(f'<path fill="none" stroke="{fill}" stroke-width="39" stroke-linecap="round">{A_d(thigh, T)}</path>')
    s.append(f'<path fill="none" stroke="{fill2}" stroke-width="27" stroke-linecap="round">{A_d(shin, T)}</path>')
    h1 = [hl_seg(h, k, 9.5) for (h, k, a, p, an) in data]
    h2 = [hl_seg(k, a, 6.0, 0.25) for (h, k, a, p, an) in data]
    op = ".12" if far else ".26"
    s.append(f'<path fill="none" stroke="#fff" stroke-opacity="{op}" stroke-width="4" stroke-linecap="round">{A_d(h1, T)}</path>')
    s.append(f'<path fill="none" stroke="#fff" stroke-opacity="{op}" stroke-width="3.4" stroke-linecap="round">{A_d(h2, T)}</path>')
    s.append(f'<path fill="none" stroke="{C_OUT}" stroke-opacity=".3" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 11">{A_d(full, T)}</path>')
    return "".join(s)

def shoe_art(far):
    up = "#D9D6C8" if far else SHOE_W
    acc = "#D98100" if far else "#FF9F1C"
    sole = "#52566A" if far else "#2B2D38"
    return ('<g transform="scale(.92)">'
            '<path d="M-24,12H26V18H-24Z" fill="#454A58" stroke="#23262F" stroke-width="2" stroke-linejoin="round"/>'
            '<circle r="5" cy="15" fill="#9099A5" stroke="#23262F" stroke-width="1.6"/>'
            f'<path d="M-35,6C-38,-12 -37,-32 -30,-40L2,-40C4,-32 8,-27 18,-24C32,-21 46,-15 50,-3C52,4 48,9 40,10L-28,10C-33,10 -35,9 -35,6Z" fill="{up}" stroke="#23262F" stroke-width="2.8" stroke-linejoin="round"/>'
            f'<path d="M-36,2H49C52,4 50,8 46,10L-28,10C-33,10 -36,8 -36,2Z" fill="{sole}"/>'
            f'<path d="M-35,6H50" stroke="#fff" stroke-width="1.6" opacity=".55"/>'
            f'<path d="M30,-17C40,-13 46,-8 48,-1" stroke="{acc}" stroke-width="5.4" fill="none" stroke-linecap="round"/>'
            f'<path d="M-34,-8C-18,-16 8,-17 34,-4" stroke="{acc}" stroke-width="3.4" fill="none" stroke-linecap="round"/>'
            '<path d="M2,-32L12,-26M5,-25L16,-19M10,-19L21,-14" stroke="#8B8E99" stroke-width="2.2" stroke-linecap="round"/>'
            '<path d="M-30,-30C-29,-22 -28,-14 -29,-6" stroke="#fff" stroke-opacity=".75" stroke-width="2.4" fill="none" stroke-linecap="round"/></g>')

def shoe_group(data, far):
    tr = [f"{n(p[0])},{n(p[1])}" for (h, k, a, p, an) in data]
    ro = [n(an) for (h, k, a, p, an) in data]
    return f'<g>{A_tr(tr, T)}<g>{A_tr(ro, T, "rotate")}{shoe_art(far)}</g></g>'

def crank_arm(th0, color, outline):
    return (f'<g>{A_rot(th0, th0 + 360, BB[0], BB[1], T)}'
            f'<path d="M{P(*BB)}L{P(BB[0]+CL, BB[1])}" stroke="{outline}" stroke-width="15" stroke-linecap="round"/>'
            f'<path d="M{P(*BB)}L{P(BB[0]+CL, BB[1])}" stroke="{color}" stroke-width="10.5" stroke-linecap="round"/>'
            f'<path d="M{P(BB[0]+6, BB[1]-2.6)}L{P(BB[0]+CL, BB[1]-2.6)}" stroke="#fff" stroke-opacity=".5" stroke-width="2" stroke-linecap="round"/></g>')

bike.append(crank_arm(THETA0 + 180, "#8E97A3", "#4B525C"))
bike.append(leg_svg(LEG_F, True))
bike.append(shoe_group(LEG_F, True))

# --- wheels
bike.append(wheel(RW)); bike.append(wheel(FW))
# fenders
for c, a0, a1 in [(RW, -168, -24), (FW, -152, -14)]:
    bike.append(f'<path d="{arc(c, 108, a0, a1)}" fill="none" stroke="#9C2432" stroke-width="8.5" stroke-linecap="round"/>')
    bike.append(f'<path d="{arc(c, 108, a0, a1)}" fill="none" stroke="#F0605D" stroke-width="5.2" stroke-linecap="round"/>')
    bike.append(f'<path d="{arc(c, 107, a0+10, a1-30)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.6" stroke-linecap="round"/>')
# rear reflector
rr = (RW[0] + 108 * math.cos(math.radians(-168)), RW[1] + 108 * math.sin(math.radians(-168)))
bike.append(f'<rect x="{n(rr[0]-7)}" y="{n(rr[1]-4)}" width="9" height="11" rx="3" fill="#FF3B4E" stroke="#8A1020" stroke-width="1.6"/>')

# --- frame
ST_TOP = (538, 368)
SEAT_TOP = (527, 330)
TT_A, TT_B = (542, 382), (752, 372)
DT_B = (761, 396)
HT_T, HT_B = (749, 363), (765, 405)
SS_A = (541, 378)
tubes = [
    ([BB, ST_TOP], 10), ([TT_A, TT_B], 9), ([BB, DT_B], 11), ([HT_T, HT_B], 12),
    ([BB, RW], 7), ([SS_A, RW], 6),
]
fork_d = f"M{P(*HT_B)}Q786,442 {P(*FW)}"
bike.append(f'<path d="{fork_d}" fill="none" stroke="#9C2432" stroke-width="11" stroke-linecap="round"/>')
for pts, w in tubes:
    bike.append(f'<path d="{poly(pts, False)}" fill="none" stroke="#9C2432" stroke-width="{w+3.4}" stroke-linecap="round" stroke-linejoin="round"/>')
bike.append(f'<path d="{fork_d}" fill="none" stroke="#E6554F" stroke-width="7.6" stroke-linecap="round"/>')
for pts, w in tubes:
    bike.append(f'<path d="{poly(pts, False)}" fill="none" stroke="url(#gFrame)" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
for pts, w in tubes:
    a, b = pts
    bike.append(f'<path d="M{P(a[0], a[1]-w*.22)}L{P(b[0], b[1]-w*.22)}" stroke="#FFB3A6" stroke-opacity=".7" stroke-width="{max(1.6, w*.17)}" fill="none" stroke-linecap="round"/>')
# head tube cups
for p, dx in [(HT_T, 0), (HT_B, 0)]:
    bike.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="7.5" fill="#CDD3DA" stroke="#6A7480" stroke-width="2"/>')
# seat post + saddle
bike.append(f'<path d="M{P(*ST_TOP)}L{P(*SEAT_TOP)}" stroke="#4B525C" stroke-width="9" stroke-linecap="round"/>')
bike.append(f'<path d="M{P(*ST_TOP)}L{P(*SEAT_TOP)}" stroke="#C9CFD6" stroke-width="6" stroke-linecap="round"/>')
bike.append('<path d="M492,331C500,322 536,322 568,327C582,330 580,341 563,342L506,343C494,343 486,337 492,331Z" fill="#7A4B2A" stroke="#3E2413" stroke-width="2.6" stroke-linejoin="round"/>'
            '<path d="M498,330C516,325 546,325 566,329" stroke="#C48A55" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".8"/>')
# bottle on down tube
bike.append('<g transform="translate(650,462) rotate(14)"><rect x="-10" y="-30" width="20" height="46" rx="8" fill="#4DB6E8" stroke="#1F6C93" stroke-width="2.2"/>'
            '<rect x="-6" y="-38" width="12" height="9" rx="3" fill="#F5F7FA" stroke="#1F6C93" stroke-width="2"/>'
            '<rect x="-10" y="-8" width="20" height="9" fill="#fff" opacity=".85"/><path d="M-5,-24V-6" stroke="#fff" stroke-opacity=".6" stroke-width="2.4" stroke-linecap="round"/></g>')
# axle dropouts
for c in (RW, FW):
    bike.append(f'<circle cx="{c[0]}" cy="{c[1]}" r="7.5" fill="#C9CFD6" stroke="#6A7480" stroke-width="2.2"/>')
# BB shell
bike.append(f'<circle cx="{BB[0]}" cy="{BB[1]}" r="12" fill="#B9C0C8" stroke="#6A7480" stroke-width="2.4"/>')

# --- chain
r1, r2 = 36.0, 18.0
dvec = (RW[0] - BB[0], RW[1] - BB[1])
Ld = math.hypot(*dvec)
ux, uy = dvec[0] / Ld, dvec[1] / Ld
k = (r1 - r2) / Ld
perp = (-uy, ux)  # (.. , ..) points up-ish (y<0) for this orientation?
if perp[1] > 0:
    perp = (-perp[0], -perp[1])
s_ = math.sqrt(1 - k * k)
n_top = (k * ux + s_ * perp[0], k * uy + s_ * perp[1])
n_bot = (k * ux - s_ * perp[0], k * uy - s_ * perp[1])
P1a = (BB[0] + r1 * n_top[0], BB[1] + r1 * n_top[1]); P2a = (RW[0] + r2 * n_top[0], RW[1] + r2 * n_top[1])
P1b = (BB[0] + r1 * n_bot[0], BB[1] + r1 * n_bot[1]); P2b = (RW[0] + r2 * n_bot[0], RW[1] + r2 * n_bot[1])
chain_d = (f"M{P(*P2a)}L{P(*P1a)}A{r1},{r1} 0 1 1 {P(*P1b)}L{P(*P2b)}A{r2},{r2} 0 0 1 {P(*P2a)}Z")
pitch = 2 * math.pi * r1 / 22
bike.append(f'<path d="{chain_d}" fill="none" stroke="#2C2F38" stroke-width="5.6" stroke-linejoin="round"/>')
bike.append(f'<path d="{chain_d}" fill="none" stroke="#A7AFB9" stroke-width="3.4" stroke-dasharray="{g(pitch*0.5)} {g(pitch*0.5)}" stroke-linejoin="round">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="{g(-pitch*22)}" dur="{g(T)}s" repeatCount="indefinite"/></path>')

def toothed(cx, cy, ro, ri, nt, hole=None):
    pts = []
    for i in range(nt * 2):
        a = math.pi * 2 * i / (nt * 2)
        r = ro if i % 2 == 0 else ri
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = poly(pts)
    if hole:
        d += f"M{P(cx+hole, cy)}A{hole},{hole} 0 1 0 {P(cx-hole, cy)}A{hole},{hole} 0 1 0 {P(cx+hole, cy)}Z"
    return d

# sprocket (rotates with the rear wheel)
bike.append(f'<g>{A_rot(0, 360, RW[0], RW[1], TW)}<path d="{toothed(RW[0], RW[1], 20.5, 17, 11, 7)}" fill="#C4CBD3" stroke="#5E6874" stroke-width="1.8" fill-rule="evenodd" stroke-linejoin="round"/></g>')
# chainring + near crank arm
ring = [f'<g>{A_rot(THETA0, THETA0 + 360, BB[0], BB[1], T)}']
ring.append(f'<path d="{toothed(BB[0], BB[1], 38.5, 34.5, 22, 27)}" fill="#CCD3DA" stroke="#5E6874" stroke-width="2" fill-rule="evenodd" stroke-linejoin="round"/>')
for i in range(5):
    a = math.radians(i * 72 + 18)
    ring.append(f'<path d="M{P(*BB)}L{P(BB[0]+29*math.cos(a), BB[1]+29*math.sin(a))}" stroke="#5E6874" stroke-width="9" stroke-linecap="round"/>'
                f'<path d="M{P(*BB)}L{P(BB[0]+29*math.cos(a), BB[1]+29*math.sin(a))}" stroke="#D5DBE1" stroke-width="5.6" stroke-linecap="round"/>')
ring.append('</g>')
bike.append("".join(ring))
bike.append(crank_arm(THETA0, "#CBD2D9", "#5E6874"))
bike.append(f'<circle cx="{BB[0]}" cy="{BB[1]}" r="8" fill="#9099A5" stroke="#4B525C" stroke-width="2"/><circle cx="{BB[0]}" cy="{BB[1]}" r="3" fill="#5E6874"/>')

# --- stem + handlebar
bike.append(f'<path d="M{P(*HT_T)}L741,336" stroke="#4B525C" stroke-width="9.5" stroke-linecap="round"/><path d="M{P(*HT_T)}L741,336" stroke="#CDD3DA" stroke-width="6.2" stroke-linecap="round"/>')
BAR = "M741,336L757,326C773,318 786,318 797,308"
bike.append(f'<path d="{BAR}" fill="none" stroke="#4B525C" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{BAR}" fill="none" stroke="#CDD3DA" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>')
# brake lever + bell
bike.append('<path d="M772,320C768,330 758,336 750,338" stroke="#4B525C" stroke-width="3.4" fill="none" stroke-linecap="round"/>')
bike.append('<g transform="translate(762,318)"><path d="M-9,0A9,9 0 0 1 9,0Z" fill="#FFD23F" stroke="#B88400" stroke-width="2"/><rect x="-10" y="0" width="20" height="3" rx="1.5" fill="#B88400"/>'
            '<path d="M-5,-4A6,6 0 0 1 0,-7" stroke="#fff" stroke-opacity=".8" stroke-width="1.6" fill="none" stroke-linecap="round"/></g>')

# --- basket + fish
bike.append('<path d="M763,382L798,366" stroke="#6A7480" stroke-width="4" stroke-linecap="round"/>')
fish = ('<g transform="translate(826,342) rotate(104)">'
        '<g><animateTransform attributeName="transform" type="rotate" values="-16 -23 0;16 -23 0;-16 -23 0" dur="0.5s" repeatCount="indefinite"/>'
        '<path d="M-22,0L-46,-13C-40,-4 -40,4 -46,13Z" fill="#6FA9DB" stroke="#2D5E8C" stroke-width="2" stroke-linejoin="round"/></g>'
        '<path d="M-26,0C-14,-15 14,-15 28,0C14,15 -14,15 -26,0Z" fill="#8CC3EF" stroke="#2D5E8C" stroke-width="2.2"/>'
        '<path d="M-22,3C-6,12 14,11 26,2C14,9 -8,8 -22,3Z" fill="#E6F3FF"/>'
        '<path d="M-6,-12L2,-22L10,-12Z" fill="#6FA9DB" stroke="#2D5E8C" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M8,-8Q4,0 8,8" fill="none" stroke="#2D5E8C" stroke-width="1.8" stroke-linecap="round"/>'
        '<circle cx="18" cy="-3" r="3.4" fill="#fff" stroke="#23262F" stroke-width="1.4"/><circle cx="18.6" cy="-3" r="1.5" fill="#23262F"/>'
        '<path d="M-14,-4l4,3M-8,-6l4,3M-2,-7l4,3" stroke="#2D5E8C" stroke-width="1" opacity=".5"/></g>')
bike.append(fish)
bike.append('<path d="M788,347H866L856,384C855,388 852,390 848,390H806C802,390 799,388 798,384Z" fill="#E2B066" stroke="#7A4D1E" stroke-width="2.8" stroke-linejoin="round"/>'
            '<path d="M788,347H866L856,384C855,388 852,390 848,390H806C802,390 799,388 798,384Z" fill="url(#pWeave)"/>'
            '<rect x="783" y="341" width="88" height="11" rx="5.5" fill="#C98A3C" stroke="#7A4D1E" stroke-width="2.6"/>'
            '<path d="M790,346H864" stroke="#F4D49A" stroke-width="2" opacity=".8" stroke-linecap="round"/>')

# ------------------------------------------------------------------ CROC
# --- tail (animated outline)
ROOT = (490, 328)
TT_PER = 2 * T
NTAIL = 30
def tail_geom(t):
    N = 26; Ltail = 330.0; ds = Ltail / (N - 1)
    x, y = ROOT
    cs, ns, ts, ws = [], [], [], []
    for i in range(N):
        s = i / (N - 1)
        th = math.pi - 0.30 + 0.78 * s + 0.5 * (s ** 0.7) * math.sin(2 * math.pi * 1.15 * s - 2 * math.pi * t / TT_PER)
        w = 31 * (1 - s) ** 0.85 + 1.6
        cs.append((x, y)); ns.append((-math.sin(th), math.cos(th))); ts.append((math.cos(th), math.sin(th))); ws.append(w)
        x += ds * math.cos(th); y += ds * math.sin(th)
    return cs, ns, ts, ws

tail_base, tail_belly, tail_bands, tail_scutes = [], [], [], []
for k in range(NTAIL + 1):
    t = k * TT_PER / NTAIL
    cs, ns, ts, ws = tail_geom(t)
    N = len(cs)
    top = [(c[0] + w * nn[0], c[1] + w * nn[1]) for c, nn, w in zip(cs, ns, ws)]
    bot = [(c[0] - w * nn[0], c[1] - w * nn[1]) for c, nn, w in zip(cs, ns, ws)]
    mid = [(c[0] - 0.22 * w * nn[0], c[1] - 0.22 * w * nn[1]) for c, nn, w in zip(cs, ns, ws)]
    inn = [(c[0] - 0.30 * w * nn[0], c[1] - 0.30 * w * nn[1]) for c, nn, w in zip(cs, ns, ws)]
    tail_base.append(poly(top + bot[::-1]))
    i0, i1 = 1, N - 5
    tail_belly.append(poly(bot[i0:i1] + inn[i0:i1][::-1]))
    bands = ""
    for i in range(3, N - 4, 3):
        bands += poly([top[i], top[i + 1], mid[i + 1], mid[i]])
    tail_bands.append(bands)
    sc = f"M{P(*top[1])}"
    for i in range(1, N - 3, 2):
        s = i / (N - 1)
        h = 15 * (1 - s) ** 0.7 + 3
        mx, my = (top[i][0] + top[i + 2][0]) / 2, (top[i][1] + top[i + 2][1]) / 2
        tip = (mx + ns[i + 1][0] * h + ts[i + 1][0] * 6, my + ns[i + 1][1] * h + ts[i + 1][1] * 6)
        sc += f"L{P(*tip)}L{P(*top[i+2])}"
    tail_scutes.append(sc + "Z")

def anim_path(dlist, dur, attrs):
    return f'<path fill-rule="evenodd" {attrs}>{A_d(dlist, dur)}</path>'

tail_svg = (anim_path(tail_scutes, TT_PER, f'fill="{C_DARK}" stroke="{C_OUT}" stroke-width="2.6" stroke-linejoin="round"') +
            anim_path(tail_base, TT_PER, f'fill="url(#gTail)" stroke="{C_OUT}" stroke-width="3.2" stroke-linejoin="round"') +
            anim_path(tail_belly, TT_PER, 'fill="#EFE8A8" opacity=".85"') +
            anim_path(tail_bands, TT_PER, f'fill="{C_OUT}" opacity=".26"'))

# --- torso
TORSO = [(484, 334), (474, 304), (492, 270), (532, 244), (582, 224), (630, 206), (676, 196),
         (722, 202), (740, 238), (716, 278), (692, 310), (660, 340), (610, 360), (560, 368), (512, 362)]
torso_d = cr_path(TORSO, True)
samp = cr_sample(TORSO, True, 12)

def normal_at(i, pts):
    a = pts[(i - 1) % len(pts)]; b = pts[(i + 1) % len(pts)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dy)
    return (dy / l, -dx / l), (dx / l, dy / l)

# back scutes
sc_d = ""
acc = 0.0
last = samp[12 * 1]
next_at = 10.0
for i in range(12 * 1, 12 * 6 + 6):
    p = samp[i]
    acc += math.hypot(p[0] - last[0], p[1] - last[1]); last = p
    if acc >= next_at:
        (nx, ny), (tx, ty) = normal_at(i, samp)
        u = (i - 12) / (12 * 5.5)
        h = 18 - 8 * u
        w = 11 - 3 * u
        b1 = (p[0] - tx * w, p[1] - ty * w); b2 = (p[0] + tx * w, p[1] + ty * w)
        tip = (p[0] + nx * h - tx * 6, p[1] + ny * h - ty * 6)
        sc_d += f"M{P(*b1)}L{P(*tip)}L{P(*b2)}Z"
        next_at = acc + 25
back_scutes = f'<path d="{sc_d}" fill="{C_DARK}" stroke="{C_OUT}" stroke-width="2.8" stroke-linejoin="round"/>'

# belly strip
bi0, bi1 = 12 * 8 + 6, 12 * 13 + 4
outer, inner = [], []
for i in range(bi0, bi1 + 1):
    (nx, ny), _ = normal_at(i, samp)
    u = (i - bi0) / (bi1 - bi0)
    th = 11 + 27 * (1 - u) ** 0.9
    p = samp[i]
    outer.append((p[0] - nx * 1.2, p[1] - ny * 1.2)); inner.append((p[0] - nx * th, p[1] - ny * th))
belly_d = poly(outer + inner[::-1])
plates = ""
for j in range(0, len(outer), 4):
    a, b = outer[j], inner[j]
    plates += f"M{P(*a)}L{P(*b)}"
belly = (f'<path d="{belly_d}" fill="url(#gBelly)"/>'
         f'<path d="{plates}" stroke="#BDB26A" stroke-width="1.5" opacity=".75" fill="none" stroke-linecap="round"/>')

# rim light along the back
rim = []
for i in range(12 * 2, 12 * 6):
    (nx, ny), _ = normal_at(i, samp)
    p = samp[i]
    rim.append((p[0] - nx * 9, p[1] - ny * 9))
rim_d = "M" + "L".join(P(*p) for p in rim)

torso_svg = (back_scutes +
             f'<path d="{torso_d}" fill="url(#gBody)" stroke="{C_OUT}" stroke-width="3.4" stroke-linejoin="round"/>'
             f'<path d="{torso_d}" fill="url(#pScales)"/>' + belly +
             f'<path d="{rim_d}" stroke="#fff" stroke-opacity=".22" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')

# --- head
def lipy(x):
    pts = [(22, 22), (56, 19), (100, 13), (150, 9), (194, 8), (216, 2)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]

UH = [(-46, 24), (-52, -4), (-40, -32), (-14, -48), (22, -46), (56, -34), (96, -27), (140, -25),
      (178, -27), (200, -34), (216, -28), (222, -12), (216, 2), (194, 8), (150, 9), (100, 13),
      (56, 19), (22, 22), (-6, 30), (-30, 34)]
upper_d = cr_path(UH, True)
LJ = [(20, 24), (60, 22), (100, 18), (150, 14), (194, 12), (212, 8), (220, 16), (212, 26), (188, 33),
      (140, 39), (90, 43), (50, 45), (20, 45), (4, 37), (6, 27)]
lower_d = cr_path(LJ, True)

upper_teeth = ""
for x, h in [(70, 11), (96, 13), (122, 17), (148, 12), (176, 16), (202, 10)]:
    y = lipy(x) - 1.5
    upper_teeth += f"M{P(x-5.5, y)}L{P(x+.5, y+h)}L{P(x+6, y)}"
lower_teeth = ""
for x, h in [(84, 9), (110, 11), (136, 9), (162, 12), (190, 9)]:
    y = 14 + (lipy(x) - 14) * 0 + 14  # roughly jaw top
    lower_teeth += f"M{P(x-5, y+4)}L{P(x, y-h+4)}L{P(x+5, y+4)}"

head = ['<g transform="translate(745,200)">']
# mouth interior
head.append('<path d="M20,18L216,0L218,26L20,40Z" fill="#6E1B2C"/>')
# lower jaw
head.append(f'<g transform="translate(22,24)"><g>'
            f'<animateTransform attributeName="transform" type="rotate" values="2.2;5.2;2.2" dur="0.8s" repeatCount="indefinite"/>'
            f'<g transform="translate(-22,-24)">'
            f'<path d="{lower_d}" fill="url(#gJaw)" stroke="{C_OUT}" stroke-width="3.2" stroke-linejoin="round"/>'
            f'<path d="M64,20C100,10 150,6 186,10C168,17 120,19 64,22Z" fill="#F08AA0" stroke="#B94A66" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<path d="{lower_teeth}" fill="#fff" stroke="#55603f" stroke-width="1.4" stroke-linejoin="round"/>'
            f'<path d="M40,42Q120,48 200,32" stroke="#C9C47E" stroke-width="2" fill="none" opacity=".8" stroke-linecap="round"/>'
            f'</g></g></g>')
# upper head
head.append(f'<path d="{upper_d}" fill="url(#gHead)" stroke="{C_OUT}" stroke-width="3.4" stroke-linejoin="round"/>')
# snout highlight & scales
head.append('<path d="M70,-24C110,-20 160,-18 196,-22" stroke="#fff" stroke-opacity=".28" stroke-width="4.4" fill="none" stroke-linecap="round"/>')
head.append('<path d="M30,-8C60,-4 120,-4 205,-12" stroke="#1E5A39" stroke-opacity=".18" stroke-width="2" fill="none" stroke-linecap="round" stroke-dasharray="0 9" stroke-linejoin="round"/>')
# nostril
head.append('<ellipse cx="206" cy="-27" rx="5.6" ry="3.8" fill="#16402B" transform="rotate(-10 206 -27)"/><ellipse cx="204.6" cy="-28.4" rx="1.6" ry="1" fill="#fff" opacity=".6"/>')
# upper teeth
head.append(f'<path d="{upper_teeth}" fill="#fff" stroke="#55603f" stroke-width="1.5" stroke-linejoin="round"/>')
# cheek + smile crease
head.append('<ellipse cx="36" cy="8" rx="14" ry="8" fill="#D3F0A8" opacity=".5"/><ellipse cx="36" cy="8" rx="8" ry="4.4" fill="#FFB8C6" opacity=".45"/>')
head.append('<path d="M20,24C12,22 8,14 10,6" stroke="#1E5A39" stroke-width="2.8" fill="none" stroke-linecap="round"/>')
# eye bump + eye
head.append(f'<circle cx="16" cy="-38" r="24.5" fill="url(#gHead)" stroke="{C_OUT}" stroke-width="3.2"/>')
head.append('<path d="M-2,-56C6,-62 20,-62 30,-56" stroke="#fff" stroke-opacity=".3" stroke-width="3" fill="none" stroke-linecap="round"/>')
head.append('<g transform="translate(17,-38)"><g>'
            '<animateTransform attributeName="transform" type="scale" values="1 1;1 1;1 .06;1 1;1 1" keyTimes="0;.9;.935;.97;1" dur="4.2s" repeatCount="indefinite"/>'
            '<circle r="16" fill="#fff" stroke="#16402B" stroke-width="2.6"/>'
            '<circle cx="3.5" cy="1" r="10.5" fill="#FFD34E"/><circle cx="3.5" cy="1" r="10.5" fill="none" stroke="#E5A800" stroke-width="1.4"/>'
            '<ellipse cx="4.5" cy="1" rx="3.7" ry="9" fill="#14211B"/>'
            '<circle cx="8" cy="-4.5" r="3.4" fill="#fff"/><circle cx="1" cy="6" r="1.5" fill="#fff" opacity=".85"/>'
            '<path d="M-15.2,-5A16,16 0 0 1 15.2,-5Z" fill="#4AA763" stroke="#16402B" stroke-width="2.4" stroke-linejoin="round"/>'
            '</g></g>')
# helmet (worn over the eye bump, brim just above the eye)
HELMET = "M34,-58C20,-77 -10,-82 -38,-65C-62,-50 -67,-8 -56,24C-40,23 -22,16 -14,0C-8,-14 -10,-34 -2,-46C6,-56 20,-62 34,-58Z"
head.append(f'<path d="{HELMET}" fill="url(#gHelmet)" stroke="#8F4A00" stroke-width="3.4" stroke-linejoin="round"/>')
head.append('<path d="M28,-63C14,-76 -10,-77 -32,-63C-52,-50 -58,-18 -50,10" fill="none" stroke="#FFE2A8" stroke-width="3.2" stroke-linecap="round" opacity=".85"/>')
head.append('<path d="M-36,-46C-26,-60 -8,-68 12,-66M-46,-26C-34,-44 -22,-52 -10,-56M-44,-6C-36,-18 -26,-28 -18,-34" fill="none" stroke="#9A5200" stroke-width="4.6" stroke-linecap="round" opacity=".72"/>')
head.append('<path d="M-56,24C-40,23 -22,16 -14,0C-8,-14 -10,-34 -2,-46C6,-56 20,-62 34,-58" fill="none" stroke="#8F4A00" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>')
# strap
head.append('<path d="M-26,20C-20,34 -8,43 8,46" stroke="#6B3700" stroke-width="4" fill="none" stroke-linecap="round"/>'
            '<path d="M-26,20C-20,34 -8,43 8,46" stroke="#FFD08A" stroke-width="1.3" fill="none" stroke-linecap="round" stroke-opacity=".6"/>')
head.append('</g>')
head_svg = "".join(head)

# --- scarf
def ribbon_geom(t, root, L, w0, w1, phase, amp, head0):
    N = 16; ds = L / (N - 1)
    x, y = root
    top, bot, cs, ns = [], [], [], []
    for i in range(N):
        s = i / (N - 1)
        th = head0 + amp * (s ** 0.8) * math.sin(2 * math.pi * 1.6 * s - 2 * math.pi * t / 0.8 + phase)
        w = w0 + (w1 - w0) * s
        nn = (-math.sin(th), math.cos(th))
        cs.append((x, y)); ns.append(nn)
        top.append((x + w * nn[0], y + w * nn[1])); bot.append((x - w * nn[0], y - w * nn[1]))
        x += ds * math.cos(th); y += ds * math.sin(th)
    return cs, ns, top, bot

SCARF_N = 20
r1_d, r2_d, r1_st, r2_st = [], [], [], []
def stripes(cs, top, bot, step=3):
    st = ""
    for i in range(2, len(cs) - 1, step):
        st += poly([top[i], top[i + 1], bot[i + 1], bot[i]])
    return st
for k in range(SCARF_N + 1):
    t = k * 0.8 / SCARF_N
    cs, ns, top, bot = ribbon_geom(t, (686, 212), 150, 11, 8.5, 0.0, 0.5, math.pi + 0.2)
    r1_d.append(poly(top + bot[::-1])); r1_st.append(stripes(cs, top, bot))
    cs, ns, top, bot = ribbon_geom(t, (688, 218), 100, 9.5, 7, 1.7, 0.62, math.pi - 0.05)
    r2_d.append(poly(top + bot[::-1])); r2_st.append(stripes(cs, top, bot))

scarf_svg = (anim_path(r2_d, 0.8, 'fill="#FFB733" stroke="#B87600" stroke-width="2.6" stroke-linejoin="round"') +
             anim_path(r2_st, 0.8, 'fill="#E58A00" opacity=".55"') +
             anim_path(r1_d, 0.8, 'fill="url(#gScarf)" stroke="#B87600" stroke-width="2.6" stroke-linejoin="round"') +
             anim_path(r1_st, 0.8, 'fill="#E58A00" opacity=".55"') +
             '<path d="M686,214C694,238 716,256 740,262" fill="none" stroke="#B87600" stroke-width="23" stroke-linecap="round"/>'
             '<path d="M686,214C694,238 716,256 740,262" fill="none" stroke="url(#gScarf)" stroke-width="17.5" stroke-linecap="round"/>'
             '<path d="M690,230l12,-6M701,244l11,-8M716,254l7,-11M729,259l3,-11" stroke="#E58A00" stroke-width="3.2" stroke-linecap="round" opacity=".6"/>'
             '<path d="M683,216C690,236 710,252 734,257" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="2.4" stroke-linecap="round"/>'
             '<circle cx="686" cy="215" r="10.5" fill="url(#gScarf)" stroke="#B87600" stroke-width="2.6"/>'
             '<path d="M680,212C684,209 688,209 691,211" stroke="#fff" stroke-opacity=".6" stroke-width="2" fill="none" stroke-linecap="round"/>')

# --- arms
def arm_data(far):
    out = []
    for t in FR:
        sh0 = FS0 if far else S0
        sh = (sh0[0], sh0[1] + bob(t))
        hand = FGRIP if far else GRIP
        el = ik(sh, hand, A1, A2, -1)
        out.append((sh, el, hand))
    return out

def arm_svg(data, far):
    up = [f"M{P(*s)}L{P(*e)}" for (s, e, h) in data]
    lo = [f"M{P(*e)}L{P(*h)}" for (s, e, h) in data]
    full = [f"M{P(*s)}L{P(*e)}L{P(*h)}" for (s, e, h) in data]
    f1 = C_FAR if far else "#58B26A"
    f2 = "#418F57" if far else "#4DA761"
    hu = [hl_seg(s, e, 8.0) for (s, e, h) in data]
    hlow = [hl_seg(e, h, 6.0, 0.25) for (s, e, h) in data]
    op = ".12" if far else ".26"
    return (f'<path fill="none" stroke="{C_OUT}" stroke-width="34" stroke-linecap="round">{A_d(up, T)}</path>'
            f'<path fill="none" stroke="{C_OUT}" stroke-width="29" stroke-linecap="round">{A_d(lo, T)}</path>'
            f'<path fill="none" stroke="{f1}" stroke-width="28" stroke-linecap="round">{A_d(up, T)}</path>'
            f'<path fill="none" stroke="{f2}" stroke-width="23" stroke-linecap="round">{A_d(lo, T)}</path>'
            f'<path fill="none" stroke="#fff" stroke-opacity="{op}" stroke-width="3.6" stroke-linecap="round">{A_d(hu, T)}</path>'
            f'<path fill="none" stroke="#fff" stroke-opacity="{op}" stroke-width="3.2" stroke-linecap="round">{A_d(hlow, T)}</path>'
            f'<path fill="none" stroke="{C_OUT}" stroke-opacity=".28" stroke-width="4.2" stroke-linecap="round" stroke-dasharray="0 10">{A_d(full, T)}</path>')

def hand_svg(pos, far):
    fill = "#418F57" if far else "#5BB46C"
    return (f'<g transform="translate({pos[0]},{pos[1]})">'
            f'<path d="M-15,-9C-15,-19 12,-19 17,-8C22,2 17,15 4,15C-9,15 -15,6 -15,-9Z" fill="{fill}" stroke="{C_OUT}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M5,-10C13,-4 13,3 7,9M-3,-9C4,-3 4,3 -1,10" stroke="{C_OUT}" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".75"/>'
            f'<path d="M15,-5L21,-6L18,0ZM15,3L21,3L17,8Z" fill="#FFF8DE" stroke="#55603f" stroke-width="1.2" stroke-linejoin="round"/></g>')

ARM_N = arm_data(False); ARM_F = arm_data(True)

# ------------------------------------------------------------------ assemble bike group
bob_vals = [f"0,{n(bob(t))}" for t in FR]
BOB = A_tr(bob_vals, T)
nod_vals = [f"{n(nod(t))} 724 232" for t in FR]
NOD = A_tr(nod_vals, T, "rotate")

croc = []
croc.append(f'<g>{BOB}{tail_svg}</g>')
croc.append(arm_svg(ARM_F, True))
croc.append(hand_svg(FGRIP, True))
croc.append(f'<g>{BOB}{torso_svg}{scarf_svg}<g>{NOD}{head_svg}</g></g>')
croc.append(leg_svg(LEG_N, False))
croc.append(shoe_group(LEG_N, False))
croc.append(f'<g>{BOB}<circle cx="{H0[0]}" cy="{H0[1]}" r="25" fill="url(#gBody)"/><circle cx="{H0[0]}" cy="{H0[1]}" r="25" fill="url(#pScales)"/></g>')
croc.append(arm_svg(ARM_N, False))
croc.append(hand_svg(GRIP, False))

bounce_vals = [f"0,{n(bounce(t))}" for t in FR]
bike_group = (f'<g transform="translate({BIKE_DX},0)"><g>{A_tr(bounce_vals, T)}' + "".join(bike) + "".join(croc) + '</g></g>')

# ------------------------------------------------------------------ foreground
fore = scroll("tFore", V * 1.7)

# ------------------------------------------------------------------ output
svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" style="background:#cfe9f4">
<title>Crocodile riding a bicycle</title>
<desc>An animated, procedurally generated SVG: a crocodile in a helmet and scarf cycling along a riverside road.</desc>
<defs>{"".join(defs)}</defs>
<g id="scene">{"".join(scene)}</g>
{"".join(fx_back)}
{shadow}
{"".join(dust)}
{bike_group}
<g id="foreground">{fore}</g>
<rect width="{W}" height="{H}" fill="url(#gVig)" pointer-events="none"/>
</svg>
'''
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "crocodile_bike.svg")
open(out, "w", encoding="utf-8").write(svg)
print("written", out, f"{len(svg)/1024:.0f} KB")
