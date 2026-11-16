import math

N = 48  # keyframes for pedaling
CRANK_DUR = 1.2
WHEEL_DUR = 0.9
R_WHEEL = 68
V = 2 * math.pi * R_WHEEL / WHEEL_DUR  # px/s ground speed

BB = (370, 370)
CR = 28
REAR = (260, 370)
FRONT = (530, 370)

OUT = "#1e3f1b"
G = "#4f9e3f"
G_D = "#3a7d2f"
G_L = "#86c96e"
G_FAR = "#3b7a31"
BELLY = "#ece6b4"
BELLY_D = "#cfc68b"


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def ik(h, p, L1, L2, prefer="right"):
    dx, dy = p[0] - h[0], p[1] - h[1]
    d = math.hypot(dx, dy)
    d = max(min(d, L1 + L2 - 0.5), abs(L1 - L2) + 0.5)
    a = math.atan2(dy, dx)
    A = math.acos((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))
    k1 = (h[0] + L1 * math.cos(a - A), h[1] + L1 * math.sin(a - A))
    k2 = (h[0] + L1 * math.cos(a + A), h[1] + L1 * math.sin(a + A))
    if prefer == "right":
        return k1 if k1[0] > k2[0] else k2
    return k1 if k1[1] > k2[1] else k2


def cubic(p, t):
    mt = 1 - t
    x = mt**3 * p[0][0] + 3 * mt * mt * t * p[1][0] + 3 * mt * t * t * p[2][0] + t**3 * p[3][0]
    y = mt**3 * p[0][1] + 3 * mt * mt * t * p[1][1] + 3 * mt * t * t * p[2][1] + t**3 * p[3][1]
    dx = 3 * mt * mt * (p[1][0] - p[0][0]) + 6 * mt * t * (p[2][0] - p[1][0]) + 3 * t * t * (p[3][0] - p[2][0])
    dy = 3 * mt * mt * (p[1][1] - p[0][1]) + 6 * mt * t * (p[2][1] - p[1][1]) + 3 * t * t * (p[3][1] - p[2][1])
    return (x, y), (dx, dy)


def scutes(curve, n, size, t0=0.05, t1=0.95, sign=1, fill=G_D):
    s = []
    for i in range(n):
        t = t0 + (t1 - t0) * i / (n - 1)
        (x, y), (dx, dy) = cubic(curve, t)
        L = math.hypot(dx, dy)
        tx, ty = dx / L, dy / L
        nx, ny = sign * ty, -sign * tx
        sz = size * (0.75 + 0.25 * math.sin(math.pi * t))
        b = sz * 0.55
        pts = [(x - tx * b, y - ty * b), (x + nx * sz - tx * b * 0.3, y + ny * sz - ty * b * 0.3), (x + tx * b, y + ty * b)]
        s.append(f'<path d="M{f(pts[0][0])},{f(pts[0][1])} L{f(pts[1][0])},{f(pts[1][1])} L{f(pts[2][0])},{f(pts[2][1])}Z" fill="{fill}" stroke="{OUT}" stroke-width="2" stroke-linejoin="round"/>')
    return "\n".join(s)


def anim_vals(vals):
    return ";".join(vals)


# ---------- pedaling keyframes ----------
frames = [2 * math.pi * k / N for k in range(N + 1)]


def leg_anims(hip, phase, L1=72, L2=70):
    thigh, shin, foot = [], [], []
    for th in frames:
        a = th + phase
        pedal = (BB[0] + CR * math.cos(a), BB[1] + CR * math.sin(a))
        ankle = (pedal[0] - 3, pedal[1] - 11)
        knee = ik(hip, ankle, L1, L2, "right")
        thigh.append(f"M{f(hip[0])},{f(hip[1])} L{f(knee[0])},{f(knee[1])}")
        shin.append(f"M{f(knee[0])},{f(knee[1])} L{f(ankle[0])},{f(ankle[1])}")
        foot.append(f"{f(ankle[0])},{f(ankle[1])}")
    return anim_vals(thigh), anim_vals(shin), anim_vals(foot)


def pedal_anim(phase):
    v = []
    for th in frames:
        a = th + phase
        v.append(f"{f(BB[0] + CR * math.cos(a))},{f(BB[1] + CR * math.sin(a))}")
    return anim_vals(v)


