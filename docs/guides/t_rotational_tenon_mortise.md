# T-Rotational Tenon Mortise

`TRotationalTenonMortiseJoint` connects the end of a main beam to the side of a cross beam (T topology) with a hooked
tenon that is swung into its mortise by turning the main beam about an axis along it.

* The tenon lies in the main beam's cross section. It starts at the main beam's top or bottom face and hooks down and
  around the rotation axis, both its flanks being arcs around it.
* The mortise is the tenon's path out of the cross beam's face on the same side. So, like a dovetail, the joint goes
  together from the cross beam's top or bottom face.
* Once in, the hook keeps the tenon from being pulled straight out: the only way out is turning the main beam back
  about the same axis.
* The main beam may meet the cross beam at an angle. The axis still runs along the main beam, so the whole beam turns
  about one axis, and its end stays flush with the cross beam's slanted face.

## Getting it

Until it is released, the joint is on the `rotational-joints` branch. To use it in your own scripts, install that
branch into your Python environment:

```bash
pip install "compas_timber[viz] @ git+https://github.com/gramaziokohler/compas_timber.git@rotational-joints"
```

To also run the Joint Explorer (an example script, which is not installed with the package), clone the repository,
switch to the branch and install it from there instead:

```bash
git clone https://github.com/gramaziokohler/compas_timber.git
cd compas_timber
git checkout rotational-joints
pip install -e ".[viz]"
```

With `-e`, a later `git pull` brings in updates without installing again. The `viz` extra adds the COMPAS viewer the
explorer needs. With [uv](https://docs.astral.sh/uv/), `uv sync --extra viz` instead of `pip install -e ".[viz]"`.

!!! note
    You do not need to generate the protobuf files (`invoke generate-proto-classes`) for any of this. They are only
    used to exchange models in the protobuf format, through `compas_pb`, and are generated from the `.proto` files in
    `src/compas_timber/proto` rather than kept in git, for all joints alike. Only run that command if you use that
    format from a git checkout.

## Using it in a design

Create the joint between the main beam (the one with the tenon) and the cross beam, then let the model process the
joinery. Any parameter left out gets a default worked out from the beams.

```python
import math

from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Vector
from compas.tolerance import Tolerance

from compas_timber.connections import TRotationalTenonMortiseJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxWriter
from compas_timber.model import TimberModel

# a cross beam along x, and a main beam which meets its side at 70 degrees, both lying flat (z up)
cross_beam = Beam.from_centerline(Line(Point(-700, 0, 0), Point(700, 0, 0)), width=160, height=160)
direction = Vector(math.cos(math.radians(70)), math.sin(math.radians(70)), 0)
main_beam = Beam.from_centerline(Line(Point(0, 0, 0) + direction * 900, Point(0, 0, 0)), width=120, height=160)

model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3))  # BTLx is in mm
model.add_element(main_beam)
model.add_element(cross_beam)

joint = TRotationalTenonMortiseJoint.create(model, main_beam, cross_beam, rotation_radius=120.0)

errors = model.process_joinery()
for error in errors:
    print(error.debug_info)  # why a joint could not be made, and what to change

print("length:", round(joint.length, 1), "width:", joint.width, "height:", round(joint.height, 1))
print("swing out by", round(joint.release_angle, 1), "degrees about", joint.rotation_axis)

# the main beam turned out of the mortise, e.g. to check the assembly
axis = joint.rotation_axis
swung = main_beam.geometry.transformed(Rotation.from_axis_and_angle(axis.direction, math.radians(joint.release_angle), point=axis.start))

BTLxWriter().write(model, "rotational_joint.btlx")
```

The beams must lie in one plane, each with a face parallel to it: the main beam may meet the cross beam at any angle
in that plane, but not tilted out of it.

### Parameters

All lengths are in model units, measured in the main beam's cross section unless said otherwise. See the class
docstring (`help(TRotationalTenonMortiseJoint)`) for the details.

| Parameter | What it does | Default |
| --- | --- | --- |
| `start_y` | Position of the tenon across the main beam's face, from its centerline, away from the axis. The axis lies at `start_y - rotation_radius`. | centered, so the tenon stays within the main beam |
| `start_depth` | Depth below the main beam's face at which the tenon starts. | 0 (flush) |
| `rotation` | 0 or 180: which of the main beam's faces (top or bottom) the tenon starts from, and so which face of the cross beam the joint goes together from. | the side needing the least turn; if alike, from above |
| `length` | How deep the tenon reaches into the cross beam, along the main beam. | 3/4 of the cross beam's depth where deepest |
| `width` | Width of the tenon across its arcs (at its tip for a conical profile). | half the main beam's width |
| `height` | How far below its start the tenon reaches. | hooks the tip 45° around the axis |
| `tenon_shape` | Tip shape: `TenonShapeType.ROUND`, `SQUARE` or `RADIUS`. | ROUND |
| `shape_radius` | Corner radius of a `RADIUS` tip. | half `tool_diameter`, or `width / 4` |
| `rotation_radius` | Distance from the axis to the tenon's centerline: how tightly it curves. | the main beam's width |
| `axis_offset` | How far the axis lies above the start of the tenon. Positive raises it out of the main beam. | 0 |
| `profile` | `RotationalTenonProfile.PARALLEL` (equally wide all along) or `CONICAL` (tapers from `start_width` to `width`, both flanks moved off the axis). | PARALLEL |
| `start_width` | Width of a conical tenon where it starts. | 1.5 × `width` |
| `end_mill` | `EndMillType.FLAT` (walls square to the shoulder) or `DOVETAIL` (walls inclined by `tool_angle`, which also locks the main beam against being pulled back along its axis). | FLAT |
| `tool_angle` | Angle of the dovetail end mill, in degrees. | 15 |
| `tool_diameter` | Diameter of the end mill cutting the mortise. If given, the joint reports a mortise narrower than it, and tip corners tighter than it (a `SQUARE` tip cannot be milled at all). | not checked |

Once processed, the joint also gives:

* `rotation_axis`: the line the main beam turns about. Turning by a positive angle about it swings the tenon out.
* `release_angle`: the turn, in degrees, which brings the tenon all the way out of the cross beam.
* `return_angle`: the turn at which the tenon, swung on past `release_angle`, would come round to the cross beam again
  (None if it never does).

### Beams at an angle

* The rotation axis runs along the main beam, on the side of the acute angle.
* The main beam's end is flush with the cross beam's slanted face, and the tenon reaches out of it along the main beam
  to a square end, so it is longer on the side of the acute angle. `length` is measured from where the main beam's
  centerline meets the face.
* The mortise is exactly the tenon's shape: its walls follow the main beam, tilted to the face as with a conical tool,
  and its bottom is the tenon's square end.
* The axis must lie at or above the cross beam's face the joint goes together from (raise it with `axis_offset` if
  not), and the tenon must still reach past the face on the side of the obtuse angle (make `length` larger if not).

