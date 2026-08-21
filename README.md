# Viola da gamba fingerboard jig

A parametric build123d model for a 3D-printed planing jig. The default cradle
is 256 mm long, tapers from 42 mm at the nut to 62 mm at the bridge end, and
has a constant 55 mm transverse radius.

The printed jig is 250 mm long to fit a Bambu Lab P1S build plate with margin.
The 256 mm fingerboard is centred and overhangs each open end by 3 mm.

The model assumes the curved face of the fingerboard sits down in the concave
cradle while its opposite face is planed. There are no raised end stops or side
lips. The outside vice block has parallel sides and a flat 30 mm height; only
the tapered cylindrical support rises above it. Foam can therefore be left
oversized and hang over the support edges. Dimensions are in millimetres.

The default hard cradle has a 60 mm radius so that a uniform 5 mm foam lining
leaves a 55 mm exposed radius for the fingerboard. The viewer shows the printed
jig, foam, and a nominal fingerboard as separate objects. The ghost
fingerboard's curved face and outline are exact; its editable 6 mm edge
thickness is illustrative because the face being planed has not been measured.

## Generate and preview

```sh
uv sync --extra viewer
source .venv/bin/activate
python fingerboard_jig.py --show
```

This exports `build/fingerboard_jig.stl` and `build/fingerboard_jig.step`, then
sends the model to the OCP CAD Viewer. The orange translucent shape is the
volume removed for the fingerboard.

Every important dimension is a command-line parameter. For example:

```sh
python fingerboard_jig.py --radius 60 --clearance 0.35 --show
```

Run `python fingerboard_jig.py --help` for all options.

The default outside size is about 250 x 78.5 x 38.7 mm. There is at least
30 mm of material below every point of the cradle for clamping in a vice. Check
the printer bed before slicing; a split-and-keyed version can be added once the
cradle fit and preferred print orientation are confirmed.
