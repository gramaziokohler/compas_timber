"""Free contours with NURBS segments.

In BTLx a NURBS curve is not a processing of its own. It is one of the segment types a contour can be made
of, next to `Line` and `Arc` (see `NURBSCurveType` and `FreeContourType` in the BTLx 2.3.0 specification).
An arbitrarily shaped contour on a timber element is therefore a `FreeContour` whose contour is built from
`NurbsCurve` segments, optionally mixed with straight `Line` segments.

This example cuts

* a free-form aperture through a plate, from a single closed NURBS curve, and
* a lens shaped pocket into a beam, from a NURBS curve closed by a straight line,

writes the result to BTLx and shows it in the viewer.

Not every consumer implements the NURBS contour segment type. Lignocam's BtlViewer, for one, parses the
`NURBS` element but never assigns the segment an end point, so the contour collapses onto its start point
instead of failing outright. Pass `tessellate=True` to write the very same contour as straight segments,
which any consumer can read; the second file below does that.
"""

import os

from compas.colors import Color
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyline
from compas.tolerance import Tolerance
from compas_brep.curves import NurbsCurve
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.elements import Plate
from compas_timber.fabrication import BTLxWriter
from compas_timber.fabrication import FreeContour
from compas_timber.model import TimberModel

HERE = os.path.dirname(__file__)

PLATE_LENGTH = 600.0
PLATE_WIDTH = 400.0
PLATE_THICKNESS = 20.0

BEAM_LENGTH = 1200.0
BEAM_WIDTH = 120.0
BEAM_HEIGHT = 200.0
POCKET_DEPTH = 40.0


def create_viewer():
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [1200.0, -1400.0, 900.0]
    viewer.renderer.camera.target = [500.0, 100.0, 0.0]
    viewer.renderer.camera.pandelta = 0.01
    viewer.renderer.rendermode = "ghosted"
    return viewer


# ==============================================================================
# a plate with a free-form aperture cut from a single closed NURBS curve
# ==============================================================================

plate_outline = Polyline(
    [
        Point(0, 0, 0),
        Point(0, PLATE_WIDTH, 0),
        Point(PLATE_LENGTH, PLATE_WIDTH, 0),
        Point(PLATE_LENGTH, 0, 0),
        Point(0, 0, 0),
    ]
)
plate = Plate.from_outline_thickness(plate_outline, PLATE_THICKNESS)

# the control points close the loop, so the resulting curve is a closed contour.
# they live on the top face of the plate, which is how the reference side is found.
aperture_points = [
    Point(120, 80, 0),
    Point(300, 20, 0),
    Point(480, 80, 0),
    Point(540, 200, 0),
    Point(480, 320, 0),
    Point(300, 380, 0),
    Point(120, 320, 0),
    Point(60, 200, 0),
    Point(120, 80, 0),
]
aperture_curve = NurbsCurve.from_points(aperture_points, degree=3)

# interior=True removes the material inside the contour. Without an explicit depth the contour cuts
# all the way through the element.
plate.add_features([FreeContour.from_nurbs_curves_and_element(aperture_curve, plate, interior=True)])


# ==============================================================================
# a beam with a pocket cut from a NURBS curve closed by a straight line
# ==============================================================================

beam = Beam.from_centerline(Line(Point(0, -600, 0), Point(BEAM_LENGTH, -600, 0)), BEAM_WIDTH, BEAM_HEIGHT)

# the contour is laid out in the 2D coordinates of the reference side and then moved onto it, which keeps
# the numbers readable and guarantees the contour ends up flat on the face.
ref_side = beam.ref_sides[0]
to_ref_side = ref_side.to_transformation()

wave_points = [
    Point(200, 30, 0),
    Point(400, 150, 0),
    Point(600, -40, 0),
    Point(800, 150, 0),
    Point(1000, 30, 0),
]
wave = NurbsCurve.from_points(wave_points, degree=3).transformed(to_ref_side)
# a straight segment closes the contour, so the two segment types end up in the same BTLx <Contour>
closing_line = Line(Point(1000, 30, 0), Point(200, 30, 0)).transformed(to_ref_side)

beam.add_features(
    [
        FreeContour.from_nurbs_curves_and_element(
            [wave, closing_line],
            beam,
            depth=POCKET_DEPTH,
            interior=True,
        )
    ]
)


# ==============================================================================
# BTLx
# ==============================================================================

# the geometry is modelled in millimeters, so tell the model as much and BTLx will not rescale it
model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-6, relative=1e-6))
model.add_element(plate)
model.add_element(beam)

PATH = os.path.join(HERE, "nurbs_contour.btlx")
BTLxWriter().write(model, PATH)
print("wrote {}".format(PATH))


# the same two contours, written as straight segments for consumers without NURBS support
tessellated_plate = Plate.from_outline_thickness(plate_outline, PLATE_THICKNESS)
tessellated_plate.add_features([FreeContour.from_nurbs_curves_and_element(aperture_curve, tessellated_plate, interior=True, tessellate=True)])

tessellated_beam = Beam.from_centerline(Line(Point(0, -600, 0), Point(BEAM_LENGTH, -600, 0)), BEAM_WIDTH, BEAM_HEIGHT)
tessellated_beam.add_features([FreeContour.from_nurbs_curves_and_element([wave, closing_line], tessellated_beam, depth=POCKET_DEPTH, interior=True, tessellate=True)])

tessellated_model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-6, relative=1e-6))
tessellated_model.add_element(tessellated_plate)
tessellated_model.add_element(tessellated_beam)

TESSELLATED_PATH = os.path.join(HERE, "nurbs_contour_tessellated.btlx")
BTLxWriter().write(tessellated_model, TESSELLATED_PATH)
print("wrote {}".format(TESSELLATED_PATH))


# ==============================================================================
# visualization
# ==============================================================================

if __name__ == "__main__":
    viewer = create_viewer()

    for element in (plate, beam):
        viewer.scene.add(element.geometry)

    # draw the driving curves on top of the machined geometry
    for curve in (aperture_curve, wave):
        viewer.scene.add(curve.to_polyline(200), linewidth=3, linecolor=Color.red())
    viewer.scene.add(Polyline([closing_line.start, closing_line.end]), linewidth=3, linecolor=Color.red())

    viewer.show()