def leg(hip, phase, col, col_d, outline=OUT, ident=""):
    th, sh, ft = leg_anims(hip, phase)
    d = CRANK_DUR
    a = lambda vals: f'<animate attributeName="d" dur="{d}s" repeatCount="indefinite" values="{vals}"/>'
    foot_path = (f'<path d="M-9,-2 C-10,-11 6,-12 16,-6 L27,-3 L21,0 L28,3 L20,4 L24,8 L12,7 C2,9 -9,8 -9,-2Z" '
                 f'fill="{col}" stroke="{outline}" stroke-width="2.5" stroke-linejoin="round"/>'
                 f'<path d="M0,-5 C5,-7 10,-6 14,-4" fill="none" stroke="{col_d}" stroke-width="2" stroke-linecap="round"/>')
    return f'''
<g>
  <path stroke="{outline}" stroke-width="30" stroke-linecap="round" fill="none">{a(th)}</path>
  <path stroke="{col}" stroke-width="24" stroke-linecap="round" fill="none">{a(th)}</path>
  <path stroke="{outline}" stroke-width="23" stroke-linecap="round" fill="none">{a(sh)}</path>
  <path stroke="{col}" stroke-width="17" stroke-linecap="round" fill="none">{a(sh)}</path>
  <path stroke="{col_d}" stroke-width="5" stroke-linecap="round" fill="none" opacity="0.55" stroke-dasharray="3 9">{a(sh)}</path>
  <g>
    <animateTransform attributeName="transform" type="translate" dur="{d}s" repeatCount="indefinite" values="{ft}"/>
    {foot_path}
  </g>
</g>'''


def pedal(phase, dark=False):
    c = "#2b2b2b" if not dark else "#1a1a1a"
    return f'''
<g>
  <animateTransform attributeName="transform" type="translate" dur="{CRANK_DUR}s" repeatCount="indefinite" values="{pedal_anim(phase)}"/>
  <rect x="-13" y="-3.5" width="26" height="7" rx="2" fill="{c}"/>
  <rect x="-13" y="-3.5" width="26" height="2" rx="1" fill="#666"/>
</g>'''


def crank_arm(phase, col):
    deg = math.degrees(phase)
    return f'''
<g>
  <animateTransform attributeName="transform" type="rotate" dur="{CRANK_DUR}s" repeatCount="indefinite"
     from="{f(deg)} {BB[0]} {BB[1]}" to="{f(deg + 360)} {BB[0]} {BB[1]}"/>
  <line x1="{BB[0]}" y1="{BB[1]}" x2="{BB[0] + CR}" y2="{BB[1]}" stroke="{col}" stroke-width="7" stroke-linecap="round"/>
  <circle cx="{BB[0] + CR}" cy="{BB[1]}" r="3.5" fill="#888"/>
</g>'''


def arm(sh, hand, col, col_d, outline=OUT):
    el = ik(sh, hand, 46, 46, "down")
    p1 = f"M{f(sh[0])},{f(sh[1])} L{f(el[0])},{f(el[1])}"
    p2 = f"M{f(el[0])},{f(el[1])} L{f(hand[0])},{f(hand[1])}"
    return f'''
<g>
  <path d="{p1}" stroke="{outline}" stroke-width="22" stroke-linecap="round" fill="none"/>
  <path d="{p1}" stroke="{col}" stroke-width="16" stroke-linecap="round" fill="none"/>
  <path d="{p2}" stroke="{outline}" stroke-width="19" stroke-linecap="round" fill="none"/>
  <path d="{p2}" stroke="{col}" stroke-width="13" stroke-linecap="round" fill="none"/>
  <circle cx="{hand[0]}" cy="{hand[1]}" r="10" fill="{col}" stroke="{outline}" stroke-width="2.5"/>
  <path d="M{hand[0]+3},{hand[1]-8} l6,-2 M{hand[0]+6},{hand[1]-3} l6,-1 M{hand[0]+6},{hand[1]+3} l6,1"
        stroke="#f4f0d8" stroke-width="2.4" stroke-linecap="round"/>
</g>'''


