"""Infographic images for the Tableau Story (rendered as PNG so they look the same on Tableau Public).

Style: a data-model aesthetic. Entities are white cards with a colored header strip, field rows in a
monospace face, thin orthogonal connectors and a dot-grid canvas. Each bureau keeps one color
everywhere: Experian blue, Equifax orange, TransUnion green, and bureau names are bold in that color.
"""
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "tableau" / "_images"
S = 2  # 2x for sharp text
INTER = Path("/usr/share/fonts/opentype/inter")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

BUREAU = {"Experian": "#1F63B8", "Equifax": "#C4501F", "TransUnion": "#13805A"}
TINT = {"Experian": "#E3EDF9", "Equifax": "#FBE9DF", "TransUnion": "#E0F2EA"}
INK, INK2, MUTED, LINE, CANVAS, NAVY = "#1F2937", "#4A5568", "#6B7280", "#C9CED8", "#F7F8FA", "#08306B"
NEUTRAL = "#2B3445"
BW = re.compile(r"(Experian|Equifax|TransUnion)")


def f(weight, size):
    name = {"regular": "Inter-Regular.otf", "medium": "Inter-Medium.otf", "semibold": "Inter-SemiBold.otf", "bold": "Inter-Bold.otf"}[weight]
    return ImageFont.truetype(str(INTER / name), int(size * S))


def mono(size, bold=False):
    return ImageFont.truetype(MONO_B if bold else MONO, int(size * S))


def canvas(w, h, grid=True, bg=CANVAS):
    im = Image.new("RGB", (w * S, h * S), bg)
    d = ImageDraw.Draw(im)
    if grid:
        for x in range(0, w * S, 16 * S):
            for y in range(0, h * S, 16 * S):
                d.point((x, y), fill="#D5DAE2")
    return im, d


def rich_words(text):
    """Split text into (word, is_bureau) tokens, keeping punctuation attached to words."""
    out = []
    for w in text.split():
        m = BW.search(w)
        out.append((w, bool(m)))
    return out


def draw_rich(d, x, y, width, text, size=10, weight="regular", color=INK2, align="left", line_gap=4):
    """Wrap and draw text, with bureau names bold in their color. Returns the y after the last line."""
    fr, fb = f(weight, size), f("bold", size)
    words = rich_words(text)
    lines, cur, cw = [], [], 0
    space = d.textlength(" ", font=fr)
    for w, b in words:
        wl = d.textlength(w, font=fb if b else fr)
        if cur and cw + space + wl > width:
            lines.append((cur, cw)); cur, cw = [], 0
        cw = cw + (space if cur else 0) + wl
        cur.append((w, b, wl))
    if cur:
        lines.append((cur, cw))
    lh = fr.getbbox("Ag")[3] + line_gap * S
    for ln, lw in lines:
        xx = x + (width - lw) / 2 if align == "center" else x
        for i, (w, b, wl) in enumerate(ln):
            if b:
                m = BW.search(w)
                pre, word, post = w[:m.start()], m.group(1), w[m.end():]
                if pre:
                    d.text((xx, y), pre, font=fr, fill=color); xx += d.textlength(pre, font=fr)
                d.text((xx, y), word, font=fb, fill=BUREAU[word]); xx += d.textlength(word, font=fb)
                if post:
                    d.text((xx, y), post, font=fr, fill=color); xx += d.textlength(post, font=fr)
            else:
                d.text((xx, y), w, font=fr, fill=color); xx += wl
            xx += space
        y += lh
    return y


def text_height(d, width, text, size=10, weight="regular", line_gap=4):
    im = Image.new("RGB", (10, 10)); dd = ImageDraw.Draw(im)
    return draw_rich(dd, 0, 0, width, text, size, weight, line_gap=line_gap)


