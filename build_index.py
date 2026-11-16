#!/usr/bin/env python3
"""Build the model-comparison page (index.html) for ahoo/claude-test.

All numbers (file sizes, animation element counts, external-resource checks)
are computed from the files in the repo, not typed by hand.
"""
import html
import os
import re
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.chdir(REPO)

PROMPT = "帮我用 svg 画一个鳄鱼骑自行车的动画，越精致越好，不要联网搜索素材"

# (display name, relative path, format label, generator script present?, note)
FINALS = [
    ("Claude Sonnet 5.5", "sonnet-5.5/crocodile_bike.svg", "SVG · SMIL", "sonnet-5.5/gen.py",
     "逐帧 IK 关键帧、d 属性形变的尾巴与围巾、多层视差背景"),
    ("Claude Opus 5.5", "opus-5.5/crocodile_bike.svg", "SVG · SMIL", "opus-5.5/gen.py",
     "反向运动学预计算 48 帧、尾灯闪烁、扬尘与速度线"),
    ("Claude Fable 5.2 · 第 3 轮", "fable-5.2/v3.html", "HTML · JavaScript", None,
     "内嵌 SVG，由 requestAnimationFrame 逐帧驱动；需下载后用浏览器打开"),
    ("Claude Haiku 5.5", "haiku-5.5/crocodile_bike.svg", "SVG · SMIL", "haiku-5.5/gen.py",
     "逐帧 IK 脚踏、固定齿轮联动、头盔与围巾，尾巴与围巾行波形变"),
]

ROUNDS = [
    ("第 1 轮", "fable-5.2/v1.html", "用户反馈：效果一般啊，细节不多"),
    ("第 2 轮", "fable-5.2/v2.html", "用户反馈：不是动画了啊，也没有尾巴了（已知失败版本，静止）"),
    ("第 3 轮（成品）", "fable-5.2/v3.html", "用户反馈：—（当前成品）"),
]

ANIM_RE = re.compile(r"<animate(?:Transform|Motion)?[\s>]")
EXT_RE = re.compile(r'(?:href|src)="https?://[^"]*"', re.I)


def stats(path):
    size = os.path.getsize(path)
    text = open(path, encoding="utf-8").read()
    smil = len(ANIM_RE.findall(text))
    js = text.count("requestAnimationFrame")
    ext = len(EXT_RE.findall(text))
    return size, smil, js, ext


def kb(n):
    return f"{n / 1024:.1f} KB"


def anim_cell(smil, js):
    if smil:
        return f"{smil} 个（SMIL）"
    if js:
        return "JS 逐帧驱动"
    return "无动画"


def preview(path):
    if path.endswith(".svg"):
        return f'<img src="{html.escape(path)}" alt="{html.escape(path)}">'
    return f'<iframe src="{html.escape(path)}" title="{html.escape(path)}" loading="lazy"></iframe>'


def card(name, path, fmt):
    size, smil, js, _ = stats(path)
    return f"""
    <article class="card">
      <div class="stage">{preview(path)}</div>
      <div class="info">
        <div class="name">{html.escape(name)}</div>
        <div class="tag">{html.escape(fmt)}</div>
        <div class="meta"><span>{kb(size)}</span><span>{anim_cell(smil, js)}</span></div>
        <a href="{html.escape(path)}" target="_blank" rel="noopener">打开文件 →</a>
      </div>
    </article>"""


# ---- gather metrics for every file in the table ----
rows = []
all_paths = [(n, p, f, g, note) for (n, p, f, g, note) in FINALS]
for label, path, fb in ROUNDS:
    all_paths.append((f"Fable 5.2 · {label}", path, "HTML · JavaScript", None, fb))

metrics = {}
for name, path, fmt, gen, note in all_paths:
    metrics[path] = stats(path)
max_size = max(v[0] for v in metrics.values())

for name, path, fmt, gen, note in all_paths:
    size, smil, js, ext = metrics[path]
    width = max(4, round(size / max_size * 100))
    gen_cell = (f'<a href="{html.escape(gen)}">{html.escape(gen)}</a>' if gen
                else '<span class="muted">无</span>')
    rows.append(f"""
        <tr>
          <td><b>{html.escape(name)}</b></td>
          <td><code>{html.escape(path)}</code></td>
          <td>{html.escape(fmt)}</td>
          <td><div class="bar"><i style="width:{width}%"></i></div><span class="num">{kb(size)}</span></td>
          <td>{anim_cell(smil, js)}</td>
          <td>{'无' if ext == 0 else f'{ext} 处'}</td>
          <td>{gen_cell}</td>
        </tr>""")

