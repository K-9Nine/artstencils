# Method: Lowry by stencil and airbrush

Kit assumed: laser cutter, airbrush, acrylics, brushes, a board or heavy paper,
Inkscape or LightBurn (both free enough), `tools/stencilgen.py`.

## 1. Choose and prepare the image

- Work from the best reproduction you can find. Crop to the composition you
  want and straighten it. Keep the signature if you want it, it is a nice
  last black-layer detail.
- Decide the physical size first. Stencils get flimsy above A3 in Mylar, so
  for anything bigger tile the image or move to 300 micron sheet. A3 image
  area with a 20 mm margin is a 340 x 460 mm sheet, which fits most desktop
  lasers.
- Lowry's canvases have visible texture. Blur it out (`--blur-mm 0.4` to
  `0.8`) so the tonal split follows shapes, not brush marks. You will put the
  texture back by hand.

## 2. Decide the layer plan

Tonal mode (default) is right for Lowry. The tool picks tones by k-means,
but sanity-check the previews:

- **Ground**: the painted base coat, the lightest tone. Not a stencil.
- **Layer 1, light grey**: sky texture, pavement, distant buildings.
- **Layer 2, mid grey**: road, building faces, shadows.
- **Layer 3, dark grey**: coat, cab shadow, figures in the distance.
- **Layer 4, black key layer**: outlines, cab, wheels, hat, signature.

Four layers plus ground is the sweet spot. Five if the image has a lot of
mid-tone. Above that, registration errors and bridge marks start to outweigh
the extra tone. Colour mode (`--mode colour`) is worth trying for the pinks
and ochres, but for Lowry those areas are big, flat and few, so a brush does
them faster and looks better.

## 3. Generate and tidy the cut files

```bash
python3 tools/stencilgen.py input/painting.jpg -o out --layers 4 --width-mm 280 --margin-mm 20
```

Then open every SVG in Inkscape and check:

- **Bridges**. The tool joins every island with two bridges. Move or delete
  the ones that land somewhere ugly and add your own where a shape wants it.
  Lowry outlines are wobbly so a bridge mark is easily lost. Bridges 2 to 3 mm
  wide hold up in Mylar; 1.5 mm is the floor.
- **Thin sheet between cut regions**. Anything under 1.5 mm will lift and
  let paint under. Either widen the gap or merge the two cut regions.
- **Noise**. Delete any speck you would not want to spray. `--min-area-mm2`
  raises the automatic threshold.
- **Registration marks** must be present and unchanged on every file.

Kerf: run a test card first. Cut a 10 mm square and measure it. If it comes
out at 10.3 mm, that is 0.15 mm kerf per side and thin features will be
0.3 mm thinner than drawn. Rerun with `--kerf-mm 0.15` if it matters.

## 4. Cut

Material:

| material | notes |
|---|---|
| 190 to 250 micron Mylar (polyester) | the standard. Reusable, cleans with water, does not swell when sprayed, cuts cleanly |
| 300 micron Mylar | for A2 and up, or many reuses |
| 220 gsm card | one-off pieces or tests. Swells if you flood it |
| oiled manila | traditional, handles nicely, cuts with a bit of smoke |

**Diode lasers (Ortur, xTool D1, Atomstack and similar):** blue light goes
straight through clear Mylar, so it will not cut. Use 220 to 300 gsm kraft
or grey card, oiled manila, or opaque blue/black "diode-safe" stencil film.
White card reflects blue light and needs more passes. Put a sacrificial
sheet under the work, tape every edge down, use air assist if you have it,
and stay with the machine: an open frame and card is a fire waiting for a
lifted corner. Starting points in mm/min, one 10 mm test square first:
5 W optical 300 mm/min at 90 % two passes; 10 W 600 mm/min at 80 % one
pass; 20 W 1200 mm/min at 70 % one pass, all for 220 gsm kraft card.

Never cut PVC or anything that says "vinyl" without checking. Chlorinated
plastics release chlorine gas in a laser and wreck the machine and you. Mylar
and PET are fine.

Settings: high speed, low power, one pass. On a 40 to 60 W CO2, something
like 30 mm/s at 12 to 18 % is the ballpark for 250 micron Mylar. Cut a small
test grid first. You want the cut to just part, not flare. Cut on a honeycomb
bed or on a sheet of card so the backside does not get flashback. Cut the blue
registration marks as through-cuts on every layer. Cut the red image last so
the sheet stays flat while the marks are cut.

Putting every layer in the same place: tape an L-shaped corner stop to the
bed (front-left on a GRBL machine like an Ortur). In LightBurn set Start
From to Absolute Coords, drag the first layer so its green outline sits a
few mm inside the stop, and note the X/Y. Put every other layer at the same
X/Y. Then push each card into the stop, tape the edges, frame, and cut.
The card does not need to be centred; the marks land in the same place on
every sheet because the sheet is in the same place and the file is too.