def wheel(c, idp):
    cx, cy = c
    spokes = []
    for i in range(18):
        a = 2 * math.pi * i / 18
        a2 = a + 0.35
        spokes.append(f'<line x1="{f(cx + 9 * math.cos(a2))}" y1="{f(cy + 9 * math.sin(a2))}" x2="{f(cx + 58 * math.cos(a))}" y2="{f(cy + 58 * math.sin(a))}"/>')
    tread = "".join(
        f'<rect x="{f(cx - 2.5)}" y="{f(cy - R_WHEEL - 5)}" width="5" height="5" rx="1" transform="rotate({f(360 * i / 36)} {cx} {cy})"/>'
        for i in range(36))
    return f'''
<g>
  <animateTransform attributeName="transform" type="rotate" dur="{WHEEL_DUR}s" repeatCount="indefinite"
     from="0 {cx} {cy}" to="360 {cx} {cy}"/>
  <circle cx="{cx}" cy="{cy}" r="{R_WHEEL}" fill="none" stroke="#222" stroke-width="12"/>
  <g fill="#333">{tread}</g>
  <circle cx="{cx}" cy="{cy}" r="{R_WHEEL - 4}" fill="none" stroke="#3a3a3a" stroke-width="2" opacity="0.6"/>
  <circle cx="{cx}" cy="{cy}" r="{R_WHEEL - 8}" fill="none" stroke="url(#rim)" stroke-width="5"/>
  <g stroke="#cfd4d9" stroke-width="1.6">{''.join(spokes)}</g>
  <circle cx="{cx}" cy="{cy}" r="11" fill="url(#hub)" stroke="#555" stroke-width="1.5"/>
  <circle cx="{cx}" cy="{cy}" r="4" fill="#444"/>
  <path d="M{cx - 40},{cy - 46} A61,61 0 0 1 {cx + 30},{cy - 53}" fill="none" stroke="#fff" stroke-width="2" opacity="0.5"/>
</g>'''


