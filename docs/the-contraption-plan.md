# Plan: *The Contraption* (1949) with a Just Eat twist

Size assumed: A3 image area (280 x 296 mm, the painting is nearly square),
20 mm margin, sheets 320 x 336 mm, 250 micron Mylar.

```bash
python3 tools/stencilgen.py input/contraption.jpg -o out --layers 4 --width-mm 280 --blur-mm 0.6
```

## Ground

Titanium white with a small amount of yellow ochre and a speck of ivory
black. Warm off-white, matte. Brush it on with visible strokes; Lowry's
grounds are not flat.

## Layer 1, light warm grey

Sky texture, the pavement, the pale left-hand terrace, the far street.
Expect big open regions with a few islands (window reflections). The tool
will bridge them. Spray a thin coat; this layer is mostly about breaking up
the ground.

## Layer 2, mid grey

Road surface, kerb line, the shadow side of the buildings, the small figure
and dog on the right, the roofline, chimney stacks. Bridges will go through
the roofline. Fine.

## Layer 3, dark grey

The rider's coat and trousers, the underside of the cab, the wheel hubs.
Small layer, quick to spray.

## Layer 4, black key layer

The cab, the wheel rims, the frame and pedals, the bowler hat, the man's
shoes, the signature and date. This is the layer that makes it Lowry.

Islands on this layer, all handled by the tool:

- the white square panel on the cab side (two bridges)
- the white disc inside each wheel rim (two bridges each, they read as spokes)
- the gap between the rider and the cab

Check the frame tubes. They are about 2 mm at A3 and right at the limit of
`--min-feature-mm`. If they vanish, lower it to 0.9 and use thicker Mylar,
or paint the frame by hand with a rigger brush, which is honestly easier.

## Hand colour, after the black layer

| element | mix |
|---|---|
| left terrace and right terrace | vermilion + white + ochre, scrubbed on thin |
| red door, left building | vermilion, a single dab |
| chimney pots | vermilion + ochre |
| coat and trousers | ochre + a little black, dry-brushed over layer 3 |
| face and hands | white + ochre + a touch of vermilion |
| wheel discs | pure white impasto, a small palette knife |
| sky and pavement | dry-brushed white over layer 1 to put the texture back |

## The twist

The white panel on the cab is a perfect logo panel. Cut the Just Eat logo as
a single extra stencil, sized to fit the panel with 3 mm clearance, on the
same 320 x 336 sheet with the same registration marks. Spray it in orange
(cadmium orange, or RGB 255 128 0) after everything else is dry.

Optional extras, each one more small stencil or a brush job:

- insulated courier bag on the rider's back in the same orange
- phone in a handlebar mount, painted black by hand
- the far-right figure carrying a takeaway bag in orange

One twist reads as wit. Three reads as clutter. Start with the panel.

## Sequence

1. ground, cure overnight
2. cut layers 1 to 4 and the logo
3. pin the registration jig
4. spray 1, 2, 3, 4, let each dry
5. peel, touch up bridge gaps in black
6. hand colour
7. spray the logo layer
8. matte varnish