finals_html = "".join(card(n, p, f) for (n, p, f, g, note) in FINALS)
rounds_html = "".join(card(f"Fable 5.2 · {label}", path, "HTML · JavaScript") for label, path, fb in ROUNDS)
rounds_notes = "".join(f"<li><b>{html.escape(label)}</b>：{html.escape(fb)}</li>" for label, path, fb in ROUNDS)
final_notes = "".join(f"<li><b>{html.escape(n)}</b>：{html.escape(note)}</li>" for n, p, f, g, note in FINALS)

page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>鳄鱼骑自行车 · 模型对比</title>
<style>
:root {{ --bg:#f6f7fb; --card:#fff; --ink:#1d2433; --muted:#667085; --line:#e4e7ec; --accent:#2f6fd6; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font: 15px/1.6 -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; }}
header, main {{ max-width:1200px; margin:0 auto; padding:0 24px; }}
header {{ padding-top:36px; }}
h1 {{ font-size:28px; margin:0 0 6px; }}
.prompt {{ color:var(--muted); margin:0; }}
h2 {{ font-size:19px; margin:40px 0 6px; }}
.lead {{ color:var(--muted); margin:0 0 14px; font-size:14px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:16px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden;
  display:flex; flex-direction:column; }}
.stage {{ position:relative; aspect-ratio:16/10; background:#dff3ff; }}
.stage img, .stage iframe {{ position:absolute; inset:0; width:100%; height:100%; border:0; object-fit:contain; }}
.info {{ padding:12px 14px 14px; display:flex; flex-direction:column; gap:4px; }}
.name {{ font-weight:700; }}
.tag {{ font-size:12px; color:var(--muted); }}
.meta {{ display:flex; gap:12px; flex-wrap:wrap; font-size:13px; color:var(--muted); }}
a {{ color:var(--accent); text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line);
  border-radius:12px; overflow:hidden; font-size:14px; }}
th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:middle; }}
th {{ background:#f0f3f8; font-weight:600; white-space:nowrap; }}
tr:last-child td {{ border-bottom:0; }}
code {{ font-size:12px; color:var(--muted); }}
.bar {{ display:inline-block; vertical-align:middle; width:140px; height:8px; border-radius:4px;
  background:#e6ecf7; position:relative; margin-right:8px; }}
.bar i {{ position:absolute; left:0; top:0; bottom:0; border-radius:4px; background:var(--accent); }}
.num {{ font-variant-numeric: tabular-nums; }}
.muted {{ color:var(--muted); }}
.table-wrap {{ overflow-x:auto; }}
ul {{ padding-left:20px; margin:8px 0; }}
li {{ margin:4px 0; }}
.note {{ background:#fff8e6; border:1px solid #f3e1a6; border-radius:12px; padding:12px 16px; font-size:14px; }}
footer {{ max-width:1200px; margin:0 auto; padding:28px 24px 40px; color:var(--muted); font-size:13px; }}
</style>
</head>
<body>
<header>
  <h1>鳄鱼骑自行车 · 模型对比</h1>
  <p class="prompt">提示词：「{html.escape(PROMPT)}」· 日期：2026-11-15</p>
</header>
<main>

  <h2>成品并排</h2>
  <p class="lead">每张卡片都是实际动画。点“打开文件”可单独查看或下载。</p>
  <section class="grid">{finals_html}
  </section>

  <h2>Fable 5.2 三轮迭代</h2>
  <p class="lead">Fable 5.2 在聊天里出图，三轮结果都保留在 <code>fable-5.2/</code> 目录。</p>
  <section class="grid">{rounds_html}
  </section>
  <ul>{rounds_notes}</ul>

  <h2>指标对比</h2>
  <p class="lead">以下数字由脚本直接从仓库文件统计：文件大小、动画元素数量、外部资源引用数。</p>
  <div class="table-wrap">
  <table>
    <thead>
      <tr><th>模型</th><th>文件</th><th>格式</th><th>文件大小</th><th>动画实现</th><th>外部资源</th><th>生成脚本</th></tr>
    </thead>
    <tbody>{"".join(rows)}
    </tbody>
  </table>
  </div>

  <h2>要点</h2>
  <ul>{final_notes}</ul>
  <p class="note">这是一次性对比，不是评分。文件大小和元素数只反映实现方式，不直接代表画面好坏，好坏请以上面的预览为准。</p>

</main>
<footer>
  <div>仓库：<a href="https://github.com/ahoo/claude-test">github.com/ahoo/claude-test</a></div>
  <div>页面由 <code>build_index.py</code> 生成，数字来自仓库文件，不是手填。</div>
</footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(page)
print("wrote", os.path.abspath("index.html"), len(page), "bytes")
for p, v in metrics.items():
    print(f"  {p:28s} size={v[0]:7d} smil={v[1]:3d} js={v[2]} ext={v[3]}")
