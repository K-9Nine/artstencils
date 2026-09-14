#!/usr/bin/env python3
"""
reticle.py - stencil pieces for a mil-dot duplex rifle-scope reticle, sized to
a canvas, laid out on one A4 sheet.  Assumes the thin cross is already painted:
every piece has a 2 mm viewing slot that you line up on that painted line.

Pieces on the sheet
  POST    thick outer bar. Cut once, use four times (rotate). Its outer end
          butts against the canvas edge. Includes a "tick" crossbar layer
          (magenta) - only enable it for the bottom post.
  DOTS    one arm's mil-dots, starting from a cross-shaped window that you
          line up on the centre of the painted cross. Cut once, use four times.
  CENTRE  the red centre dot, with four slots to line up on the cross arms.

Usage
  python3 tools/reticle.py --canvas-mm 1000 -o out_reticle
Measure the painted canvas width and pass it; every dimension scales from it.
"""
import argparse
import math
import os

from PIL import Image, ImageDraw


def parse():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("-o", "--out", default="out_reticle")
    p.add_argument("--canvas-mm", type=float, default=1000.0,
                   help="width of the painted image area (reticle spans the whole width)")
    p.add_argument("--post-len", type=float, default=0.34,
                   help="thick post length as a fraction of the half-width")
    p.add_argument("--post-w", type=float, default=0.028, help="post width, fraction of half-width")
    p.add_argument("--dots", type=int, default=4, help="dots per arm")
    p.add_argument("--dot-spacing", type=float, default=0.13, help="fraction of half-width")
    p.add_argument("--dot-d", type=float, default=0.020, help="dot diameter, fraction of half-width")
    p.add_argument("--centre-d", type=float, default=0.034, help="red dot diameter, fraction")
    p.add_argument("--tick-w", type=float, default=0.086, help="bottom crossbar width, fraction")
    p.add_argument("--tick-t", type=float, default=0.012, help="bottom crossbar thickness, fraction")
    p.add_argument("--slot-w", type=float, default=2.0, help="viewing slot width in mm (absolute)")
    p.add_argument("--sheet", default="210x297", help="sheet size WxH mm")
    return p.parse_args()


def rect(x, y, w, h):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/>'


def circle(cx, cy, d):
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{d / 2:.2f}"/>'


