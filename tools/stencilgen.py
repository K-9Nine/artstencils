#!/usr/bin/env python3
"""
stencilgen.py - turn a painting or photo into laser-cuttable multi-layer stencils.

Pipeline
  1. resize the image to a physical size (mm) at a working resolution (px/mm)
  2. split it into N tonal layers (k-means on luminance) or N colour layers
     (k-means on Lab colour).  Tonal layers are cumulative: layer 1 is every
     pixel darker than the lightest tone, layer N is only the darkest tone.
     Spray light -> dark and each layer overpaints the previous one.
  3. clean every mask so nothing is thinner than --min-feature-mm (spray bleed
     and laser kerf would eat it anyway) and drop tiny specks
  4. find islands (bits of sheet completely surrounded by cut-out) and join
     them to the mainland with bridges of --bridge-mm width
  5. trace each mask to an SVG in millimetre units, with registration marks
     that are identical on every layer, plus PNG previews

Usage
  python3 tools/stencilgen.py painting.jpg -o out --layers 4 --width-mm 280
  python3 tools/stencilgen.py painting.jpg -o out --mode colour --layers 6

Only depends on numpy, opencv-python-headless and Pillow.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageDraw

CUT = 255     # pixel value meaning "cut out / paint goes here"
SHEET = 0     # pixel value meaning "stencil material stays"


# ----------------------------------------------------------------------------
# arguments
# ----------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Generate laser-cuttable multi-layer stencils from an image.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("image", help="input image (jpg/png/...)")
    p.add_argument("-o", "--out", default="out", help="output directory")
    p.add_argument("--mode", choices=["tone", "colour"], default="tone",
                   help="tone = cumulative greyscale layers (add colour by hand); "
                        "colour = one stencil per quantised colour")
    p.add_argument("--layers", type=int, default=4,
                   help="number of stencil layers (not counting the painted ground)")
    p.add_argument("--width-mm", type=float, default=280.0,
                   help="physical width of the printed image area")
    p.add_argument("--max-height-mm", type=float, default=None,
                   help="shrink to fit this height if the image is tall")
    p.add_argument("--margin-mm", type=float, default=20.0,
                   help="blank stencil border around the image (holds registration marks)")
    p.add_argument("--px-per-mm", type=float, default=8.0,
                   help="working resolution")
    p.add_argument("--blur-mm", type=float, default=0.4,
                   help="pre-blur to kill canvas texture before quantising (0 = off)")
    p.add_argument("--min-feature-mm", type=float, default=1.2,
                   help="nothing thinner than this survives (cut or sheet)")
    p.add_argument("--min-area-mm2", type=float, default=4.0,
                   help="drop cut regions and sheet specks smaller than this")
    p.add_argument("--bridge-mm", type=float, default=2.5,
                   help="width of auto-generated bridges")
    p.add_argument("--bridges-per-island", type=int, default=2,
                   help="bridges added to each island (2 stops it flapping)")
    p.add_argument("--simplify-mm", type=float, default=0.15,
                   help="vector simplification tolerance")
    p.add_argument("--reg-mark-mm", type=float, default=8.0,
                   help="registration mark size")
    p.add_argument("--kerf-mm", type=float, default=0.0,
                   help="grow every cut by this much to compensate laser kerf (usually leave 0)")
    p.add_argument("--keep-lightest", action="store_true",
                   help="colour mode: also make a stencil for the lightest colour "
                        "(default treats it as the painted ground)")
    p.add_argument("--seed", type=int, default=7, help="k-means seed")
    return p.parse_args(argv)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
@dataclass
class Layer:
    index: int              # 1-based, spray order
    name: str
    mask: np.ndarray        # uint8, CUT where paint goes
    tone_rgb: tuple         # suggested paint colour for preview
    islands_bridged: int = 0
    cut_regions: int = 0
    notes: list = field(default_factory=list)


def odd(n: int) -> int:
    n = int(round(n))
    return max(1, n if n % 2 == 1 else n + 1)


def ellipse(diameter_px: float):
    d = odd(diameter_px)
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def load_and_size(path, width_mm, max_height_mm, ppm):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    img_w_mm = width_mm
    img_h_mm = width_mm * h / w
    if max_height_mm and img_h_mm > max_height_mm:
        img_h_mm = max_height_mm
        img_w_mm = max_height_mm * w / h
    W = int(round(img_w_mm * ppm))
    H = int(round(img_h_mm * ppm))
    img = img.resize((W, H), Image.LANCZOS)
    return np.asarray(img), img_w_mm, img_h_mm


def kmeans(data: np.ndarray, k: int, seed: int):
    cv2.setRNGSeed(seed)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centres = cv2.kmeans(data.astype(np.float32), k, None,
                                    criteria, 5, cv2.KMEANS_PP_CENTERS)
    return labels.flatten(), centres


# ----------------------------------------------------------------------------
# layer separation
# ----------------------------------------------------------------------------
def tone_layers(rgb, n_layers, blur_px, seed) -> tuple[list[Layer], dict]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    if blur_px > 0:
        gray = cv2.GaussianBlur(gray, (0, 0), blur_px)
    labels, centres = kmeans(gray.reshape(-1, 1), n_layers + 1, seed)
    centres = sorted(float(c) for c in centres.flatten())          # dark -> light
    thresholds = [(centres[i] + centres[i + 1]) / 2 for i in range(n_layers)]
    layers = []
    for i in range(n_layers):
        # layer 1 = everything darker than the lightest tone, ..., layer n = darkest only
        t = thresholds[n_layers - 1 - i]
        tone = int(round(centres[n_layers - 1 - i]))
        mask = np.where(gray < t, CUT, SHEET).astype(np.uint8)
        layers.append(Layer(i + 1, f"tone{i + 1}", mask, (tone, tone, tone)))
    info = {"ground_grey": int(round(centres[-1])),
            "tone_greys": [int(round(c)) for c in centres[:-1]][::-1],
            "thresholds": [round(t, 1) for t in thresholds][::-1]}
    return layers, info


def colour_layers(rgb, n_layers, blur_px, seed, keep_lightest) -> tuple[list[Layer], dict]:
    img = rgb
    if blur_px > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur_px)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).reshape(-1, 3)
    k = n_layers if keep_lightest else n_layers + 1
    labels, centres = kmeans(lab, k, seed)
    labels = labels.reshape(rgb.shape[:2])
    centres_rgb = cv2.cvtColor(centres.reshape(1, -1, 3).astype(np.uint8),
                               cv2.COLOR_LAB2RGB).reshape(-1, 3)
    order = np.argsort(-centres[:, 0])               # lightest first
    layers = []
    start = 0 if keep_lightest else 1
    for li, ci in enumerate(order[start:], start=1):
        mask = np.where(labels == ci, CUT, SHEET).astype(np.uint8)
        col = tuple(int(v) for v in centres_rgb[ci])
        layers.append(Layer(li, f"colour{li}", mask, col))
    ground = tuple(int(v) for v in centres_rgb[order[0]])
    return layers, {"ground_rgb": ground,
                    "layer_rgb": [l.tone_rgb for l in layers]}


# ----------------------------------------------------------------------------
# cleanup, islands, bridges
# ----------------------------------------------------------------------------
def drop_small(mask, value, min_area_px):
    """remove connected components of `value` smaller than min_area_px"""
    target = (mask == value).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(target, connectivity=8)
    small = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] < min_area_px]
    if small:
        mask = mask.copy()
        mask[np.isin(lab, small)] = CUT if value == SHEET else SHEET
    return mask


def clean_mask(mask, min_feature_px, min_area_px, kerf_px):
    k = ellipse(min_feature_px)
    m = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)     # kill thin cut slivers
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)       # kill thin sheet slivers
    m = drop_small(m, CUT, min_area_px)               # specks of paint
    m = drop_small(m, SHEET, min_area_px)             # specks of sheet (tiny islands)
    if kerf_px > 0:
        m = cv2.erode(m, ellipse(kerf_px * 2))        # shrink cut so kerf grows it back
    # soften pixel staircase a touch before tracing
    m = cv2.GaussianBlur(m, (0, 0), max(0.6, min_feature_px * 0.25))
    return np.where(m >= 128, CUT, SHEET).astype(np.uint8)


def find_islands(mask):
    """return (labels, island_ids, mainland_bool) for sheet regions"""
    sheet = (mask == SHEET).astype(np.uint8)
    n, lab, stats, cents = cv2.connectedComponentsWithStats(sheet, connectivity=8)
    edge = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
    edge = set(int(e) for e in edge) - {0}
    islands = [i for i in range(1, n) if i not in edge]
    mainland = np.isin(lab, list(edge))
    return lab, islands, mainland, stats


def nearest_mainland(mainland_bool):
    """distance to mainland + coordinates of the nearest mainland pixel, per pixel"""
    src = np.where(mainland_bool, 0, 255).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(
        src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zs = np.argwhere(mainland_bool)                       # (y, x) of every mainland pixel
    lut = np.zeros((labels.max() + 1, 2), dtype=np.int32)
    lut[labels[zs[:, 0], zs[:, 1]]] = zs
    return dist, labels, lut


def add_bridges(mask, bridge_px, per_island):
    """join every island to the mainland; islands are processed nearest-first
    and become mainland once bridged so chains of islands work."""
    mask = mask.copy()
    lab, islands, mainland, stats = find_islands(mask)
    # pixel lists per island, computed once
    pix = {i: np.where(lab == i) for i in islands}
    remaining = set(islands)
    n_bridged = 0
    while remaining:
        dist, labels, lut = nearest_mainland(mainland)
        # pick the island closest to the mainland
        best = None
        for i in remaining:
            ys, xs = pix[i]
            d = dist[ys, xs]
            j = int(np.argmin(d))
            if best is None or d[j] < best[0]:
                best = (d[j], i, j)
        _, i, j = best
        ys, xs = pix[i]
        remaining.discard(i)
        cy, cx = ys.mean(), xs.mean()
        p0 = (int(xs[j]), int(ys[j]))
        t0 = lut[labels[ys[j], xs[j]]]
        picks = [(p0, t0)]
        # further bridges: prefer the opposite side of the island
        v0 = np.array([p0[0] - cx, p0[1] - cy])
        d = dist[ys, xs].astype(np.float64)
        for _ in range(per_island - 1):
            v = np.stack([xs - cx, ys - cy], axis=1)
            nv = np.linalg.norm(v, axis=1) + 1e-6
            cosang = (v @ v0) / (nv * (np.linalg.norm(v0) + 1e-6))
            for limit in (-0.3, 0.3, 1.1):
                cand = np.where(cosang < limit)[0]
                if len(cand):
                    jj = cand[int(np.argmin(d[cand]))]
                    p = (int(xs[jj]), int(ys[jj]))
                    t = lut[labels[ys[jj], xs[jj]]]
                    picks.append((p, t))
                    v0 = np.array([p[0] - cx, p[1] - cy])
                    break
        for p, t in picks:
            cv2.line(mask, p, (int(t[1]), int(t[0])), SHEET, int(round(bridge_px)))
            cv2.line(mainland.view(np.uint8), p, (int(t[1]), int(t[0])), 1, int(round(bridge_px)))
        mainland[ys, xs] = True
        n_bridged += 1
        if n_bridged % 25 == 0:
            print(f"      bridged {n_bridged}/{len(islands)} islands", flush=True)
    return mask, n_bridged


# ----------------------------------------------------------------------------
# vector output
# ----------------------------------------------------------------------------
def trace(mask, eps_px, ppm, offset_mm):
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    paths = []
    for c in contours:
        c = cv2.approxPolyDP(c, eps_px, True)
        if len(c) < 3:
            continue
        pts = c.reshape(-1, 2) / ppm + offset_mm
        d = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z"
        paths.append(d)
    return paths


def reg_marks_svg(sheet_w, sheet_h, margin, size):
    """crosshair-in-circle at each corner of the margin, identical on every layer"""
    r = size / 2
    out = []
    c = margin / 2
    for (x, y) in [(c, c), (sheet_w - c, c), (c, sheet_h - c), (sheet_w - c, sheet_h - c)]:
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}"/>')
        out.append(f'<path d="M {x - r:.2f},{y:.2f} L {x + r:.2f},{y:.2f} '
                   f'M {x:.2f},{y - r:.2f} L {x:.2f},{y + r:.2f}"/>')
    return "\n".join(out)


def write_svg(path, paths, sheet_w, sheet_h, margin, img_w, img_h, reg_size, label):
    body = "\n".join(f'<path d="{d}"/>' for d in paths)
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{sheet_w:.2f}mm" height="{sheet_h:.2f}mm"
     viewBox="0 0 {sheet_w:.2f} {sheet_h:.2f}">
  <!-- units are millimetres. red = CUT, blue = registration (cut on ALL layers),
       green = sheet outline, black text = engrave or ignore -->
  <g id="sheet-outline" fill="none" stroke="#00aa00" stroke-width="0.1">
    <rect x="0" y="0" width="{sheet_w:.2f}" height="{sheet_h:.2f}"/>
  </g>
  <g id="image-area" fill="none" stroke="#bbbbbb" stroke-width="0.1" stroke-dasharray="2,2">
    <rect x="{margin:.2f}" y="{margin:.2f}" width="{img_w:.2f}" height="{img_h:.2f}"/>
  </g>
  <g id="registration" fill="none" stroke="#0000ff" stroke-width="0.1">
{reg_marks_svg(sheet_w, sheet_h, margin, reg_size)}
  </g>
  <g id="label" font-family="sans-serif" font-size="4" fill="#000000">
    <text x="{margin:.2f}" y="{margin * 0.55:.2f}">{label}</text>
  </g>
  <g id="cut" fill="none" stroke="#ff0000" stroke-width="0.1" fill-rule="evenodd">
{body}
  </g>
</svg>
'''
    with open(path, "w") as f:
        f.write(svg)


# ----------------------------------------------------------------------------
# previews
# ----------------------------------------------------------------------------
def layer_preview_png(path, mask, islands_before):
    """white = sheet, black = cut. Islands that got bridged shown in red outline."""
    img = np.full(mask.shape + (3,), 255, np.uint8)
    img[mask == CUT] = (30, 30, 30)
    if islands_before is not None:
        edges = cv2.morphologyEx(islands_before.astype(np.uint8), cv2.MORPH_GRADIENT,
                                 ellipse(3))
        img[edges > 0] = (220, 30, 30)
    Image.fromarray(img).save(path)



def swatch_card_png(path, ground_rgb, layers, mode):
    """one row per paint: ground first, then the stencils in spray order.
    Shows the target colour, hex, and a mixing hint."""
    rows = [("ground / base coat (brush on)", ground_rgb)] + \
           [(f"layer {l.index:02d}  {l.name}  (spray {l.index}/{len(layers)})", l.tone_rgb)
            for l in layers]
    W, rh, sw = 900, 90, 260
    img = Image.new("RGB", (W, rh * len(rows) + 20), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for k, (label, rgb) in enumerate(rows):
        y = 10 + k * rh
        d.rectangle([10, y, 10 + sw, y + rh - 10], fill=tuple(rgb), outline=(0, 0, 0))
        r, g, b = rgb
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if mode == "tone":
            hint = f"greyscale {lum:.0f}/255  ->  roughly {100 - lum / 2.55:.0f}% black in white"
        else:
            hint = f"luminance {lum:.0f}/255"
        for i, t in enumerate([label, f"rgb({r}, {g}, {b})   #{r:02x}{g:02x}{b:02x}", hint]):
            d.text((sw + 30, y + 8 + i * 24), t, fill=(0, 0, 0))
    img.save(path)

def composite_preview_png(path, shape, ground_rgb, layers):
    img = np.empty(shape + (3,), np.uint8)
    img[:] = ground_rgb
    for l in layers:
        img[l.mask == CUT] = l.tone_rgb
    Image.fromarray(img).save(path)


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main(argv=None):
    a = parse_args(argv)
    ppm = a.px_per_mm
    os.makedirs(a.out, exist_ok=True)

    rgb, img_w_mm, img_h_mm = load_and_size(a.image, a.width_mm, a.max_height_mm, ppm)
    H, W = rgb.shape[:2]
    print(f"image area {img_w_mm:.1f} x {img_h_mm:.1f} mm  ({W} x {H} px)")

    blur_px = a.blur_mm * ppm
    if a.mode == "tone":
        layers, info = tone_layers(rgb, a.layers, blur_px, a.seed)
        ground = (info["ground_grey"],) * 3
    else:
        layers, info = colour_layers(rgb, a.layers, blur_px, a.seed, a.keep_lightest)
        ground = info["ground_rgb"]

    sheet_w = img_w_mm + 2 * a.margin_mm
    sheet_h = img_h_mm + 2 * a.margin_mm
    min_feature_px = a.min_feature_mm * ppm
    min_area_px = a.min_area_mm2 * ppm * ppm
    bridge_px = max(2, a.bridge_mm * ppm)

    report = {"image": os.path.abspath(a.image), "mode": a.mode,
              "image_mm": [round(img_w_mm, 1), round(img_h_mm, 1)],
              "sheet_mm": [round(sheet_w, 1), round(sheet_h, 1)],
              "ground_rgb": list(ground), "separation": info, "layers": []}

    for l in layers:
        print(f"  layer {l.index}: cleaning + bridging ...", flush=True)
        m = clean_mask(l.mask, min_feature_px, min_area_px, a.kerf_mm * ppm)
        lab, islands, _, stats = find_islands(m)
        islands_before = np.isin(lab, islands) if islands else None
        m, n_bridged = add_bridges(m, bridge_px, a.bridges_per_island)
        m = drop_small(m, CUT, min_area_px)          # bridges can leave crumbs
        _, still, _, _ = find_islands(m)
        n_cut, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0:2]
        l.mask = m
        l.islands_bridged = n_bridged
        l.cut_regions = len(n_cut)
        if still:
            l.notes.append(f"{len(still)} island(s) still unbridged - check in Inkscape")
        coverage = float((m == CUT).mean() * 100)

        stem = f"layer{l.index:02d}_{l.name}"
        paths = trace(m, a.simplify_mm * ppm, ppm, a.margin_mm)
        write_svg(os.path.join(a.out, stem + ".svg"), paths, sheet_w, sheet_h,
                  a.margin_mm, img_w_mm, img_h_mm, a.reg_mark_mm,
                  f"{stem}  spray order {l.index}/{len(layers)}  rgb{l.tone_rgb}")
        layer_preview_png(os.path.join(a.out, stem + ".png"), m, islands_before)

        report["layers"].append({
            "file": stem + ".svg", "spray_order": l.index, "paint_rgb": list(l.tone_rgb),
            "cut_regions": l.cut_regions, "islands_bridged": n_bridged,
            "coverage_pct": round(coverage, 1), "svg_paths": len(paths), "notes": l.notes})
        print(f"  {stem}: {l.cut_regions} cut regions, {n_bridged} islands bridged, "
              f"{coverage:.1f}% coverage, paint rgb{l.tone_rgb}"
              + (f"  ** {l.notes}" if l.notes else ""))

    composite_preview_png(os.path.join(a.out, "preview_composite.png"), (H, W), ground, layers)
    swatch_card_png(os.path.join(a.out, "swatches.png"), ground, layers, a.mode)
    Image.fromarray(rgb).save(os.path.join(a.out, "preview_source.png"))
    with open(os.path.join(a.out, "report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print()
    print("PAINT PER STENCIL (also in swatches.png and report.json)")
    print(f"  ground / base coat   rgb{tuple(ground)}   brush on, let cure")
    for l in layers:
        r, g, b = l.tone_rgb
        print(f"  layer {l.index:02d} {l.name:<9} rgb({r:3d},{g:3d},{b:3d})  #{r:02x}{g:02x}{b:02x}   spray {l.index}/{len(layers)}")
    print(f"wrote {len(layers)} layers to {a.out}/  (sheet {sheet_w:.0f} x {sheet_h:.0f} mm)")


if __name__ == "__main__":
    main()