def tube(a, b, w=9):
    return (f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#8a221b" stroke-width="{w + 4}" stroke-linecap="round"/>',
            f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="url(#frameG)" stroke-width="{w}" stroke-linecap="round"/>')


def frame():
    seat_top = (342, 282)
    head_top = (482, 262)
    head_bot = (474, 302)
    tubes = [tube(REAR, BB, 7), tube(REAR, seat_top, 7), tube(BB, seat_top, 10), tube(seat_top, head_top, 10), tube(BB, head_bot, 11), tube(head_top, head_bot, 14)]
    outl = "".join(t[0] for t in tubes)
    body = "".join(t[1] for t in tubes)
    fork = f'''
  <path d="M474,300 Q498,336 {FRONT[0]},{FRONT[1]}" fill="none" stroke="#5a5f66" stroke-width="12" stroke-linecap="round"/>
  <path d="M474,300 Q498,336 {FRONT[0]},{FRONT[1]}" fill="none" stroke="#c9ced4" stroke-width="7" stroke-linecap="round"/>'''
    highlight = f'<line x1="350" y1="279" x2="476" y2="261" stroke="#ffb3a8" stroke-width="2.5" stroke-linecap="round" opacity="0.8"/>' \
                f'<line x1="372" y1="364" x2="468" y2="304" stroke="#ffb3a8" stroke-width="2.5" stroke-linecap="round" opacity="0.7"/>'
    text = '<text x="400" y="330" font-family="Georgia, serif" font-style="italic" font-weight="bold" font-size="13" fill="#fff" transform="rotate(-32 400 330)" opacity="0.9">Croco</text>'
    stem = '''
  <path d="M482,262 L486,240" stroke="#5a5f66" stroke-width="9" stroke-linecap="round"/>
  <path d="M482,262 L486,240" stroke="#c9ced4" stroke-width="5" stroke-linecap="round"/>
  <path d="M470,242 Q488,234 500,238 Q514,242 512,254" fill="none" stroke="#5a5f66" stroke-width="8" stroke-linecap="round"/>
  <path d="M470,242 Q488,234 500,238 Q514,242 512,254" fill="none" stroke="#d6dbe0" stroke-width="4" stroke-linecap="round"/>
  <circle cx="474" cy="236" r="6" fill="#f7d34a" stroke="#a8861b" stroke-width="1.5"/>
  <circle cx="472" cy="234" r="2" fill="#fff" opacity="0.8"/>'''
    saddle = '''
  <path d="M341,282 L338,268" stroke="#5a5f66" stroke-width="7" stroke-linecap="round"/>
  <path d="M308,266 Q326,256 362,262 Q368,272 352,274 L318,274 Q304,273 308,266Z" fill="#2d2420" stroke="#120d0b" stroke-width="2"/>
  <path d="M314,264 Q330,259 356,262" fill="none" stroke="#6b5a50" stroke-width="2" stroke-linecap="round"/>'''
    # chain
    chain = f'''
  <path d="M{REAR[0]},{REAR[1] - 9} L{BB[0]},{BB[1] - 19} M{REAR[0]},{REAR[1] + 9} L{BB[0]},{BB[1] + 19}" stroke="#555" stroke-width="3.5" fill="none" stroke-dasharray="3 2">
    <animate attributeName="stroke-dashoffset" from="0" to="-10" dur="0.25s" repeatCount="indefinite"/>
  </path>
  <circle cx="{REAR[0]}" cy="{REAR[1]}" r="9" fill="#777" stroke="#444" stroke-width="2"/>'''
    chainring = f'''
  <g>
    <animateTransform attributeName="transform" type="rotate" dur="{CRANK_DUR}s" repeatCount="indefinite" from="0 {BB[0]} {BB[1]}" to="360 {BB[0]} {BB[1]}"/>
    <circle cx="{BB[0]}" cy="{BB[1]}" r="20" fill="none" stroke="#666" stroke-width="5" stroke-dasharray="3 2.2"/>
    <circle cx="{BB[0]}" cy="{BB[1]}" r="17" fill="#b9bec4" stroke="#555" stroke-width="1.5"/>
    <path d="M{BB[0]},{BB[1] - 14} L{BB[0]},{BB[1] + 14} M{BB[0] - 14},{BB[1]} L{BB[0] + 14},{BB[1]}" stroke="#8a8f96" stroke-width="4"/>
    <circle cx="{BB[0]}" cy="{BB[1]}" r="6" fill="#555"/>
  </g>'''
    mudguard = f'''
  <path d="M{REAR[0] - 72},{REAR[1] + 4} A76,76 0 0 1 {REAR[0] + 30},{REAR[1] - 70}" fill="none" stroke="#e8e8e8" stroke-width="6" stroke-linecap="round"/>
  <path d="M{FRONT[0] - 40},{FRONT[1] - 64} A76,76 0 0 1 {FRONT[0] + 74},{FRONT[1] - 14}" fill="none" stroke="#e8e8e8" stroke-width="6" stroke-linecap="round"/>
  <circle cx="{REAR[0] - 70}" cy="{REAR[1] - 8}" r="5" fill="#ff3b2f" stroke="#7a1410" stroke-width="1.5">
     <animate attributeName="opacity" values="1;0.35;1" dur="0.8s" repeatCount="indefinite"/>
  </circle>
  <path d="M{FRONT[0] + 26},{FRONT[1] - 62} l14,-4 l2,10 l-14,2Z" fill="#fff6c8" stroke="#888" stroke-width="1.5"/>'''
    return chain, chainring, f"<g>{outl}{body}{highlight}{text}</g>{fork}{stem}{saddle}{mudguard}"


# ---------- croc pieces ----------
TORSO = "M305,262 C292,210 340,165 405,152 C432,147 456,152 472,162 L484,198 C466,222 432,250 402,270 C372,288 322,288 305,262Z"
BELLY_P = "M352,281 C392,270 438,238 482,196 L486,206 C468,232 436,258 404,275 C384,285 366,288 352,281Z"
TAIL = "M318,240 C262,238 205,255 158,284 C128,302 100,322 62,322 C88,312 120,298 160,298 C214,296 276,290 338,280Z"
HEAD_UP = "M445,166 C440,128 486,106 520,118 C548,128 600,132 648,142 C665,146 666,163 648,167 L522,172 C498,174 478,183 470,196Z"
JAW = "M468,190 C488,180 512,177 530,178 L641,170 C656,170 658,184 643,188 C603,199 520,205 486,203 C470,202 462,197 468,190Z"


def teeth():
    s = []
    for i in range(9):
        t = i / 8
        x = 530 + (636 - 530) * t
        y = 171.5 + (166.5 - 171.5) * t
        s.append(f'<path d="M{f(x - 3.5)},{f(y)} L{f(x)},{f(y + 8)} L{f(x + 3.5)},{f(y)}Z"/>')
    for i in range(8):
        t = i / 7
        x = 538 + (630 - 538) * t
        y = 178 + (171 - 178) * t
        s.append(f'<path d="M{f(x - 3)},{f(y)} L{f(x)},{f(y - 7)} L{f(x + 3)},{f(y)}Z"/>')
    return f'<g fill="#fffdf2" stroke="#9c9a86" stroke-width="0.8" stroke-linejoin="round">{"".join(s)}</g>'


def scale_spots():
    import random
    random.seed(7)
    s = []
    for (x, y, r) in [(560, 140, 4), (585, 142, 3.5), (610, 146, 3), (540, 135, 3), (470, 150, 4), (455, 140, 3),
                      (575, 152, 2.5), (600, 155, 2.5), (625, 156, 2.2)]:
        s.append(f'<ellipse cx="{x}" cy="{y}" rx="{r * 1.4}" ry="{r}" fill="{G_D}" opacity="0.7"/>')
    for (x, y) in [(340, 205), (365, 185), (395, 172), (425, 168), (330, 232), (360, 215), (390, 200), (420, 190), (380, 230), (410, 215)]:
        s.append(f'<path d="M{x - 8},{y} q8,-6 16,0 q-8,6 -16,0Z" fill="{G_D}" opacity="0.55"/>')
    return "".join(s)


back_curve = [(305, 262), (292, 210), (340, 165), (405, 152)]
neck_curve = [(405, 152), (432, 147), (456, 152), (472, 162)]
tail_curve = [(318, 240), (262, 238), (205, 255), (158, 284)]
tail_curve2 = [(158, 284), (128, 302), (100, 322), (62, 322)]
head_curve = [(522, 118), (548, 128), (600, 132), (648, 142)]


def belly_lines():
    s = []
    for t in [0.12, 0.25, 0.38, 0.51, 0.64, 0.77, 0.9]:
        # along belly band roughly from (356,282) to (484,200)
        x = 356 + (484 - 356) * t
        y = 282 + (200 - 282) * t
        s.append(f'<path d="M{f(x - 4)},{f(y - 7)} L{f(x + 7)},{f(y + 6)}" stroke="{BELLY_D}" stroke-width="2" stroke-linecap="round"/>')
    return "".join(s)


def scarf_tails():
    v1 = ["M452,176 C420,168 392,170 360,160 C352,158 346,164 350,170 C384,182 418,186 450,190Z",
          "M452,176 C420,160 392,178 360,166 C352,164 345,172 350,177 C384,186 418,180 450,190Z",
          "M452,176 C420,174 392,160 360,152 C352,150 346,157 350,163 C384,178 418,192 450,190Z",
          "M452,176 C420,168 392,170 360,160 C352,158 346,164 350,170 C384,182 418,186 450,190Z"]
    v2 = ["M450,184 C424,190 400,198 372,196 C364,196 362,203 368,207 C398,212 426,204 452,196Z",
          "M450,184 C424,196 400,190 372,202 C364,203 362,210 368,213 C398,214 426,200 452,196Z",
          "M450,184 C424,186 400,206 372,190 C364,189 362,196 368,200 C398,208 426,208 452,196Z",
          "M450,184 C424,190 400,198 372,196 C364,196 362,203 368,207 C398,212 426,204 452,196Z"]
    return f'''
<path fill="url(#scarfG)" stroke="#8c2a12" stroke-width="2" stroke-linejoin="round">
  <animate attributeName="d" dur="0.5s" repeatCount="indefinite" values="{';'.join(v2)}"/>
</path>
<path fill="url(#scarfG)" stroke="#8c2a12" stroke-width="2" stroke-linejoin="round">
  <animate attributeName="d" dur="0.42s" repeatCount="indefinite" values="{';'.join(v1)}"/>
</path>'''


# ---------- background ----------
def hills(y0, amp, period, phase, color, h=520):
    pts = []
    for x in range(0, 1601, 20):
        y = y0 - amp * (0.6 * math.sin(2 * math.pi * x / period + phase) + 0.4 * math.sin(4 * math.pi * x / period + phase * 2))
        pts.append(f"{x},{f(y)}")
    return f'<path d="M0,{h} L{" L".join(pts)} L1600,{h}Z" fill="{color}"/>'


def tree(x, base, s=1.0, kind=0):
    if kind == 0:
        return f'''<g transform="translate({x},{base}) scale({s})">
  <rect x="-5" y="-40" width="10" height="42" rx="3" fill="#7a5233"/>
  <circle cx="0" cy="-58" r="28" fill="#3f8a3a"/>
  <circle cx="-16" cy="-46" r="18" fill="#3f8a3a"/>
  <circle cx="16" cy="-46" r="18" fill="#3f8a3a"/>
  <circle cx="-6" cy="-66" r="16" fill="#58a64b"/>
  <circle cx="10" cy="-56" r="10" fill="#58a64b"/>
  <circle cx="-10" cy="-70" r="5" fill="#7cc46a" opacity="0.8"/>
</g>'''
    return f'''<g transform="translate({x},{base}) scale({s})">
  <rect x="-4" y="-18" width="8" height="20" fill="#6b4529"/>
  <path d="M0,-92 L24,-46 L14,-46 L30,-16 L-30,-16 L-14,-46 L-24,-46Z" fill="#2f7a3a"/>
  <path d="M0,-92 L-24,-46 L-14,-46 L-30,-16 L0,-16Z" fill="#3c9148" opacity="0.8"/>
</g>'''


def cloud(x, y, s):
    return f'''<g transform="translate({x},{y}) scale({s})" opacity="0.95">
  <ellipse cx="0" cy="0" rx="46" ry="16" fill="#fff"/>
  <circle cx="-18" cy="-8" r="18" fill="#fff"/>
  <circle cx="8" cy="-16" r="22" fill="#fff"/>
  <circle cx="28" cy="-4" r="14" fill="#fff"/>
  <ellipse cx="0" cy="8" rx="44" ry="6" fill="#dbe9f5"/>
</g>'''


def scroll(content, period, dur):
    return f'''<g>
  <animateTransform attributeName="transform" type="translate" from="0 0" to="-{period} 0" dur="{dur}s" repeatCount="indefinite"/>
  {content}
  <g transform="translate({period},0)">{content}</g>
</g>'''


def flowers():
    s = []
    import random
    random.seed(3)
    for i in range(26):
        x = random.uniform(0, 800)
        y = random.uniform(402, 432)
        c = random.choice(["#ffffff", "#ffd84d", "#ff8fb1", "#ffffff"])
        s.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(random.uniform(1.6, 3))}" fill="{c}"/>')
    return "".join(s)