Order of operations in LightBurn: registration (blue) then cut (red). Delete
the green outline and the grey image box or set them to no output.

## 5. Register

Because every layer has the same sheet size and marks, you only need one jig:

1. Paint the board with the ground and let it cure.
2. Tape layer 1 to the board where you want it.
3. Push pins, or dots of pencil, through the four registration crosshairs
   onto the board.
4. Every subsequent layer drops onto the same four pins or marks.

Two pushpins through the top marks plus a pencil dot at the bottom is enough.
Or glue small L-shaped stops to the board at two corners of the sheet and
push each stencil into the corner.

## 6. Spray

Airbrush setup:

- 0.3 to 0.5 mm needle. 0.5 is more forgiving with acrylic.
- 15 to 25 psi. Lower pressure means less paint driven under the stencil.
- Paint: airbrush-ready acrylics (Golden High Flow, Createx, Vallejo Air) or
  heavy body acrylics thinned with airbrush medium to milk consistency.
- Spray straight down, perpendicular to the board. Angled spray drives paint
  under the edge.
- Light passes. Two or three thin passes beat one wet one every time.

Holding the stencil flat:

- Repositionable spray adhesive (3M 75 or Krylon Easy-Tack) misted on the
  back, let it go tacky for a minute, press down. Clean Mylar with water.
- Or low-tack tape and a hand on the sheet. Fine for big shapes, poor for
  wheels and lettering.

Order: layer 1 is the lightest grey, layer N is black. Let each layer dry
before the next (a hairdryer on cool is fine). Peel each stencil straight up.

Mix the greys from Lowry's palette, not from a tube grey. Ivory black plus
flake (titanium) white, with a touch of ochre for warmth in the light greys
and a touch of Prussian blue in the darks. The composite preview gives the
target values per layer; `report.json` has the RGB numbers.

## 7. Colour by hand

This is where it becomes a painting rather than a print. Lowry's palette:

| colour | where it goes in *The Contraption* |
|---|---|
| flake white | sky and ground highlights, impasto on the wheel discs |
| ivory black | touch up outlines where bridges left gaps |
| vermilion | the red door, chimney pots, a hint on the lips |
| Prussian blue | in the greys, never straight |
| yellow ochre | the coat and trousers, warmth in the buildings and pavement |

Pink buildings are vermilion plus white plus a little ochre. Flesh is white,
ochre and a touch of vermilion. Work with a bristle brush and a bit of scrub
so the paint has the same dry, chalky quality as the ground. Dry-brush white
over the sky and pavement to put back the texture the stencils flattened.

Fill bridge gaps last. A wobbly hand-painted outline over a stencilled black
layer reads as a painting, not a mistake.

## 8. The contemporary twist

Keep it to one or two things. Ideas that fit this painting:

- The blank white panel on the cab is a ready-made billboard. That is where
  the Just Eat logo goes.
- Swap the cab for a courier box. Same silhouette, add the logo.
- Insulated delivery bag on the rider's back, phone in a handlebar mount.
- The figure on the far right with the dog carries a takeaway bag.
- A single stencilled line of text on the pavement: "Out for delivery".

Making the logo stencil:

1. Get the logo as a vector (SVG) or a large clean PNG.
2. In Inkscape: Path > Trace Bitmap if PNG, then Path > Object to Path,
   Path > Union so it is one shape.
3. Letters with counters (e, a, o) are islands. Draw 2 mm bridges by hand or
   run the PNG through the tool with `--layers 1 --mode tone`.
4. Set it to the same sheet size with the same registration marks: copy the
   `registration` and `sheet-outline` groups out of any generated layer.
5. Cut it, spray it last in brand colour (Just Eat orange is roughly
   RGB 255 128 0, close to cadmium orange).

On the logo itself: for a one-off artwork or a print run you keep for
yourself, using a trademark is normal parody and commentary. If you plan to
sell prints, keep the logo clearly part of a wider satire and do not use it in
the title or marketing, where it would look like an endorsement.

## 9. Finish

Matte varnish only. Lowry is dead flat and a gloss varnish will kill it.

## Troubleshooting

| problem | fix |
|---|---|
| paint under the stencil edge | lower pressure, thinner passes, spray more perpendicular, more adhesive |
| thin bits of stencil curling | raise `--min-feature-mm`, add bridges, use thicker Mylar |
| bridges showing in the result | fill by hand with a brush, or narrow to 2 mm |
| layers not lining up | cut the registration marks first and on every layer; check the sheet has not been trimmed |
| edge halo of overspray | mask the margin with paper; tape the sheet edge down |
| the split puts the sky and the road in the same layer | change `--seed`, raise `--layers`, or edit the mask PNG and re-trace in Inkscape |