def main():
    a = parse()
    os.makedirs(a.out, exist_ok=True)
    half = a.canvas_mm / 2
    post_len = a.post_len * half
    post_w = a.post_w * half
    spacing = a.dot_spacing * half
    dot_d = a.dot_d * half
    centre_d = a.centre_d * half
    tick_w, tick_t = a.tick_w * half, a.tick_t * half
    slot = a.slot_w
    sw, sh = (float(v) for v in a.sheet.lower().split("x"))
    margin = 6.0

    cut, tick, red, outline, info = [], [], [], [], []

    # ---------------- POST piece (vertical, outer end at top of the piece) ----
    piece_w = max(tick_w + 16, post_w + 30)
    slot_ext = min(80.0, half - post_len - spacing)     # how far the viewing slot runs inward
    piece_h = post_len + slot_ext + 5
    px, py = margin, margin
    outline.append(rect(px, py, piece_w, piece_h))
    cx = px + piece_w / 2
    cut.append(rect(cx - post_w / 2, py, post_w, post_len))           # the post, from the canvas edge
    cut.append(rect(cx - slot / 2, py + post_len + 3, slot, slot_ext - 3))  # viewing slot inward
    # tick crossbar sits at the inner end of the post (bottom arm only)
    tick.append(rect(cx - tick_w / 2, py + post_len - tick_t, tick_w, tick_t))
    info.append(f'<text x="{px + 3:.1f}" y="{py + piece_h - 3:.1f}">POST x4  edge at top  tick=bottom only</text>')

    # ---------------- DOTS strip (centre window at the top) ------------------
    strip_w = max(dot_d + 24, 36)
    win = 24.0                                             # centre cross window size
    strip_h = a.dots * spacing + win / 2 + dot_d / 2 + 6
    sx, sy = px + piece_w + margin, margin
    outline.append(rect(sx, sy, strip_w, strip_h))
    scx = sx + strip_w / 2
    c0y = sy + win / 2 + 2                                   # y of the reticle centre on the strip
    cut.append(rect(scx - win / 2, c0y - slot / 2, win, slot))          # centre window: horizontal slot
    cut.append(rect(scx - slot / 2, c0y - win / 2, slot, win))          # centre window: vertical slot
    prev_end = c0y + win / 2
    for i in range(1, a.dots + 1):
        dy = c0y + i * spacing
        # viewing slot between the previous feature and this dot, 1 mm short of each
        cut.append(rect(scx - slot / 2, prev_end + 1, slot, (dy - dot_d / 2) - prev_end - 2))
        cut.append(circle(scx, dy, dot_d))
        prev_end = dy + dot_d / 2
    info.append(f'<text x="{sx + 2:.1f}" y="{sy + strip_h - 3:.1f}">DOTS x4</text>')

    # ---------------- CENTRE piece (red dot) ---------------------------------
    cp = centre_d + 50
    ccx0, ccy0 = sx + strip_w + margin, margin
    outline.append(rect(ccx0, ccy0, cp, cp))
    ccx, ccy = ccx0 + cp / 2, ccy0 + cp / 2
    red.append(circle(ccx, ccy, centre_d))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        l0, l1 = centre_d / 2 + 4, cp / 2 - 4
        if dx:
            x0 = ccx + min(dx * l0, dx * l1)
            cut.append(rect(x0, ccy - slot / 2, l1 - l0, slot))
        else:
            y0 = ccy + min(dy * l0, dy * l1)
            cut.append(rect(ccx - slot / 2, y0, slot, l1 - l0))
    info.append(f'<text x="{ccx0 + 2:.1f}" y="{ccy0 + cp - 3:.1f}">CENTRE (red)</text>')

    need_w = ccx0 + cp + margin
    need_h = max(piece_h, strip_h, cp) + 2 * margin
    if need_w > sw or need_h > sh:
        print(f"WARNING: pieces need {need_w:.0f} x {need_h:.0f} mm, sheet is {sw:.0f} x {sh:.0f}. "
              f"Try a smaller --canvas-mm test or a bigger --sheet.")

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{sw}mm" height="{sh}mm" viewBox="0 0 {sw} {sh}">
  <!-- mm units. red = cut (black paint). magenta = cut ONLY for the bottom post (crossbar).
       orange = cut (red paint). green = piece outline, cut last. black text = ignore -->
  <g id="cut-black" fill="none" stroke="#ff0000" stroke-width="0.1">
{chr(10).join(cut)}
  </g>
  <g id="cut-tick-bottom-only" fill="none" stroke="#ff00ff" stroke-width="0.1">
{chr(10).join(tick)}
  </g>
  <g id="cut-red-paint" fill="none" stroke="#ff8000" stroke-width="0.1">
{chr(10).join(red)}
  </g>
  <g id="piece-outline" fill="none" stroke="#00aa00" stroke-width="0.1">
{chr(10).join(outline)}
  </g>
  <g id="labels" font-family="sans-serif" font-size="3" fill="#000">
{chr(10).join(info)}
  </g>