def tufts():
    s = []
    import random
    random.seed(11)
    for i in range(22):
        x = random.uniform(0, 800)
        y = 440
        h = random.uniform(8, 16)
        s.append(f'<path d="M{f(x)},{y} q-3,-{f(h * 0.6)} -6,-{f(h)} M{f(x)},{y} q1,-{f(h * 0.7)} 2,-{f(h * 1.2)} M{f(x)},{y} q4,-{f(h * 0.5)} 8,-{f(h * 0.9)}" stroke="#4c9a3c" stroke-width="2.2" fill="none" stroke-linecap="round"/>')
    for x in [120, 520]:
        s.append(f'<g transform="translate({x},440)"><rect x="-3" y="-34" width="6" height="34" fill="#f2f2f2" stroke="#999"/><rect x="-3" y="-30" width="6" height="6" fill="#e04a3a"/></g>')
    return "".join(s)


def dust():
    s = []
    for i, (dy, r) in enumerate([(0, 6), (-6, 5), (4, 4.5), (-2, 5.5)]):
        b = i * 0.2
        s.append(f'''<circle cx="210" cy="{432 + dy}" r="{r}" fill="#e9dcc0">
  <animate attributeName="cx" from="215" to="120" dur="0.8s" begin="{b}s" repeatCount="indefinite"/>
  <animate attributeName="r" from="{r * 0.5}" to="{r * 2}" dur="0.8s" begin="{b}s" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0.9;0.5;0" dur="0.8s" begin="{b}s" repeatCount="indefinite"/>
</circle>''')
    return "".join(s)


