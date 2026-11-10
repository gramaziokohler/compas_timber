"""Butt and miter joints with user-defined cutting planes (`CutPlaneSpec`).

Ten examples laid out on a 5x2 grid, each with its custom plane(s) drawn in orange.
Convention: a cutting plane's normal points towards the material that is removed.

Butt planes must be parallel to the cross beam's centerline, back planes parallel to the
main beam's centerline. Miter planes can have any orientation.
"""

import math

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Rotation
from compas.geometry import Vector
from compas_viewer import Viewer
from compas_viewer.scene import Tag

from compas_timber.connections import CutPlaneSpec
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel

W, H = 80, 160  # beam cross-section
SPACING = 2200


def cell_offset(index):
    return Vector((index % 5) * SPACING, -(index // 5) * SPACING, 0)


def beam(start, end, offset):
    return Beam.from_centerline(Line(Point(*start) + offset, Point(*end) + offset), W, H)


def plane(point, normal, offset):
    return Plane(Point(*point) + offset, Vector(*normal))


def rotated_z(vector, degrees):
    return Vector(*vector).transformed(Rotation.from_axis_and_angle([0, 0, 1], math.radians(degrees)))


# Each example: (title, build) where build(model, offset) adds beams + joint and returns the custom planes.
# L/T butt layout: main beam runs +X from the joint, cross beam runs along Y. Cross beam faces are at x = +-W/2.


def l_butt_tilted(model, o):
    main, cross = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([main, cross])
    butt = plane((W / 2, 0, 0), (-1, 0, -0.5), o)  # slanted end in elevation
    LButtJoint.create(model, main, cross, butt_plane_spec=CutPlaneSpec.from_butt_plane(main, cross, butt))
    return [butt]


def l_butt_gap(model, o):
    main, cross = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([main, cross])
    butt = plane((W / 2 + 60, 0, 0), (-1, 0, 0), o)  # 60 mm gap, e.g. for a connector plate
    LButtJoint.create(model, main, cross, butt_plane_spec=CutPlaneSpec.from_butt_plane(main, cross, butt))
    return [butt]


def l_butt_back_tilted(model, o):
    main, cross = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([main, cross])
    back = plane((0, -W / 2, 0), (0, -1, 0.6), o)  # slanted overhang of the cross beam
    LButtJoint.create(model, main, cross, back_plane_spec=CutPlaneSpec.from_back_plane(main, cross, back))
    return [back]


def l_butt_angled_both(model, o):
    direction = rotated_z([1200, 0, 0], 30)  # main beam at 60 deg to the cross beam
    main, cross = beam((0, 0, 0), direction, o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([main, cross])
    butt = plane((W / 2, 0, 0), (-1, 0, 0.4), o)
    away_from_cross = main.frame.xaxis.cross([0, 0, 1])  # horizontal, perpendicular to main's axis
    back = Plane(Point(0, 0, 0) + o + away_from_cross * (W / 2), away_from_cross + Vector(0, 0, -0.5))
    LButtJoint.create(
        model,
        main,
        cross,
        butt_plane_spec=CutPlaneSpec.from_butt_plane(main, cross, butt),
        back_plane_spec=CutPlaneSpec.from_back_plane(main, cross, back),
    )
    return [butt, back]


def t_butt_tilted(model, o):
    main, cross = beam((0, 0, 0), (1200, 0, 0), o), beam((0, -600, 0), (0, 600, 0), o)
    model.add_elements([main, cross])
    butt = plane((W / 2, 0, 0), (-1, 0, 0.7), o)
    TButtJoint.create(model, main, cross, butt_plane_spec=CutPlaneSpec.from_butt_plane(main, cross, butt))
    return [butt]


def t_butt_rafter_plumb_cut(model, o):
    # main beam rises at 30 deg onto a horizontal cross beam, cut with a plumb (vertical) plane
    main = beam((0, 0, 0), (1000, 0, 1000 * math.tan(math.radians(30))), o)
    cross = beam((0, -600, 0), (0, 600, 0), o)
    model.add_elements([main, cross])
    butt = plane((W / 2 + 20, 0, 0), (-1, 0, 0), o)
    TButtJoint.create(model, main, cross, butt_plane_spec=CutPlaneSpec.from_butt_plane(main, cross, butt))
    return [butt]


# L-miter layout: beam_a runs +X, beam_b runs +Y, corner at the origin. The default miter is the bisector.


def l_miter_unequal(model, o):
    a, b = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([a, b])
    miter = plane((0, 0, 0), rotated_z([1, -1, 0], 15), o)  # 15 deg off the bisector
    LMiterJoint.create(model, a, b, miter_plane=CutPlaneSpec.from_plane(a, miter))
    return [miter]


def l_miter_3d_tilt(model, o):
    a, b = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), (0, 1200, 0), o)
    model.add_elements([a, b])
    miter = plane((0, 0, 0), (1, -1, 0.6), o)  # tilted out of the XY plane
    LMiterJoint.create(model, a, b, miter_plane=CutPlaneSpec.from_plane(a, miter))
    return [miter]


def l_miter_obtuse_square_cut(model, o):
    # beams at 120 deg, miter replaced by a cut square to beam_a
    a, b = beam((0, 0, 0), (1200, 0, 0), o), beam((0, 0, 0), rotated_z([1200, 0, 0], 120), o)
    model.add_elements([a, b])
    miter = plane((-W / 2, 0, 0), (1, 0, 0), o)
    LMiterJoint.create(model, a, b, miter_plane=CutPlaneSpec.from_plane(a, miter))
    return [miter]


def u_frame_shared_beam(model, o):
    # two custom miters on one beam: the left one extends its START, which used to shift the right plane
    bottom = beam((0, 0, 0), (1600, 0, 0), o)
    left = beam((0, 0, 0), (-300, 1500, 0), o)
    right = beam((1600, 0, 0), (1700, 1500, 0), o)
    model.add_elements([bottom, left, right])
    miter_left = plane((0, 0, 0), (1, -0.6, 0), o)  # a few degrees off the bisectors
    miter_right = plane((1600, 0, 0), (1, 0.7, 0), o)
    LMiterJoint.create(model, bottom, left, miter_plane=CutPlaneSpec.from_plane(bottom, miter_left))
    LMiterJoint.create(model, bottom, right, miter_plane=CutPlaneSpec.from_plane(bottom, miter_right))
    return [miter_left, miter_right]


EXAMPLES = [
    ("1 L-Butt: tilted butt plane", l_butt_tilted),
    ("2 L-Butt: 60 mm gap", l_butt_gap),
    ("3 L-Butt: tilted back plane", l_butt_back_tilted),
    ("4 L-Butt: angled beams, butt + back", l_butt_angled_both),
    ("5 T-Butt: tilted butt plane", t_butt_tilted),
    ("6 T-Butt: rafter plumb cut", t_butt_rafter_plumb_cut),
    ("7 L-Miter: 15 deg off bisector", l_miter_unequal),
    ("8 L-Miter: 3D tilted plane", l_miter_3d_tilt),
    ("9 L-Miter: 120 deg, square cut", l_miter_obtuse_square_cut),
    ("10 L-Miter: U-frame, shared beam", u_frame_shared_beam),
]


def build():
    model = TimberModel()
    planes, tags = [], []
    for index, (title, build_example) in enumerate(EXAMPLES):
        offset = cell_offset(index)
        planes.extend(build_example(model, offset))
        tags.append(Tag(title, Point(-300, -500, 0) + offset, height=60))
    model.process_joinery()
    return model, planes, tags


def plane_patch(plane, size=350):
    frame = Frame.from_plane(plane)
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    return Polygon([frame.point + frame.xaxis * (u * size) + frame.yaxis * (v * size) for u, v in corners])


if __name__ == "__main__":
    model, planes, tags = build()

    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [4000.0, -6000.0, 6000.0]
    viewer.renderer.camera.target = [4400.0, -1100.0, 0.0]
    viewer.renderer.camera.pandelta = 0.05

    for element in model.beams:
        viewer.scene.add(element.geometry, facecolor=Color.from_hex("#d9b38c"), linecolor=Color.grey().darkened(50))
    for cut_plane in planes:
        viewer.scene.add(plane_patch(cut_plane), facecolor=Color.orange(), linecolor=Color.orange(), opacity=0.4)
    for tag in tags:
        viewer.scene.add(tag)

    viewer.show()