def entity(d, box, title, fields=(), head=NEUTRAL, head_ink="#FFFFFF", key="◆", fsize=9, title_size=10, body=None):
    """A data-model entity: header strip plus monospace field rows (name, value) or a rich body text."""
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
    hh = 26 * S
    d.rounded_rectangle((x0, y0, x1, y0 + hh), radius=6 * S, fill=head)
    d.rectangle((x0, y0 + hh - 6 * S, x1, y0 + hh), fill=head)
    d.text((x0 + 10 * S, y0 + 6 * S), f"{key} {title}", font=f("bold", title_size), fill=head_ink)
    y = y0 + hh + 8 * S
    for name, val in fields:
        d.text((x0 + 10 * S, y), name, font=mono(fsize), fill=MUTED)
        nx = x0 + 10 * S + d.textlength(name + "  ", font=mono(fsize))
        y = draw_rich(d, nx, y, x1 - nx - 10 * S, val, size=fsize + 0.5, weight="medium", color=INK) + 2 * S
    if body:
        draw_rich(d, x0 + 10 * S, y, x1 - x0 - 20 * S, body, size=fsize + 0.5, color=INK2)
    return y


def elbow(d, x0, y0, x1, y1, color="#8A93A3", dash=False, arrow=True):
    """Orthogonal connector: down, across, down, with a small arrowhead."""
    ym = (y0 + y1) / 2
    pts = [(x0, y0), (x0, ym), (x1, ym), (x1, y1)]
    for a, b in zip(pts, pts[1:]):
        if dash:
            n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / (6 * S)) or 1
            for k in range(0, n, 2):
                p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                q = (a[0] + (b[0] - a[0]) * min(k + 1, n) / n, a[1] + (b[1] - a[1]) * min(k + 1, n) / n)
                d.line((p, q), fill=color, width=int(1.5 * S))
        else:
            d.line((a, b), fill=color, width=int(1.5 * S))
    if arrow:
        d.polygon([(x1, y1), (x1 - 4 * S, y1 - 7 * S), (x1 + 4 * S, y1 - 7 * S)], fill=color)


def pill(d, cx, cy, text, color=NEUTRAL, fill="#FFFFFF"):
    ft = mono(8, True)
    w = d.textlength(text, font=ft) + 12 * S
    d.rounded_rectangle((cx - w / 2, cy - 9 * S, cx + w / 2, cy + 9 * S), radius=9 * S, fill=fill, outline=color, width=1 * S)
    d.text((cx - w / 2 + 6 * S, cy - 6 * S), text, font=ft, fill=color)