def speed_lines():
    s = []
    for i, (y, x, w) in enumerate([(200, 60, 70), (228, 30, 90), (258, 20, 60), (330, 40, 80), (172, 120, 50)]):
        s.append(f'''<line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" stroke="#fff" stroke-width="3" stroke-linecap="round">
  <animate attributeName="opacity" values="0;0.85;0" dur="0.7s" begin="{i * 0.15}s" repeatCount="indefinite"/>
  <animateTransform attributeName="transform" type="translate" from="30 0" to="-60 0" dur="0.7s" begin="{i * 0.15}s" repeatCount="indefinite"/>
</line>''')
    return "".join(s)


def sun():
    rays = "".join(f'<path d="M0,-52 L5,-70 L-5,-70Z" transform="rotate({i * 30})"/>' for i in range(12))
    return f'''<g transform="translate(690,80)">
  <circle r="80" fill="url(#sunGlow)"/>
  <g fill="#ffd25a" opacity="0.8">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="30s" repeatCount="indefinite"/>
    {rays}
  </g>
  <circle r="40" fill="#ffd84d"/>
  <circle r="32" fill="#ffe57a"/>
</g>'''


chain, chainring, frame_body = frame()

HIP_N = (350, 262)
HIP_F = (340, 258)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#6fc3f0"/><stop offset="0.65" stop-color="#bfe6fa"/><stop offset="1" stop-color="#fdf3d8"/>
  </linearGradient>
  <radialGradient id="sunGlow"><stop offset="0.4" stop-color="#fff4b0" stop-opacity="0.9"/><stop offset="1" stop-color="#fff4b0" stop-opacity="0"/></radialGradient>
  <linearGradient id="frameG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff6a5c"/><stop offset="1" stop-color="#d4372c"/></linearGradient>
  <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f4f6f8"/><stop offset="1" stop-color="#8d949b"/></linearGradient>
  <radialGradient id="hub" cx="0.35" cy="0.35"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#8d949b"/></radialGradient>
  <linearGradient id="skin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{G_L}"/><stop offset="0.45" stop-color="{G}"/><stop offset="1" stop-color="{G_D}"/></linearGradient>
  <linearGradient id="tailG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{G}"/><stop offset="1" stop-color="{G_D}"/></linearGradient>
  <linearGradient id="scarfG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff7a3d"/><stop offset="1" stop-color="#ffb13d"/></linearGradient>
  <linearGradient id="road" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6b6f75"/><stop offset="1" stop-color="#4a4d52"/></linearGradient>
  <linearGradient id="field" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fd76a"/><stop offset="1" stop-color="#6fbf4f"/></linearGradient>
  <clipPath id="eyeClip"><ellipse cx="504" cy="114" rx="13" ry="12"/></clipPath>