</svg>
'''
    with open(os.path.join(a.out, "reticle_pieces.svg"), "w") as f:
        f.write(svg)

    # ---------------- full-size reference of the whole reticle ---------------
    C = a.canvas_mm
    full = []
    thin = 0.010 * half
    full.append(rect(0, half - thin / 2, C, thin))
    full.append(rect(half - thin / 2, 0, thin, C))
    for ang in (0, 90, 180, 270):
        # posts as rects from the edge inward
        if ang == 0:   full.append(rect(half - post_w / 2, 0, post_w, post_len))
        if ang == 90:  full.append(rect(C - post_len, half - post_w / 2, post_len, post_w))
        if ang == 180: full.append(rect(half - post_w / 2, C - post_len, post_w, post_len))
        if ang == 270: full.append(rect(0, half - post_w / 2, post_len, post_w))
    for i in range(1, a.dots + 1):
        d = i * spacing
        full += [circle(half, half - d, dot_d), circle(half, half + d, dot_d),
                 circle(half - d, half, dot_d), circle(half + d, half, dot_d)]
    full.append(rect(half - tick_w / 2, C - post_len, tick_w, tick_t))
    with open(os.path.join(a.out, "reticle_full_reference.svg"), "w") as f:
        f.write(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{C}mm" height="{C}mm" viewBox="0 0 {C} {C}">
  <g fill="#000">{chr(10).join(full)}</g>
  <circle cx="{half}" cy="{half}" r="{centre_d / 2}" fill="#e01010"/>
</svg>
''')

    # ---------------- previews -----------------------------------------------
    s = 2.0  # px per mm
    im = Image.new("RGB", (int(C * s), int(C * s)), (225, 220, 210))
    d = ImageDraw.Draw(im)
    d.rectangle([0, (half - thin / 2) * s, C * s, (half + thin / 2) * s], fill=(20, 20, 20))
    d.rectangle([(half - thin / 2) * s, 0, (half + thin / 2) * s, C * s], fill=(20, 20, 20))
    d.rectangle([(half - post_w / 2) * s, 0, (half + post_w / 2) * s, post_len * s], fill=(20, 20, 20))
    d.rectangle([(half - post_w / 2) * s, (C - post_len) * s, (half + post_w / 2) * s, C * s], fill=(20, 20, 20))
    d.rectangle([0, (half - post_w / 2) * s, post_len * s, (half + post_w / 2) * s], fill=(20, 20, 20))
    d.rectangle([(C - post_len) * s, (half - post_w / 2) * s, C * s, (half + post_w / 2) * s], fill=(20, 20, 20))
    for i in range(1, a.dots + 1):
        dd = i * spacing
        for (x, y) in ((half, half - dd), (half, half + dd), (half - dd, half), (half + dd, half)):
            d.ellipse([(x - dot_d / 2) * s, (y - dot_d / 2) * s, (x + dot_d / 2) * s, (y + dot_d / 2) * s], fill=(20, 20, 20))
    d.rectangle([(half - tick_w / 2) * s, (C - post_len) * s, (half + tick_w / 2) * s, (C - post_len + tick_t) * s], fill=(20, 20, 20))
    d.ellipse([(half - centre_d / 2) * s, (half - centre_d / 2) * s, (half + centre_d / 2) * s, (half + centre_d / 2) * s], fill=(224, 16, 16))
    im.save(os.path.join(a.out, "preview_full.png"))

    # sheet preview: white = sheet, black = cut, red = centre, magenta = tick, green outline
    s2 = 4.0
    sheet = Image.new("RGB", (int(sw * s2), int(sh * s2)), (255, 255, 255))
    d2 = ImageDraw.Draw(sheet)
    import re
    def draw_list(items, col):
        for it in items:
            nums = [float(v) for v in re.findall(r'"([-\d.]+)"', it)]
            if it.startswith("<rect"):
                x, y, w, h = nums
                d2.rectangle([x * s2, y * s2, (x + w) * s2, (y + h) * s2], fill=col)
            else:
                cx_, cy_, r = nums
                d2.ellipse([(cx_ - r) * s2, (cy_ - r) * s2, (cx_ + r) * s2, (cy_ + r) * s2], fill=col)
    for o in outline:
        x, y, w, h = [float(v) for v in re.findall(r'"([-\d.]+)"', o)]
        d2.rectangle([x * s2, y * s2, (x + w) * s2, (y + h) * s2], outline=(0, 170, 0), width=2)
    draw_list(cut, (20, 20, 20)); draw_list(tick, (200, 0, 200)); draw_list(red, (224, 16, 16))
    sheet.save(os.path.join(a.out, "preview_sheet.png"))

    print(f"canvas {C:.0f} mm  half {half:.0f}")
    print(f"  posts     {post_w:.1f} mm wide x {post_len:.0f} mm long, from each edge inward")
    print(f"  dots      {a.dots} per arm, {dot_d:.1f} mm dia, every {spacing:.1f} mm from centre")
    print(f"  centre    {centre_d:.1f} mm red dot")
    print(f"  crossbar  {tick_w:.0f} x {tick_t:.1f} mm at the inner end of the bottom post")
    print(f"  pieces fit on {sw:.0f} x {sh:.0f}: {'yes' if need_w <= sw and need_h <= sh else 'NO'}")
    print(f"wrote {a.out}/reticle_pieces.svg, reticle_full_reference.svg, preview_full.png, preview_sheet.png")


if __name__ == "__main__":
    main()