### When the joint cannot be made

`process_joinery()` returns the joints it could not make, and each error's `debug_info` says what to change. The most
common ones:

| Message (shortened) | What to do |
| --- | --- |
| The tenon reaches out of the side of the main beam | make it narrower or less high, or move it with `start_y` or `rotation_radius` |
| The tenon reaches out of the main beam's opposite face | make `start_depth` or `height` smaller |
| The tenon cannot be swung out of the cross beam | use a smaller `start_depth`, a larger `axis_offset` or `rotation_radius`, or the other `rotation` |
| For a main beam at an angle, the rotation axis must lie at or above the cross beam's face | raise the axis with `axis_offset` by the amount given |
| The tenon does not reach into the cross beam on the side of the obtuse angle | make `length` larger than the value given (for a dovetail, a smaller `tool_angle` or `start_width` may then be needed) |
| The mortise is narrower than the end mill | make the tenon wider or use a smaller tool |
| The beams must lie in one plane | the main beam is tilted out of the plane of both beams: this joint cannot connect them |

## Fabrication (BTLx)

Both the tenon and the mortise are `FreeContour` processings, with a `JackRafterCut` at the end of the tenon where the
main beam's blank reaches past it:

* Beams at 90°: the tenon is milled out of the main beam's end, the mortise into the cross beam's face, with exact
  NURBS arcs. If your CAM software does not read NURBS in a FreeContour, write the file with
  `BTLxWriter(tessellate=True)`, which turns the arcs into short straight segments.
* Beams at an angle: both are FreeContours of two contours (`DualContour`), the waste around the tenon from the main
  beam's end down to the slanted shoulder, and the mortise from the cross beam's face down to the tenon's square end.
  Their arcs are written as short straight segments.

!!! warning
    Check with your CAM software that it reads FreeContours with NURBS arcs and with two contours, the second of them
    on a tilted plane, before sending them to a machine.

## Joint Explorer

The Joint Explorer is an interactive playground for all joints of compas_timber. From the cloned repository, run:

```bash
python examples/model/0014_joint_explorer.py
```

Pick "T-Rotational Tenon Mortise" from the dropdown in the side dock, then:

* **Beams:** set the beams' sizes and the angle between them.
* **Joint parameters:** drag the sliders. Parameters marked "auto" are left to the joint, and the slider shows the
  value it picked; touch one to take it over, press "Reset joint parameters" to hand them back. Every change rebuilds
  the joint, so what you see is what the library produces, and a joint which cannot be made shows why.
* **Display:** the rotation axis is drawn in red, with the circle the tenon's centerline follows. The explode slider
  swings the main beam out about the axis instead of pulling it apart.
* **Copy code:** puts a script which rebuilds what is on screen, with all its parameters, on the clipboard. Paste it
  into your design to start from there.