</defs>

<!-- sky -->
<rect width="800" height="500" fill="url(#sky)"/>
{sun()}
{scroll(cloud(120, 70, 1.0) + cloud(420, 120, 0.7) + cloud(620, 50, 0.85), 800, 40)}
{scroll(hills(320, 30, 800, 0.0, "#a9d6b8"), 800, 24)}
{scroll(hills(355, 26, 400, 1.3, "#7fc28a"), 800, 14)}
<rect x="0" y="380" width="800" height="62" fill="url(#field)"/>
{scroll(flowers() + tree(60, 400, 0.9) + tree(250, 404, 1.0, 1) + tree(330, 398, 0.7) + tree(480, 402, 1.15) + tree(660, 404, 0.85, 1) + tree(740, 400, 0.75), 800, 4.5)}

<!-- road -->
<rect x="0" y="438" width="800" height="62" fill="url(#road)"/>
<rect x="0" y="436" width="800" height="5" fill="#d9cfb5"/>
<line x1="0" y1="474" x2="800" y2="474" stroke="#f4f1e6" stroke-width="5" stroke-dasharray="44 36">
  <animate attributeName="stroke-dashoffset" from="0" to="80" dur="{f(80 / V)}s" repeatCount="indefinite"/>
</line>
{scroll(tufts(), 800, f(800 / V))}

{speed_lines()}
<ellipse cx="395" cy="442" rx="200" ry="9" fill="#000" opacity="0.18"/>
{dust()}

<!-- far side: leg, pedal, arm -->
{crank_arm(math.pi, "#3a3a3a")}
{pedal(math.pi, True)}
{leg(HIP_F, math.pi, G_FAR, "#2b5c24")}
{arm((428, 194), (497, 238), G_FAR, "#2b5c24")}

<!-- bike -->
{wheel(REAR, "r")}
{wheel(FRONT, "f")}
{chain}
{frame_body}
{chainring}

<!-- tail -->
<g>
  <animateTransform attributeName="transform" type="rotate" values="-3 325 262;4 325 262;-3 325 262" dur="1.2s" repeatCount="indefinite" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>
  {scutes(tail_curve, 8, 11, 0.05, 0.98, -1)}
  {scutes(tail_curve2, 4, 8, 0.05, 0.7, -1)}
  <path d="{TAIL}" fill="url(#tailG)" stroke="{OUT}" stroke-width="3" stroke-linejoin="round"/>
  <path d="M310,282 C250,288 200,292 160,298" fill="none" stroke="{BELLY}" stroke-width="5" stroke-linecap="round" opacity="0.8"/>
  <g stroke="{G_D}" stroke-width="2" opacity="0.6">
    <line x1="290" y1="248" x2="292" y2="280"/><line x1="260" y1="250" x2="262" y2="284"/><line x1="230" y1="256" x2="232" y2="288"/>
    <line x1="200" y1="265" x2="203" y2="292"/><line x1="172" y1="276" x2="176" y2="296"/><line x1="146" y1="290" x2="150" y2="300"/>
  </g>