def save(im, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.png"
    im.save(p)
    return p


# ---------------------------------------------------------------- 1. roadmap (introduction)
def roadmap(w, h, steps):
    im, d = canvas(w, h)
    d.text((10 * S, 8 * S), "How the Story Unfolds", font=f("bold", 13), fill=NAVY)
    d.text((10 * S, 28 * S), "Read top to bottom; each step is one or more story points", font=f("regular", 9), fill=MUTED)
    top, n, gap = 50 * S, len(steps), 10 * S
    bh = (h * S - top - 8 * S - gap * (n - 1)) / n
    for i, (pts, title, line, head) in enumerate(steps):
        y0 = top + i * (bh + gap)
        box = (10 * S, y0, w * S - 10 * S, y0 + bh)
        d.rounded_rectangle(box, radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.rounded_rectangle((box[0], y0, box[0] + 6 * S, y0 + bh), radius=3 * S, fill=head)
        d.text((box[0] + 16 * S, y0 + 6 * S), pts, font=mono(8, True), fill=MUTED)
        d.text((box[0] + 16 * S, y0 + 19 * S), title, font=f("semibold", 11), fill=INK)
        draw_rich(d, box[0] + 16 * S, y0 + 36 * S, box[2] - box[0] - 26 * S, line, size=8.5, color=INK2, line_gap=2)
        if i < n - 1:
            x = w * S / 2
            d.line((x, y0 + bh, x, y0 + bh + gap), fill="#8A93A3", width=int(1.5 * S))
    return save(im, "info_roadmap")


# ---------------------------------------------------------------- 2. market chart
def market_chart(w, h, shares, top_counts, total):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    d.text((10 * S, 8 * S), "Share of All Recorded Pulls, by Bureau", font=f("bold", 13), fill=NAVY)
    d.text((10 * S, 28 * S), f"{total:,} bureau pulls across 49 states and DC, all lenders combined", font=f("regular", 9), fill=MUTED)
    y = 54 * S
    lab_w = 100 * S
    maxw = w * S - lab_w - 120 * S
    for b, (n, p) in shares.items():
        d.text((10 * S, y + 6 * S), b, font=f("bold", 12), fill=BUREAU[b])
        d.rectangle((lab_w, y, lab_w + maxw, y + 40 * S), fill="#EEF0F3")
        d.rectangle((lab_w, y, lab_w + maxw * p, y + 40 * S), fill=BUREAU[b])
        d.text((lab_w + maxw * p + 8 * S, y + 4 * S), f"{p:.0%}", font=f("bold", 16), fill=INK)
        d.text((lab_w + maxw * p + 8 * S, y + 25 * S), f"{n:,} pulls", font=f("regular", 8.5), fill=MUTED)
        y += 56 * S
    y += 8 * S
    d.line((10 * S, y, w * S - 10 * S, y), fill=LINE, width=1 * S)
    y += 10 * S
    d.text((10 * S, y), "Top Bureau by State (49 states and DC with data)", font=f("bold", 11), fill=NAVY)
    y += 22 * S
    x = 10 * S
    for name, cnt, col in top_counts:
        tw = (w * S - 20 * S - 3 * 8 * S) / 4
        d.rounded_rectangle((x, y, x + tw, y + 56 * S), radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.rectangle((x, y + 4 * S, x + 4 * S, y + 52 * S), fill=col)
        d.text((x + 12 * S, y + 4 * S), str(cnt), font=f("bold", 20), fill=col if col != "#9AA3B2" else INK)
        d.text((x + 12 * S, y + 36 * S), name, font=f("semibold", 9), fill=INK2)
        x += tw + 8 * S
    return save(im, "info_market")


def fact_tiles(w, h, facts):
    im, d = canvas(w, h)
    d.text((10 * S, 8 * S), "Why the Bureau Matters", font=f("bold", 13), fill=NAVY)
    top, n, gap = 34 * S, len(facts), 8 * S
    bh = (h * S - top - 6 * S - gap * (n - 1)) / n
    for i, (big, text, src) in enumerate(facts):
        y0 = top + i * (bh + gap)
        box = (10 * S, y0, w * S - 10 * S, y0 + bh)
        d.rounded_rectangle(box, radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.text((box[0] + 12 * S, y0 + 8 * S), big, font=f("bold", 17), fill=NAVY)
        bw = d.textlength(big, font=f("bold", 17)) + 22 * S
        yy = draw_rich(d, box[0] + bw, y0 + 9 * S, box[2] - box[0] - bw - 12 * S, text, size=9, color=INK2, line_gap=2)
        d.text((box[0] + bw, max(yy, y0 + bh - 18 * S)), src, font=mono(7.5), fill=MUTED)
    return save(im, "info_facts")


# ---------------------------------------------------------------- 3. KPI tiles
def kpi_tiles(w, h, title, sub, tiles, name):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    d.text((8 * S, 4 * S), title, font=f("bold", 12), fill=NAVY)
    d.text((8 * S, 22 * S), sub, font=f("regular", 8.5), fill=MUTED)
    top, n, gap = 40 * S, len(tiles), 8 * S
    tw = (w * S - 16 * S - gap * (n - 1)) / n
    for i, (lab, val, ctx, col) in enumerate(tiles):
        x0 = 8 * S + i * (tw + gap)
        box = (x0, top, x0 + tw, h * S - 4 * S)
        d.rounded_rectangle(box, radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.rectangle((x0, top + 6 * S, x0 + 4 * S, h * S - 10 * S), fill=col)
        d.text((x0 + 12 * S, top + 6 * S), lab, font=mono(7.5, True), fill=MUTED)
        d.text((x0 + 12 * S, top + 20 * S), val, font=f("bold", 18), fill=col if col in BUREAU.values() else INK)
        draw_rich(d, x0 + 12 * S, top + 46 * S, tw - 20 * S, ctx, size=8, color=INK2, line_gap=1)
    return save(im, name)


# ---------------------------------------------------------------- 4. decision tree (data-model style)
def decision_tree(w, h, branches, overrides):
    im, d = canvas(w, h)
    d.text((10 * S, 8 * S), "Decision Tree: Start From Your Strongest Report", font=f("bold", 13), fill=NAVY)
    d.text((10 * S, 28 * S), "IF a report is strongest, THEN favor the issuers that pull it. Override rules apply first.", font=f("regular", 9), fill=MUTED)
    W = w * S
    root = (W / 2 - 150 * S, 48 * S, W / 2 + 150 * S, 118 * S)
    entity(d, root, "START: strongest_report", [("check", "pull all three reports, compare scores and errors"), ("then", "follow the branch for the strongest report")], head=NEUTRAL)
    colw, gap = (W - 20 * S - 2 * 24 * S) / 3, 24 * S
    by0, by1 = 168 * S, 168 * S + 112 * S
    for i, (b, why, then, ex) in enumerate(branches):
        x0 = 10 * S + i * (colw + gap)
        box = (x0, by0, x0 + colw, by1)
        cx = x0 + colw / 2
        elbow(d, W / 2, root[3], cx, by0)
        pill(d, cx, by0 - 18 * S, f"IF {b.upper()} IS STRONGEST", color=BUREAU[b])
        entity(d, box, f"THEN {then}", [("why", why)] + ex, head=BUREAU[b])
    # override rules: one entity row along the bottom, linked with a dashed line
    oy0 = by1 + 44 * S
    ow = (W - 20 * S - 2 * 16 * S) / 3
    d.line((10 * S, oy0 - 22 * S, W - 10 * S, oy0 - 22 * S), fill=LINE, width=1 * S)
    pill(d, W / 2, oy0 - 22 * S, "OVERRIDES: CHECK THESE FIRST", color="#5B3FA8")
    for i, (cond, act) in enumerate(overrides):
        x0 = 10 * S + i * (ow + 16 * S)
        entity(d, (x0, oy0, x0 + ow, h * S - 8 * S), f"IF {cond}", [("then", act)], head="#5B3FA8")
    return save(im, "info_tree")


def whatif_table(w, h, rows):
    """An entity table: header, mono column names, one row per case, with a stacked chance bar."""
    im, d = canvas(w, h)
    x0, y0, x1, y1 = 10 * S, 8 * S, w * S - 10 * S, h * S - 8 * S
    d.rounded_rectangle((x0, y0, x1, y1), radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
    hh = 26 * S
    d.rounded_rectangle((x0, y0, x1, y0 + hh), radius=6 * S, fill=NEUTRAL)
    d.rectangle((x0, y0 + hh - 6 * S, x1, y0 + hh), fill=NEUTRAL)
    d.text((x0 + 10 * S, y0 + 6 * S), "◆ WHAT_IF: model's best guess for four real cases (typical application)", font=f("bold", 10), fill="#FFFFFF")
    cols = [("lender_in_state", 0.20), ("likely_bureau", 0.17), ("chance_by_bureau", 0.33), ("why_it_matters", 0.30)]
    cx = [x0 + 10 * S]
    for _, fr in cols:
        cx.append(cx[-1] + fr * (x1 - x0 - 20 * S))
    y = y0 + hh + 6 * S
    for (name, _), x in zip(cols, cx):
        d.text((x, y), name, font=mono(8, True), fill=MUTED)
    y += 18 * S
    d.line((x0, y, x1, y), fill=LINE, width=1 * S)
    rh = (y1 - y - 4 * S) / len(rows)
    for i, (case, lead, probs, why) in enumerate(rows):
        ry = y + i * rh
        if i % 2:
            d.rectangle((x0 + 1 * S, ry, x1 - 1 * S, ry + rh), fill="#FAFBFC")
        mid = ry + rh / 2
        d.text((cx[0], mid - 8 * S), case, font=f("semibold", 10), fill=INK)
        d.text((cx[1], mid - 8 * S), lead, font=f("bold", 10), fill=BUREAU[lead])
        # stacked bar in bureau colors
        bx, bw = cx[2], cx[3] - cx[2] - 16 * S
        xx = bx
        for b in ("Experian", "Equifax", "TransUnion"):
            seg = bw * probs[b]
            d.rectangle((xx, mid - 9 * S, xx + seg, mid + 9 * S), fill=BUREAU[b])
            if probs[b] >= 0.12:
                d.text((xx + 4 * S, mid - 6 * S), f"{probs[b]:.0%}", font=f("bold", 8.5), fill="#FFFFFF")
            xx += seg
        draw_rich(d, cx[3], mid - 12 * S, x1 - cx[3] - 10 * S, why, size=8.5, color=INK2, line_gap=1)
        d.line((x0, ry + rh, x1, ry + rh), fill="#EEF0F3", width=1 * S)
    # legend
    lx = x1 - 10 * S
    for b in ("TransUnion", "Equifax", "Experian"):
        tw = d.textlength(b, font=f("bold", 8.5))
        lx -= tw + 18 * S
        d.rectangle((lx, y0 + hh + 9 * S, lx + 9 * S, y0 + hh + 18 * S), fill=BUREAU[b])
        d.text((lx + 12 * S, y0 + hh + 7 * S), b, font=f("bold", 8.5), fill=BUREAU[b])
    return save(im, "info_whatif")


# ---------------------------------------------------------------- 5. pipeline (sources card)
def pipeline(w, h, steps):
    im, d = canvas(w, h)
    d.text((10 * S, 6 * S), "How Every Number Is Made", font=f("bold", 12), fill=NAVY)
    top, n, gap = 28 * S, len(steps), 22 * S
    bw = (w * S - 20 * S - gap * (n - 1)) / n
    for i, (t, line) in enumerate(steps):
        x0 = 10 * S + i * (bw + gap)
        box = (x0, top, x0 + bw, h * S - 6 * S)
        entity(d, box, t, body=line, head=NEUTRAL, fsize=8, title_size=9)
        if i < n - 1:
            ym = (top + h * S) / 2
            d.line((x0 + bw + 3 * S, ym, x0 + bw + gap - 4 * S, ym), fill="#8A93A3", width=int(1.5 * S))
            d.polygon([(x0 + bw + gap - 3 * S, ym), (x0 + bw + gap - 10 * S, ym - 4 * S), (x0 + bw + gap - 10 * S, ym + 4 * S)], fill="#8A93A3")
    return save(im, "info_pipe")


# ---------------------------------------------------------------- 6. bureau groups (recommendations)
def bureau_groups(w, h, groups):
    im, d = canvas(w, h)
    d.text((10 * S, 8 * S), "Spread Applications Across Bureau Groups", font=f("bold", 12), fill=NAVY)
    d.text((10 * S, 26 * S), "One lender from each group per round keeps any single report from stacking up", font=f("regular", 8.5), fill=MUTED)
    top, n, gap = 46 * S, len(groups), 10 * S
    bw = (w * S - 20 * S - gap * (n - 1)) / n
    for i, (b, lenders) in enumerate(groups):
        x0 = 10 * S + i * (bw + gap)
        head = BUREAU.get(b, NEUTRAL)
        entity(d, (x0, top, x0 + bw, h * S - 8 * S), b, [(f"{k+1:02d}", l) for k, l in enumerate(lenders)], head=head, fsize=8, title_size=9)
    return save(im, "info_groups")


# ---------------------------------------------------------------- 7. stakeholders and scope
def stakeholders(w, h, primary, secondary):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    d.text((8 * S, 4 * S), "Who This Serves", font=f("bold", 12), fill=NAVY)
    top, gap = 26 * S, 10 * S
    n = len(primary)
    cw = (w * S - 16 * S - gap * (n - 1)) / n
    rh = (h * S - top - 8 * S - gap) * 0.58
    for i, (t, line) in enumerate(primary):
        x0 = 8 * S + i * (cw + gap)
        box = (x0, top, x0 + cw, top + rh)
        d.rounded_rectangle(box, radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.rectangle((x0, top, x0 + cw, top + 4 * S), fill=NAVY)
        d.text((x0 + 12 * S, top + 12 * S), "PRIMARY", font=mono(7.5, True), fill=MUTED)
        d.text((x0 + 12 * S, top + 26 * S), t, font=f("semibold", 11), fill=INK)
        draw_rich(d, x0 + 12 * S, top + 46 * S, cw - 24 * S, line, size=9, color=INK2, line_gap=2)
    y2 = top + rh + gap
    for i, (t, line) in enumerate(secondary):
        x0 = 8 * S + i * (cw + gap)
        box = (x0, y2, x0 + cw, h * S - 8 * S)
        d.rounded_rectangle(box, radius=6 * S, fill="#F7F8FA", outline=LINE, width=1 * S)
        d.text((x0 + 12 * S, y2 + 8 * S), t, font=f("semibold", 10), fill=INK)
        draw_rich(d, x0 + 12 * S, y2 + 26 * S, cw - 24 * S, line, size=8.5, color=INK2, line_gap=2)
    return save(im, "info_stakeholders")


def scope(w, h, ins, outs):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    gap = 14 * S
    cw = (w * S - 16 * S - gap) / 2
    for k, (label, items, col, mark) in enumerate([("IN SCOPE: what this story answers", ins, "#2E6CA8", "✓"),
                                                   ("OUT OF SCOPE: what it does not try to answer", outs, "#8A93A3", "✕")]):
        x0 = 8 * S + k * (cw + gap)
        d.text((x0, 4 * S), label, font=f("bold", 11), fill=col if k == 0 else INK2)
        d.line((x0, 24 * S, x0 + cw, 24 * S), fill=col, width=2 * S)
        rh = (h * S - 32 * S) / len(items)
        for r, (t, line) in enumerate(items):
            y = 30 * S + r * rh
            d.text((x0, y + 2 * S), mark, font=f("bold", 11), fill=col)
            d.text((x0 + 18 * S, y), t, font=f("semibold", 10), fill=INK)
            draw_rich(d, x0 + 18 * S, y + 17 * S, cw - 20 * S, line, size=8.5, color=INK2, line_gap=1)
            if r < len(items) - 1:
                d.line((x0 + 18 * S, y + rh - 4 * S, x0 + cw, y + rh - 4 * S), fill="#EEF0F3", width=1 * S)
    return save(im, "info_scope")


# ---------------------------------------------------------------- 8. data and method
def flow(w, h, title, steps, name, result_head=None):
    im, d = canvas(w, h)
    d.text((10 * S, 6 * S), title, font=f("bold", 12), fill=NAVY)
    top, n, gap = 28 * S, len(steps), 22 * S
    bw = (w * S - 20 * S - gap * (n - 1)) / n
    for i, (t, fields) in enumerate(steps):
        x0 = 10 * S + i * (bw + gap)
        head = result_head if (result_head and i == n - 1) else NEUTRAL
        entity(d, (x0, top, x0 + bw, h * S - 6 * S), t, fields, head=head, fsize=8, title_size=9)
        if i < n - 1:
            ym = top + 13 * S
            d.line((x0 + bw + 3 * S, ym, x0 + bw + gap - 4 * S, ym), fill="#8A93A3", width=int(1.5 * S))
            d.polygon([(x0 + bw + gap - 3 * S, ym), (x0 + bw + gap - 10 * S, ym - 4 * S), (x0 + bw + gap - 10 * S, ym + 4 * S)], fill="#8A93A3")
    return save(im, name)


# ---------------------------------------------------------------- 9. share equation
def equation(w, h, examples):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    # the rule, written as an equation
    y = 8 * S
    parts = [("Pulls on one bureau in a state", INK), (" ÷ ", MUTED), ("All bureau pulls in that state", INK), (" = ", MUTED), ("Bureau share", "#2E6CA8")]
    tw = sum(d.textlength(t, font=f("bold", 15)) for t, _ in parts)
    x = (w * S - tw) / 2
    for t, c in parts:
        d.text((x, y), t, font=f("bold", 15), fill=c); x += d.textlength(t, font=f("bold", 15))
    d.text((w * S / 2 - d.textlength("The same rule colors every state on the next three maps", font=f("regular", 9)) / 2, y + 26 * S),
           "The same rule colors every state on the next three maps", font=f("regular", 9), fill=MUTED)
    y += 54 * S
    d.line((8 * S, y, w * S - 8 * S, y), fill=LINE, width=1 * S)
    rh = (h * S - y - 6 * S) / len(examples)
    for i, (state, b, n, tot, counts, note) in enumerate(examples):
        ry = y + i * rh + 8 * S
        d.text((8 * S, ry), state, font=f("bold", 12), fill=INK)
        eq = f"{n} ÷ {tot} = {n / tot:.0%}"
        d.text((8 * S, ry + 20 * S), b, font=f("bold", 10), fill=BUREAU[b])
        d.text((8 * S + d.textlength(b + "  ", font=f("bold", 10)), ry + 20 * S), eq, font=mono(10, True), fill=INK)
        d.text((8 * S, ry + 38 * S), note, font=f("regular", 8.5), fill=MUTED)
        # stacked bar of all three shares
        bx, bw = 300 * S, w * S - 320 * S
        xx = bx
        for bb in ("Experian", "Equifax", "TransUnion"):
            p = counts[bb] / tot
            seg = bw * p
            d.rectangle((xx, ry + 6 * S, xx + seg, ry + 34 * S), fill=BUREAU[bb] if bb == b else TINT[bb])
            if p >= 0.1:
                d.text((xx + 6 * S, ry + 12 * S), f"{bb[:2].upper() if bb != 'TransUnion' else 'TU'} {p:.0%}", font=f("bold", 9), fill="#FFFFFF" if bb == b else BUREAU[bb])
            xx += seg
        if i < len(examples) - 1:
            d.line((8 * S, y + (i + 1) * rh, w * S - 8 * S, y + (i + 1) * rh), fill="#EEF0F3", width=1 * S)
    return save(im, "info_equation")


# ---------------------------------------------------------------- 10. funding ladder
def ladder(w, h, tiers):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    n = len(tiers)
    ramp = ["#E4E6EB", "#CDD1D9", "#B3B9C4", "#969EAC", "#7A8394", "#5E687B", "#434C5E"]
    gap = 8 * S
    cw = (w * S - 16 * S - gap * (n - 1)) / n
    base = h * S - 70 * S          # bottom of the risers; the "do this" text sits below
    step = (base - 70 * S) / n
    for i, (rng, head, do) in enumerate(tiers):
        x0 = 8 * S + i * (cw + gap)
        top = base - step * (i + 1)
        d.rectangle((x0, top, x0 + cw, base), fill=ramp[i])
        d.rectangle((x0, top, x0 + cw, top + 4 * S), fill="#2B3445")
        d.text((x0, top - 40 * S), rng, font=mono(11, True), fill=NAVY)
        d.text((x0, top - 22 * S), head, font=f("semibold", 10), fill=INK)
        d.text((x0 + 6 * S, base - 22 * S), f"STEP {i + 1}", font=mono(8, True), fill="#FFFFFF" if i >= 3 else NAVY)
        draw_rich(d, x0, base + 8 * S, cw, do, size=8.5, color=INK2, line_gap=1)
    d.line((8 * S, base, w * S - 8 * S, base), fill=NAVY, width=1 * S)
    return save(im, "info_ladder")


# ---------------------------------------------------------------- 11. scorecard
def scorecard(w, h, bans, issuers):
    im, d = canvas(w, h, grid=False, bg="#FFFFFF")
    n, gap = len(bans), 8 * S
    tw = (w * S - 16 * S - gap * (n - 1)) / n
    th = 78 * S
    for i, (val, lab, col) in enumerate(bans):
        x0 = 8 * S + i * (tw + gap)
        d.rounded_rectangle((x0, 4 * S, x0 + tw, 4 * S + th), radius=6 * S, fill="#FFFFFF", outline=LINE, width=1 * S)
        d.text((x0 + 12 * S, 12 * S), val, font=f("bold", 24), fill=col)
        draw_rich(d, x0 + 12 * S, 46 * S, tw - 22 * S, lab, size=8.5, color=INK2, line_gap=1)
    y = 4 * S + th + 18 * S
    d.text((8 * S, y), "Each Issuer's Bureau Habit", font=f("bold", 12), fill=NAVY)
    d.text((8 * S, y + 18 * S), "Share of each issuer's recorded pulls. A long segment means a predictable issuer.", font=f("regular", 8.5), fill=MUTED)
    # legend
    lx = w * S - 8 * S
    for b in ("TransUnion", "Equifax", "Experian"):
        t = d.textlength(b, font=f("bold", 9)); lx -= t + 20 * S
        d.rectangle((lx, y + 3 * S, lx + 10 * S, y + 13 * S), fill=BUREAU[b]); d.text((lx + 13 * S, y), b, font=f("bold", 9), fill=BUREAU[b])
    y += 46 * S
    lab_w, bx = 130 * S, 146 * S
    bw = w * S - bx - 16 * S
    rh = (h * S - y - 8 * S) / len(issuers)
    for i, (name, sh) in enumerate(issuers):
        ry = y + i * rh
        bh = min(22 * S, rh - 6 * S)
        d.text((8 * S, ry + (bh - 14 * S) / 2), name, font=f("semibold" if name != "All lenders" else "bold", 10), fill=INK)
        xx = bx
        for b in ("Experian", "Equifax", "TransUnion"):
            seg = bw * sh[b]
            d.rectangle((xx, ry, xx + seg - 1 * S, ry + bh), fill=BUREAU[b])
            if sh[b] >= 0.07:
                d.text((xx + 5 * S, ry + (bh - 12 * S) / 2), f"{sh[b]:.0%}", font=f("bold", 8.5), fill="#FFFFFF")
            xx += seg
        if name == "All lenders":
            d.line((8 * S, ry + bh + 3 * S, w * S - 8 * S, ry + bh + 3 * S), fill=LINE, width=1 * S)
    # 50% guide
    gx = bx + bw * 0.5
    for yy in range(int(y - 4 * S), int(h * S - 6 * S), 8 * S):
        d.line((gx, yy, gx, yy + 4 * S), fill="#FFFFFF", width=int(1.5 * S))
    d.text((gx - d.textlength("half of pulls", font=mono(7.5)) / 2, y - 13 * S), "half of pulls", font=mono(7.5), fill=MUTED)
    return save(im, "info_scorecard")
