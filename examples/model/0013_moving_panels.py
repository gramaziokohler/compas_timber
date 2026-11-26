"""Animated panels: the two cache tiers of an element.

A floor panel spins while a wall panel, its child, folds up and down. The wall's timber frame (beams joined
with miter and butt joints, two of them with custom cutting planes) are children of the wall, placed in its
local coordinates. Joinery is processed once, before the animation.

Every frame only the two panels' `transformation` is set. The beams then show the two cache tiers:

* element tier: the beam's geometry with its joint cuts, in local coordinates. It doesn't depend on where the
  beam is, so it is computed once and added to the viewer once.
* model tier: the beam's model transformation, composed from its ancestors' transformations. Moving a panel
  clears it for the whole subtree, so it is recomputed every frame and only the scene objects' transformation
  is updated.

The status bar counts how often each tier is computed. The custom cutting planes (orange) are stored relative
to their beam (`CutPlaneSpec`), so they follow it as well.
"""

import math

from compas.colors import Color
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polygon
from compas.geometry import Rotation
from compas.geometry import Translation
from compas.geometry import Vector
from compas_viewer import Viewer

from compas_timber.connections import CutPlaneSpec
from compas_timber.connections import LButtJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import TButtJoint
from compas_timber.elements import Beam
from compas_timber.elements import Panel
from compas_timber.model import TimberModel

W, H = 80, 160  # beam cross-section, H is the wall's thickness
L, B = 2400, 2600  # wall size
FLOOR = 3000
HINGE = Point(300, 300, 200)  # the wall's bottom edge, in floor coordinates
CENTER = Vector(FLOOR / 2, FLOOR / 2, 0)


def floor_transformation(t):
    """Spin the floor around its center."""
    return Translation.from_vector(CENTER) * Rotation.from_axis_and_angle([0, 0, 1], t * 2 * math.pi / 3) * Translation.from_vector(-CENTER)


def wall_transformation(t):
    """Fold the wall up from lying on the floor (0 deg) to standing (90 deg), relative to the floor."""
    angle = math.radians(90) * 0.5 * (1 - math.cos(t * 2 * math.pi))
    return Translation.from_vector(HINGE) * Rotation.from_axis_and_angle([1, 0, 0], angle)


def build():
    model = TimberModel()
    floor = Panel(Frame.worldXY(), FLOOR, FLOOR, 200, name="floor")
    wall = Panel(Frame.worldXY(), L, B, H, name="wall")
    model.add_element(floor)
    model.add_element(wall, parent=floor)
    floor.transformation = floor_transformation(0)
    wall.transformation = wall_transformation(0)

    # the wall's frame, in its local coordinates
    x0, x1, y0, y1, z = W / 2, L - W / 2, W / 2, B - W / 2, H / 2

    def beam(start, end):
        element = Beam.from_centerline(Line(Point(*start, z), Point(*end, z)), W, H, z_vector=Vector(0, 0, 1))
        model.add_element(element, parent=wall)
        return element

    bottom, right = beam((x0, y0), (x1, y0)), beam((x1, y0), (x1, y1))
    top, left = beam((x1, y1), (x0, y1)), beam((x0, y1), (x0, y0))
    stud = beam((L / 2, y0), (L / 2, y1))

    # custom planes are given in the wall's coordinates and placed in the world, as a user would pick them
    to_world = wall.modeltransformation
    miter = Plane(Point(x1, y1, z), Vector(1, -1, 0).rotated(math.radians(20), [0, 0, 1])).transformed(to_world)
    butt = Plane(Point(L / 2, y1 - W / 2, z), Vector(0, -1, 0.6)).transformed(to_world)
    miter_spec = CutPlaneSpec.from_plane(right, miter)
    butt_spec = CutPlaneSpec.from_butt_plane(stud, top, butt)

    LMiterJoint.create(model, bottom, left)
    LButtJoint.create(model, right, bottom)
    LMiterJoint.create(model, right, top, miter_plane=miter_spec)
    LButtJoint.create(model, top, left)
    TButtJoint.create(model, stud, bottom)
    TButtJoint.create(model, stud, top, butt_plane_spec=butt_spec)

    model = json_loads(json_dumps(model))  # the hierarchy and the custom planes survive serialization
    model.process_joinery()
    spec_beams = [(model[str(right.guid)], miter_spec), (model[str(top.guid)], butt_spec)]
    return model, spec_beams


def pose(model, t):
    """Move the two panels. Nothing else is touched."""
    panels = {panel.name: panel for panel in model.panels}
    panels["floor"].transformation = floor_transformation(t)
    panels["wall"].transformation = wall_transformation(t)


def plane_patch(frame, size=250):
    """A square around the plane's origin, in the same coordinates as `frame`."""
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    return Polygon([frame.point + frame.xaxis * (u * size) + frame.yaxis * (v * size) for u, v in corners])


def count_calls(cls, name, counts):
    original = getattr(cls, name)

    def counted(self, *args, **kwargs):
        counts[name] += 1
        return original(self, *args, **kwargs)

    setattr(cls, name, counted)


if __name__ == "__main__":
    counts = {"compute_elementgeometry": 0, "compute_modeltransformation": 0}
    count_calls(Beam, "compute_elementgeometry", counts)
    count_calls(Beam, "compute_modeltransformation", counts)

    model, spec_beams = build()
    beams = list(model.beams)

    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [6500.0, -5500.0, 5000.0]
    viewer.renderer.camera.target = [1500.0, 1500.0, 800.0]
    viewer.renderer.camera.pandelta = 0.05

    # each piece of geometry is added once, in its element's local coordinates (element tier) ...
    objects = []
    for panel in model.panels:
        color = Color.from_hex("#b7b7b7") if panel.name == "floor" else Color.from_hex("#9fb8c9")
        objects.append((panel, viewer.scene.add(panel.elementgeometry, facecolor=color, opacity=0.35)))
    for beam in beams:
        objects.append((beam, viewer.scene.add(beam.elementgeometry, facecolor=Color.from_hex("#d9b38c"), linecolor=Color.grey().darkened(50))))
    for beam, spec in spec_beams:
        patch = plane_patch(spec.local_frame)
        objects.append((beam, viewer.scene.add(patch, facecolor=Color.orange(), linecolor=Color.orange(), opacity=0.5)))
    setup = dict(counts)

    @viewer.on(interval=30)
    def animate(frame):
        pose(model, frame / 240)
        # ... and only its placement is updated (model tier)
        for element, obj in objects:
            obj.transformation = element.modeltransformation
            obj.update()
        viewer.ui.statusbar.widget.showMessage(
            "frame {}  |  {} beams  |  element tier, geometry with joint cuts computed: {} times ({} before the animation)  |  "
            "model tier, model transformation computed: {} times".format(
                frame, len(beams), counts["compute_elementgeometry"], setup["compute_elementgeometry"], counts["compute_modeltransformation"]
            )
        )

    viewer.show()