</g>

<!-- torso -->
{scutes(back_curve, 7, 12, 0.08, 0.98, 1)}
{scutes(neck_curve, 3, 9, 0.1, 0.7, 1)}
<path d="{TORSO}" fill="url(#skin)" stroke="{OUT}" stroke-width="3" stroke-linejoin="round"/>
{scale_spots()}
<path d="{BELLY_P}" fill="{BELLY}" stroke="{OUT}" stroke-width="2" stroke-linejoin="round"/>
{belly_lines()}

<!-- near leg & pedal -->
{crank_arm(0, "#2a2a2a")}
{pedal(0)}
{leg(HIP_N, 0, G, G_D)}

{scarf_tails()}

<!-- head -->
<g>
  <animateTransform attributeName="transform" type="rotate" values="0 470 185;-2 470 185;0 470 185;1.5 470 185;0 470 185" dur="1.2s" repeatCount="indefinite"/>
  <path d="{JAW}" fill="{BELLY}" stroke="{OUT}" stroke-width="3" stroke-linejoin="round"/>
  <path d="M522,172 L648,167 L641,170 L530,178Z" fill="#7a2020"/>
  {teeth()}
  {scutes(head_curve, 5, 4, 0.15, 0.85, 1)}
  <path d="{HEAD_UP}" fill="url(#skin)" stroke="{OUT}" stroke-width="3" stroke-linejoin="round"/>
  <path d="M528,171 C560,169 610,167 648,166" fill="none" stroke="{OUT}" stroke-width="2.5" stroke-linecap="round"/>
  <!-- smile curl -->
  <path d="M528,171 C518,172 512,168 510,162" fill="none" stroke="{OUT}" stroke-width="2.5" stroke-linecap="round"/>
  <!-- nostrils -->
  <ellipse cx="644" cy="141" rx="9" ry="6" fill="{G}" stroke="{OUT}" stroke-width="2"/>
  <ellipse cx="646" cy="140" rx="3" ry="2" fill="{OUT}"/>
  <!-- cheek -->
  <ellipse cx="510" cy="152" rx="10" ry="6" fill="#ff8f8f" opacity="0.45"/>
  <!-- eye -->
  <ellipse cx="503" cy="116" rx="21" ry="18" fill="{G}" stroke="{OUT}" stroke-width="3"/>
  <ellipse cx="504" cy="114" rx="13" ry="12" fill="#fff"/>
  <g clip-path="url(#eyeClip)">
    <circle cx="508" cy="114" r="8.5" fill="#f2c230"/>
    <circle cx="508" cy="114" r="8.5" fill="none" stroke="#c48f12" stroke-width="1.5"/>
    <ellipse cx="509" cy="114" rx="2.6" ry="7" fill="#1a1a1a"/>
    <circle cx="511.5" cy="110.5" r="2.4" fill="#fff"/>
    <ellipse cx="504" cy="101" rx="16" ry="0" fill="{G}">
      <animate attributeName="ry" values="0;0;14;0;0" keyTimes="0;0.9;0.94;0.98;1" dur="3.6s" repeatCount="indefinite"/>
    </ellipse>
  </g>
  <path d="M489,103 C496,96 512,96 520,102" fill="none" stroke="{OUT}" stroke-width="3" stroke-linecap="round"/>
  <!-- helmet -->
  <path d="M452,150 C446,112 482,86 520,92 C506,98 494,104 488,112 C478,122 470,138 466,154Z" fill="#2f8fe0" stroke="#174a78" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M458,140 C458,118 476,100 498,96" fill="none" stroke="#9fd2ff" stroke-width="3" stroke-linecap="round"/>
  <path d="M470,150 L478,128 M478,150 L490,118" stroke="#174a78" stroke-width="2" stroke-linecap="round"/>
  <!-- scarf band -->
  <path d="M446,168 Q468,176 486,192 L482,208 Q462,192 440,184Z" fill="url(#scarfG)" stroke="#8c2a12" stroke-width="2" stroke-linejoin="round"/>
  <path d="M452,173 L447,186 M464,180 L459,194 M475,188 L471,201" stroke="#fff3d0" stroke-width="3" stroke-linecap="round"/>
</g>

<!-- near arm -->
{arm((440, 202), (506, 244), G, G_D)}
</svg>
'''

open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "crocodile_bike.svg"), "w").write(svg)
print("ok", len(svg))
