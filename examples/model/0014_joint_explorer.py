"""Joint explorer: pick a joint type and play with its design parameters.

An interactive playground for the beam joints of compas_timber, in the COMPAS viewer. Pick a joint from the dropdown
in the side dock and drag the sliders. Every change rebuilds the beams, creates the joint with the current parameters
and runs `process_joinery()` again, so what you see is exactly what the library produces.

* Beams: the cross-sections of the beams and how they meet (angle, tilt, offset), depending on the joint's topology.
* Joint parameters: the arguments of the joint's constructor. Parameters marked "auto" are left to the joint, which
  derives them from the beams; the slider shows the value it picked. Touch the slider to take over, press
  "Reset joint parameters" to hand them back.
* Display: pull the beams apart to look inside the joint, ghost the uncut blanks, show the centerlines. Exploding
  moves each piece along the direction it is inserted in, which the explorer derives per joint type from the joint's
  own cuts (see "Insertion directions" below). A rotational tenon is swung out about its rotation axis instead, which
  is drawn in red, with the circle the tenon's centerline follows.
* "Copy code" puts a script that rebuilds the current state on the clipboard (and prints it).

Needs the `viz` extras (``pip install -e ".[viz]"``). Run with::

    python examples/model/0014_joint_explorer.py

"""

import math
import time

from compas.colors import Color
from compas.geometry import Circle
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Rotation
from compas.geometry import Sphere
from compas.geometry import Translation
from compas.geometry import Vector
from compas_viewer import Viewer
from compas_viewer.components import Button
from compas_viewer.components import Slider
from compas_viewer.components.booleantoggle import BooleanToggle
from compas_viewer.components.boundcomponent import BoundComponent
from compas_viewer.components.component import Component
from compas_viewer.components.container import Container
from compas_viewer.config import Config
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QSlider

from compas_timber.connections import BallNodeJoint
from compas_timber.connections import EndMillType
from compas_timber.connections import ISimpleScarf
from compas_timber.connections import LButtJoint
from compas_timber.connections import LFrenchRidgeLapJoint
from compas_timber.connections import LLapJoint
from compas_timber.connections import LMiterJoint
from compas_timber.connections import LTenonMortiseJoint
from compas_timber.connections import RotationalTenonProfile
from compas_timber.connections import TBirdsmouthJoint
from compas_timber.connections import TButtJoint
from compas_timber.connections import TDovetailJoint
from compas_timber.connections import TLapJoint
from compas_timber.connections import TRotationalTenonMortiseJoint
from compas_timber.connections import TStepJoint
from compas_timber.connections import TTenonMortiseJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import XNotchJoint
from compas_timber.connections import YButtJoint
from compas_timber.elements import Beam
from compas_timber.fabrication import StepShapeType
from compas_timber.fabrication import TenonShapeType
from compas_timber.model import TimberModel

# ==========================================================================
# Parameters
# ==========================================================================


class Param(object):
    """A design parameter, shown as one widget in the side dock.

    Parameters
    ----------
    name : str
        The keyword argument of the joint's constructor (or the name of a beam setting).
    label : str
        The text next to the widget.
    kind : str
        One of "float", "int", "bool" or "choice".
    default : float | int | bool | str | None
        The starting value. None means "auto": the argument is left out and the joint derives it from the beams.
    minimum, maximum, step : float
        The range of a slider.
    choices : list(str), optional
        The options of a "choice" parameter.
    zero_is_none : bool
        If True, a value of 0 is passed to the joint as None (e.g. "no drill hole").

    """

    def __init__(self, name, label, kind="float", default=None, minimum=0.0, maximum=100.0, step=1.0, choices=None, zero_is_none=False):
        self.name = name
        self.label = label
        self.kind = kind
        self.default = default
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.choices = choices or []
        self.zero_is_none = zero_is_none

    @property
    def is_auto(self):
        return self.default is None

    @property
    def placeholder(self):
        """A value for the widget before the joint has resolved an "auto" parameter."""
        if self.kind == "choice":
            return self.choices[0]
        return max(self.minimum, min(self.maximum, 0.0))

    def to_argument(self, value):
        """Converts the widget's value into the argument passed to the joint."""
        if self.kind == "int":
            value = int(round(value))
        elif self.kind == "float":
            value = float(value)
        if self.zero_is_none and not value:
            return None
        return value


def length(name, label, maximum, minimum=0.0, default=None, step=1.0, **kwargs):
    return Param(name, label + " [mm]", "float", default, minimum, maximum, step, **kwargs)


def angle(name, label, minimum, maximum, default=None, step=1.0):
    return Param(name, label + " [deg]", "float", default, minimum, maximum, step)


def integer(name, label, minimum, maximum, default):
    return Param(name, label, "int", default, minimum, maximum, 1)


def toggle(name, label, default=False):
    return Param(name, label, "bool", default)


def choice(name, label, choices, default=None):
    return Param(name, label, "choice", default, choices=choices)


TENON_SHAPES = [TenonShapeType.AUTOMATIC, TenonShapeType.SQUARE, TenonShapeType.ROUND, TenonShapeType.ROUNDED, TenonShapeType.RADIUS]
STEP_SHAPES = [StepShapeType.STEP, StepShapeType.HEEL, StepShapeType.TAPERED_HEEL, StepShapeType.DOUBLE]

# the joints fall back to their default when given 0 for most of these, hence the minimum of 1
TENON = [
    length("start_y", "Start y", minimum=-100.0, maximum=100.0),
    length("start_depth", "Start depth", 100.0),
    angle("rotation", "Rotation", -89.0, 89.0),
    length("length", "Tenon length", 400.0, minimum=1.0),
    length("width", "Tenon width", 200.0, minimum=1.0),
    length("height", "Tenon height", 200.0, minimum=1.0),
    choice("tenon_shape", "Tenon shape", TENON_SHAPES),
    length("shape_radius", "Shape radius", 100.0),
]

DOVETAIL = [
    length("start_y", "Start y", minimum=-100.0, maximum=100.0),
    length("start_depth", "Start depth", 100.0),
    angle("rotation", "Rotation", -60.0, 60.0),
    length("length", "Dovetail length", 300.0, minimum=1.0),
    length("width", "Dovetail width", 150.0, minimum=1.0),
    angle("cone_angle", "Cone angle", 1.0, 20.0),
    choice("dovetail_shape", "Dovetail shape", TENON_SHAPES),
    angle("tool_angle", "Tool (flank) angle", 5.0, 25.0),
    length("tool_diameter", "Tool diameter", 100.0, minimum=1.0),
    length("tool_height", "Tool height", 80.0, minimum=1.0),  # must stay below what the dovetail's width allows
]

LAP = [
    toggle("flip_lap_side", "Flip lap side"),
    Param("cut_plane_bias", "Cut plane bias", "float", 0.5, 0.05, 0.95, 0.05),
]

MILL_DEPTH = length("mill_depth", "Mill depth", 60.0, default=0.0)

# with a mill depth, mill a pocket that follows the main beam instead of a lap square to the cross beam
POCKET = [toggle("force_pocket", "Force pocket"), toggle("conical_tool", "Conical tool")]

# the parameters of a mortise and tenon, plus those of the rotation
ROTATIONAL_TENON = [
    length("start_y", "Start y", minimum=-150.0, maximum=150.0),
    length("start_depth", "Start depth (and axis)", 100.0),
    Param("rotation", "Rotation (side) [deg]", "float", None, 0.0, 180.0, 180.0),
    length("length", "Tenon length (into cross beam)", 400.0, minimum=1.0),
    length("width", "Tenon width", 200.0, minimum=1.0),
    length("height", "Tenon height (hook reach)", 300.0, minimum=1.0),
    choice("tenon_shape", "Tip shape", TENON_SHAPES),
    length("shape_radius", "Tip corner radius (radius tip)", 100.0, minimum=1.0),
    length("rotation_radius", "Rotation axis radius", 400.0, minimum=1.0),
    length("axis_offset", "Axis offset (above the start)", minimum=-150.0, maximum=150.0),
    choice("profile", "Profile", [RotationalTenonProfile.PARALLEL, RotationalTenonProfile.CONICAL]),
    length("start_width", "Start width (conical)", 300.0, minimum=1.0),
    choice("end_mill", "End mill", [EndMillType.FLAT, EndMillType.DOVETAIL]),
    angle("tool_angle", "Tool angle (dovetail)", 1.0, 30.0),
    length("tool_diameter", "Tool diameter (0 = not checked)", 100.0, default=0.0, zero_is_none=True),
]


# ==========================================================================
# Insertion directions
# ==========================================================================
# The joints don't define how their pieces go together (yet), so the explorer derives an insertion direction per
# joint type from the joint's own cuts, and exploding moves the pieces out along it, i.e. it plays the assembly
# backwards. Every rule was checked for collisions at several angles: moving the pieces apart along it never makes
# them overlap. Each rule maps an element of the joint to how it moves out: a direction it slides in, or a `Swing`
# about an axis; elements left out stay put. `away` maps each beam to the direction along its own axis that points
# away from the joint.


def unit(vector):
    return vector.unitized() if vector.length > 1e-9 else vector


class Slide(object):
    """Moves an element along a direction, by the explode distance."""

    def __init__(self, direction):
        self.direction = unit(direction)

    def at(self, distance):
        return Translation.from_vector(self.direction * distance)


class Swing(object):
    """Rotates an element about an axis, by the angle at which a point at `radius` from the axis travels the explode
    distance, up to `max_angle` degrees."""

    def __init__(self, axis, radius, max_angle=90.0):
        self.axis = axis
        self.radius = radius
        self.max_angle = math.radians(max_angle)

    def at(self, distance):
        angle = min(distance / self.radius, self.max_angle)
        return Rotation.from_axis_and_angle(self.axis.direction, angle, point=self.axis.start)


def about_the_rotation_axis(joint, away):
    """Rotational tenon: the main beam turns about the joint's rotation axis, which runs along it, and the tenon swings
    out of the cross beam's face following its arcs. It stops well past the turn which brings the tenon out, but
    before the tenon comes round to the cross beam again."""
    max_angle = joint.release_angle + 60.0
    if joint.return_angle is not None:
        max_angle = min(max_angle, joint.return_angle - 5.0)
    return {joint.main_beam: Swing(joint.rotation_axis, joint.rotation_radius, max_angle=max_angle)}


def along_main_axis(joint, away):
    """Butt and step joints: the main beam slides out along its own axis."""
    main = joint.elements[0]
    return {main: away[main]}


def off_the_cross_face(joint, away):
    """Tenons: the tenon is square to the cross beam's face at any angle between the beams, so it comes out along that face's normal."""
    return {joint.main_beam: joint.cross_beam.ref_sides[joint.cross_beam_ref_side_index].normal}


def apart_from_the_lap(joint, away):
    """Laps: both beams move off the lap, along the normal of beam b's lap face."""
    beam_a, beam_b = joint.elements
    normal = beam_b.ref_sides[joint.ref_side_index_b].normal
    return {beam_a: normal, beam_b: -normal}


def out_of_the_dovetail(joint, away):
    """Dovetail: the tenon slides out through the open face of the dovetail mortise; pulling it along the main beam is what a dovetail prevents."""
    return {joint.main_beam: joint.main_beam.ref_sides[joint.main_beam_ref_side_index].normal}


def off_the_seat(joint, away):
    """Birdsmouth: the rafter lifts off both faces of the cross beam it sits on."""
    normal = Vector(0, 0, 0)
    for index in joint.cross_ref_side_indices:
        normal += joint.cross_beam.ref_sides[index].normal
    return {joint.main_beam: normal}


def out_of_the_notch(joint, away):
    """Notch: the notched beam lifts off the solid beam, away from the face the notch is cut into."""
    normal = joint.notch_beam.ref_sides[joint.main_ref_side_index].normal
    return {joint.notch_beam: -normal, joint.solid_beam: normal}


def apart_from_the_scarf(joint, away):
    """Scarf: the two halves separate across the scarf, along the normal of the main beam's reference side."""
    normal = joint.main_beam.ref_sides[joint.main_beam_ref_side_index].normal
    return {joint.main_beam: normal, joint.cross_beam: -normal}


class JointSpec(object):
    """A joint type offered in the explorer.

    Parameters
    ----------
    name : str
        The name in the dropdown.
    cls : type
        The joint class.
    topology : str
        One of "L", "T", "X", "I" or "Y": how the beams are laid out.
    params : list(:class:`Param`)
        The arguments of the joint's constructor that get a widget.
    beams : dict, optional
        Overrides of the beam settings this joint needs to work (e.g. a step joint needs an inclined strut).
    roles : tuple(str), optional
        The names of the beams, in the order the joint takes them.
    insertion : callable, optional
        One of the insertion rules above, used to explode the joint. Without one, the beams move apart along their
        own axes.

    """

    def __init__(self, name, cls, topology, params=(), beams=None, roles=("main_beam", "cross_beam"), insertion=None):
        self.name = name
        self.cls = cls
        self.topology = topology
        self.params = list(params)
        self.beams = beams or {}
        self.roles = roles
        self.insertion = insertion

    @property
    def description(self):
        """The first paragraph of the joint's docstring."""
        doc = (self.cls.__doc__ or "").strip()
        return " ".join(line.strip() for line in doc.split("\n\n")[0].splitlines())


AB = ("beam_a", "beam_b")

JOINTS = [
    # LButtJoint passes force_pocket and conical_tool on to ButtJoint through its **kwargs
    JointSpec("L-Butt", LButtJoint, "L", [MILL_DEPTH, toggle("modify_cross", "Modify cross beam", True)] + POCKET, insertion=along_main_axis),
    JointSpec("L-Miter", LMiterJoint, "L", [toggle("cutoff", "Cutoff"), toggle("ref_side_miter", "Miter on ref. sides"), toggle("clean", "Cleaning cuts")], roles=AB),
    JointSpec("L-Lap", LLapJoint, "L", LAP, roles=AB, insertion=apart_from_the_lap),
    JointSpec(
        "L-French Ridge Lap",
        LFrenchRidgeLapJoint,
        "L",
        [LAP[0], length("drillhole_diam", "Drill hole diameter", 40.0, default=0.0, zero_is_none=True)],
        roles=AB,
        insertion=apart_from_the_lap,
    ),
    JointSpec("L-Tenon Mortise", LTenonMortiseJoint, "L", [toggle("modify_cross", "Modify cross beam")] + TENON, insertion=off_the_cross_face),
    JointSpec("T-Butt", TButtJoint, "T", [MILL_DEPTH] + POCKET, insertion=along_main_axis),
    # with the main beam tilted, no straight move takes a T-Lap apart: each notch is cut square to its own beam
    JointSpec("T-Lap", TLapJoint, "T", LAP, insertion=apart_from_the_lap),
    JointSpec("T-Birdsmouth", TBirdsmouthJoint, "T", [MILL_DEPTH], beams={"tilt": 30.0}, insertion=off_the_seat),
    JointSpec("T-Dovetail", TDovetailJoint, "T", DOVETAIL, insertion=out_of_the_dovetail),
    JointSpec(
        "T-Step",
        TStepJoint,
        "T",
        [
            choice("step_shape", "Step shape", STEP_SHAPES, default=StepShapeType.STEP),
            length("step_depth", "Step depth", 100.0),  # 0 for shapes without a step, the joint then uses its default
            length("heel_depth", "Heel depth", 100.0),  # 0 for shapes without a heel, idem
            length("tenon_mortise_height", "Tenon height (0 = none)", 100.0, default=0.0, zero_is_none=True),
        ],
        beams={"angle": 45.0},
        insertion=along_main_axis,
    ),
    JointSpec("T-Tenon Mortise", TTenonMortiseJoint, "T", TENON, insertion=off_the_cross_face),
    # the tenon curls out of a face of the main beam parallel to the plane of both beams: the main beam must not be
    # tilted out of it. At an angle, its end is housed in the cross beam.
    JointSpec(
        "T-Rotational Tenon Mortise",
        TRotationalTenonMortiseJoint,
        "T",
        ROTATIONAL_TENON,
        beams={"tilt": 0.0},
        insertion=about_the_rotation_axis,
    ),
    JointSpec("X-Lap", XLapJoint, "X", LAP, roles=AB, insertion=apart_from_the_lap),
    JointSpec("X-Notch", XNotchJoint, "X", beams={"offset": 120.0}, roles=("notch_beam", "solid_beam"), insertion=out_of_the_notch),
    JointSpec(
        "I-Simple Scarf",
        ISimpleScarf,
        "I",
        [
            length("length", "Scarf length", 800.0, minimum=10.0),
            length("depth_ref_side", "Depth on ref. side", 150.0, minimum=1.0),
            length("depth_opp_side", "Depth on opp. side", 150.0, minimum=1.0),
            integer("num_drill_hole", "Drill holes", 0, 2, 0),
            length("drill_hole_diam", "Drill hole diameter", 40.0, minimum=5.0, default=20.0),
            integer("ref_side_index", "Ref. side index", 0, 3, 0),
        ],
        insertion=apart_from_the_scarf,
    ),
    JointSpec("Y-Butt", YButtJoint, "Y", [MILL_DEPTH], roles=("main_beam", "cross_beam_a", "cross_beam_b")),
    JointSpec("Y-Ball Node", BallNodeJoint, "Y", [length("ball_diameter", "Ball diameter", 300.0, minimum=20.0)], roles=("beam_1", "beam_2", "beam_3")),
]

# ==========================================================================
# Beams
# ==========================================================================

ARM = 800.0  # length of a beam from the joint to its free end
NODE = Point(0, 0, 0)
UP = Vector(0, 0, 1)

TOPOLOGY_NAMES = {"L": "L topology", "T": "T topology", "X": "X topology", "I": "I topology", "Y": "Y topology"}


def beam_params(topology):
    """The settings of the beams that make up a topology."""
    params = [
        length("main_width", "Main beam width", 300.0, minimum=20.0, default=80.0, step=5.0),
        length("main_height", "Main beam height", 400.0, minimum=20.0, default=160.0, step=5.0),
        length("cross_width", "Other beam(s) width", 300.0, minimum=20.0, default=80.0, step=5.0),
        length("cross_height", "Other beam(s) height", 400.0, minimum=20.0, default=160.0, step=5.0),
    ]
    if topology in ("L", "T", "X"):
        params.append(angle("angle", "Angle between beams", 20.0, 160.0, default=90.0))
    if topology == "T":
        params.append(angle("tilt", "Main beam tilt", -60.0, 60.0, default=0.0))
    if topology == "X":
        params.append(length("offset", "Vertical offset", minimum=-300.0, maximum=300.0, default=0.0, step=5.0))
    if topology == "Y":
        params.append(angle("angle", "Branch angle", 60.0, 170.0, default=120.0))
    return params


def direction(angle, tilt=0.0):
    """A unit vector at `angle` degrees from the X axis in the XY plane, tilted `tilt` degrees out of it."""
    a, t = math.radians(angle), math.radians(tilt)
    return Vector(math.cos(a) * math.cos(t), math.sin(a) * math.cos(t), math.sin(t))


def beam_layout(topology, settings):
    """Lays out the centerlines of the beams of a topology.

    Returns
    -------
    list(tuple(:class:`~compas.geometry.Line`, float, float, :class:`~compas.geometry.Vector`))
        Per beam, in the order the joint takes them: centerline, width, height and the direction in which the
        beam moves away from the joint when the view is exploded.

    """
    main = settings["main_width"], settings["main_height"]
    other = settings["cross_width"], settings["cross_height"]
    x = Vector(1, 0, 0)
    zero = Vector(0, 0, 0)

    if topology == "L":
        d = direction(settings["angle"])
        return [(Line(NODE, NODE + d * ARM), *main, d), (Line(NODE, NODE + x * ARM), *other, x)]

    if topology == "T":
        d = direction(settings["angle"], settings["tilt"])
        cross = Line(NODE - x * ARM * 0.75, NODE + x * ARM * 0.75)
        return [(Line(NODE + d * ARM, NODE), *main, d), (cross, *other, zero)]

    if topology == "X":
        offset = UP * settings["offset"]
        d = direction(settings["angle"])
        side = UP if settings["offset"] >= 0 else -UP
        top = Line(NODE + offset - d * ARM * 0.75, NODE + offset + d * ARM * 0.75)
        bottom = Line(NODE - x * ARM * 0.75, NODE + x * ARM * 0.75)
        return [(top, *main, side), (bottom, *other, -side)]

    if topology == "I":
        return [(Line(NODE - x * ARM, NODE), *main, -x), (Line(NODE, NODE + x * ARM), *other, x)]

    if topology == "Y":
        branches = [direction(90.0), direction(90.0 + settings["angle"]), direction(90.0 - settings["angle"])]
        dims = [main, other, other]
        return [(Line(NODE + d * ARM, NODE), *dim, d) for d, dim in zip(branches, dims)]

    raise ValueError("Unknown topology: {}".format(topology))


# ==========================================================================
# UI components
# ==========================================================================


class RangeSlider(Slider):
    """A compact slider whose range survives floating point steps (e.g. 0.95 / 0.05 -> 18.999...).

    The range is shown as a tooltip instead of below the slider, so that more sliders fit in the dock.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slider.setTickPosition(QSlider.NoTicks)
        self._min_label.hide()
        self._max_label.hide()
        self.layout.setContentsMargins(9, 3, 9, 3)
        self.layout.setSpacing(2)
        self.widget.setToolTip("{} to {}".format(self.min_val, self.max_val))

    @property
    def _scaled_min_val(self):
        return int(round(self.min_val / self.step))

    @property
    def _scaled_max_val(self):
        return int(round(self.max_val / self.step))


class ComboBox(BoundComponent):
    """A labelled dropdown bound to a key of a dict, like the viewer's own sliders and toggles.

    Parameters
    ----------
    obj : dict
        The dict holding the value.
    attr : str
        The key of the value.
    items : list(tuple(str, object))
        The (text, value) pairs to choose from. An item of (None, None) inserts a separator.
    title : str, optional
        The label in front of the dropdown.
    action : callable, optional
        Called with the component and the new value when the user picks an item.

    """

    def __init__(self, obj, attr, items, title=None, action=None):
        super().__init__(obj, attr, action=action, watch_interval=None)
        self._updating = False
        layout = QHBoxLayout()
        layout.setContentsMargins(9, 4, 9, 4)
        self.label = QLabel("{}:".format(title)) if title else None
        if self.label is not None:
            layout.addWidget(self.label)
        self.combo = QComboBox()
        for text, value in items:
            if text is None:
                self.combo.insertSeparator(self.combo.count())
            else:
                self.combo.addItem(text, value)
        layout.addWidget(self.combo, 1)
        self.widget.setLayout(layout)
        self.sync_from_bound_object(self.get_attr())
        self.combo.currentIndexChanged.connect(self.on_index_changed)

    def on_index_changed(self, index):
        if not self._updating:
            self.on_value_changed(self.combo.itemData(index))

    def sync_from_bound_object(self, value):
        self._updating = True
        try:
            index = self.combo.findData(value)
            if index >= 0:
                self.combo.setCurrentIndex(index)
        finally:
            self._updating = False


class Label(Component):
    """A block of (rich) text."""

    def __init__(self, text="", style=None):
        super().__init__()
        self.widget = QLabel(text)
        self.widget.setWordWrap(True)
        self.widget.setTextFormat(Qt.RichText)
        self.widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.widget.setStyleSheet(style or "padding: 4px 9px;")

    @property
    def text(self):
        return self.widget.text()

    @text.setter
    def text(self, value):
        self.widget.setText(value)


def heading(text):
    return Label(text, style="font-weight: bold; font-size: 13px; padding: 14px 9px 2px 9px; border-bottom: 1px solid #bbbbbb;")


# ==========================================================================
# The explorer
# ==========================================================================

BEAM_COLORS = [Color.from_hex("#e3b778"), Color.from_hex("#9fbcd6"), Color.from_hex("#b5d1a0")]
EDGE_COLOR = Color.from_hex("#4d4d4d")
BLANK_COLOR = Color.from_hex("#bfbfbf")
FASTENER_COLOR = Color.from_hex("#8c8c8c")
AXIS_COLOR = Color.from_hex("#d6453d")
ERROR_COLOR = "#e5533d"  # readable on the viewer's light and dark themes


class JointExplorer(object):
    """Holds the state of the explorer, builds the side dock and redraws the joint.

    Parameters
    ----------
    viewer : :class:`compas_viewer.Viewer`
        The viewer to draw in.
    joint_name : str
        The name of the joint to start with.

    """

    def __init__(self, viewer, joint_name):
        self.viewer = viewer
        self.state = {"joint": joint_name}
        self.beam_settings = {}
        self.joint_values = {}
        self.auto = set()  # names of the joint parameters left to the joint
        self.display = {"explode": 120.0, "show_blanks": False, "show_centerlines": False}
        self.spec = None
        self.joint = None
        self.model = None
        self.layout = []
        self.objects = []  # (scene object, explode direction)
        self.param_widgets = {}

        self.rebuild_timer = QTimer()
        self.rebuild_timer.setSingleShot(True)
        self.rebuild_timer.setInterval(40)  # coalesce slider drags into one rebuild
        self.rebuild_timer.timeout.connect(self.rebuild)

        self._build_dock()
        self.select_joint(joint_name)

    # ----------------------------------------------------------------------
    # side dock
    # ----------------------------------------------------------------------

    def _build_dock(self):
        dock = self.viewer.ui.sidedock
        dock.widget.setWindowTitle("Joint Explorer")
        dock.widget.setMinimumWidth(340)

        items = []  # grouped by topology, with a separator in between
        for previous, spec in zip([None] + JOINTS[:-1], JOINTS):
            if previous is not None and previous.topology != spec.topology:
                items.append((None, None))
            items.append((spec.name, spec.name))

        dock.add(heading("Joint"))
        dock.add(ComboBox(self.state, "joint", items, title="Type", action=lambda component, name: self.select_joint(name)))
        self.description = Label(style="padding: 2px 9px 4px 9px; font-size: 11px;")
        dock.add(self.description)
        self.info = Label(style="padding: 6px 9px;")
        dock.add(self.info)
        dock.add(Button(text="Copy code", tooltip="Copy a script that rebuilds this joint to the clipboard", action=self.copy_code))

        dock.add(heading("Joint parameters"))
        self.param_container = Container()
        dock.add(self.param_container)
        dock.add(Button(text="Reset joint parameters", tooltip="Hand the parameters back to the joint", action=self.reset_joint_params))

        dock.add(heading("Display"))
        dock.add(RangeSlider(self.display, "explode", title="Explode [mm]", min_val=0.0, max_val=400.0, step=5.0, action=self.on_explode, watch_interval=None))
        for name, title in (("show_blanks", "Ghost uncut blanks"), ("show_centerlines", "Show centerlines")):
            toggle_ = BooleanToggle(self.display, name, title=title, action=lambda component, value: self.rebuild())
            toggle_.stop_watching()
            dock.add(toggle_)

        dock.add(heading("Beams"))
        self.beam_container = Container()
        dock.add(self.beam_container)

    def _make_widget(self, param, values, action):
        if param.kind == "bool":
            component = BooleanToggle(values, param.name, title=param.label, action=action)
            component.stop_watching()
            return component
        if param.kind == "choice":
            return ComboBox(values, param.name, [(c, c) for c in param.choices], title=param.label, action=action)
        return RangeSlider(values, param.name, title=param.label, min_val=param.minimum, max_val=param.maximum, step=param.step, action=action, watch_interval=None)

    def _fill(self, container, params, values, action):
        for child in container.children:
            if isinstance(child, BoundComponent):
                child.stop_watching()
        container.reset()
        widgets = {}
        for param in params:
            widget = self._make_widget(param, values, lambda component, value, param=param: action(param, value))
            container.add(widget)
            widgets[param.name] = widget
        return widgets

    def _mark_auto(self, param):
        """Shows on a widget whether its value is picked by the joint."""
        widget = self.param_widgets.get(param.name)
        text = "{} (auto):".format(param.label) if param.name in self.auto else "{}:".format(param.label)
        if isinstance(widget, Slider):
            widget.value_label.setText(text)
        elif isinstance(widget, ComboBox) and widget.label is not None:
            widget.label.setText(text)

    def _set_widget(self, param, value):
        """Shows `value` on the widget of `param` without triggering its action."""
        widget = self.param_widgets.get(param.name)
        if widget is None:
            return
        if param.kind == "bool":
            widget.checkbox.blockSignals(True)
            widget.checkbox.setChecked(value)
            widget.checkbox.blockSignals(False)
        else:
            widget.sync_from_bound_object(round(value, 2) if isinstance(value, float) else value)

    # ----------------------------------------------------------------------
    # state changes
    # ----------------------------------------------------------------------

    def select_joint(self, name):
        previous = self.spec
        self.spec = next(spec for spec in JOINTS if spec.name == name)
        self.description.text = "<b>{}</b> &middot; {}<br>{}".format(self.spec.cls.__name__, TOPOLOGY_NAMES[self.spec.topology], self.spec.description)

        # beam sizes carry over, the layout of the beams starts over when the topology changes, and what a joint set for
        # itself (e.g. the birdsmouth's tilt) goes back to its default when another joint is picked
        topology_changed = previous is None or previous.topology != self.spec.topology
        overridden_before = set(previous.beams) if previous is not None else set()
        for param in beam_params(self.spec.topology):
            if param.name.startswith(("main_", "cross_")) and param.name in self.beam_settings:
                continue
            if topology_changed or param.name not in self.beam_settings or param.name in overridden_before:
                self.beam_settings[param.name] = param.default
        self.beam_settings.update(self.spec.beams)
        self._fill(self.beam_container, beam_params(self.spec.topology), self.beam_settings, self.on_beam_changed)

        self.joint_values = {}
        self.reset_joint_params(rebuild=False)
        self.param_widgets = self._fill(self.param_container, self.spec.params, self.joint_values, self.on_param_changed)
        if not self.spec.params:
            self.param_container.display_text("This joint has no parameters.")
        for param in self.spec.params:
            self._mark_auto(param)
        self.rebuild()

    def reset_joint_params(self, rebuild=True):
        self.auto = set(param.name for param in self.spec.params if param.is_auto)
        for param in self.spec.params:
            self.joint_values[param.name] = param.placeholder if param.is_auto else param.default
        if rebuild:
            for param in self.spec.params:
                self._set_widget(param, self.joint_values[param.name])
                self._mark_auto(param)
            self.rebuild()

    def on_beam_changed(self, param, value):
        self.rebuild_timer.start()

    def on_param_changed(self, param, value):
        if param.name in self.auto:
            self.auto.discard(param.name)
            self._mark_auto(param)
        self.rebuild_timer.start()

    def on_explode(self, component, value):
        for obj, motion in self.objects:
            obj.transformation = motion.at(value)
            obj.update()
        self.viewer.renderer.update()

    # ----------------------------------------------------------------------
    # model
    # ----------------------------------------------------------------------

    def joint_kwargs(self):
        return {p.name: p.to_argument(self.joint_values[p.name]) for p in self.spec.params if p.name not in self.auto}

    def rebuild(self):
        """Builds the beams and the joint from the current state and redraws them."""
        self.rebuild_timer.stop()
        start = time.perf_counter()
        self.layout = beam_layout(self.spec.topology, self.beam_settings)
        self.model = TimberModel()
        beams = []
        for centerline, width, height, _ in self.layout:
            beam = Beam.from_centerline(centerline, width=width, height=height, z_vector=UP)
            self.model.add_element(beam)
            beams.append(beam)

        errors = []
        self.joint = None
        try:
            self.joint = self.spec.cls.create(self.model, *beams, **self.joint_kwargs())
            errors = self.model.process_joinery()
            geometries = [beam.geometry for beam in beams]
        except Exception as error:  # show whatever the joint complains about, and the beams without it
            errors.append(error)
            self.model = TimberModel()
            beams = [Beam.from_centerline(line, width=w, height=h, z_vector=UP) for line, w, h, _ in self.layout]
            for beam in beams:
                self.model.add_element(beam)
            geometries = [beam.geometry for beam in beams]
        elapsed = time.perf_counter() - start

        self._sync_auto_params()
        self._draw(beams, geometries)
        self._report(beams, errors, elapsed)

    def _sync_auto_params(self):
        """Shows the values the joint picked for the "auto" parameters."""
        if self.joint is None:
            return
        for param in self.spec.params:
            if param.name not in self.auto:
                continue
            value = getattr(self.joint, param.name, None)
            if value is None:
                continue
            self.joint_values[param.name] = value
            self._set_widget(param, value)

    def _fasteners(self):
        """Geometry of the elements the joint generated, e.g. the ball of a ball node."""
        for element in self.model.elements():
            if isinstance(element, Beam):
                continue
            geometry = element.geometry
            if geometry is None and hasattr(element, "ball_diameter"):
                geometry = Sphere(element.ball_diameter / 2.0, point=element.node_point)  # the ball node fastener has no geometry of its own yet
            if geometry is not None:
                yield geometry

    def explode_motions(self, beams):
        """How each beam moves when the view is exploded (a `Slide` or a `Swing`): its insertion, reversed.

        Falls back to pulling the beams apart along their axes for joints without an insertion rule, and when the
        joint failed to build (the beams drawn are then fresh copies the joint doesn't know).
        """
        away = {beam: vector for beam, (_, _, _, vector) in zip(beams, self.layout)}
        fallback = [Slide(away[beam]) for beam in beams]
        if self.spec.insertion is None or self.joint is None:
            return fallback
        if not all(any(beam is element for element in self.joint.elements) for beam in beams):
            return fallback
        try:
            motions = self.spec.insertion(self.joint, away)
        except Exception:  # e.g. a reference side the joint can't resolve for this layout
            return fallback
        result = []
        for beam in beams:
            motion = motions.get(beam, Vector(0, 0, 0))
            result.append(motion if isinstance(motion, (Slide, Swing)) else Slide(motion))
        return result

    def _rotation_axis(self):
        """The rotation axis of the joint and the circle the tenon's centerline follows around it on the shoulder, as
        lines to draw, if the joint has one and it was built."""
        try:
            axis = self.joint.rotation_axis
            radius = self.joint.rotation_radius
        except Exception:  # no such joint, or one which failed to build
            return []
        reach = 2.0 * max(self.beam_settings["main_height"], self.beam_settings["cross_height"])
        circle = Circle(radius, frame=Frame.from_plane(Plane(axis.start, axis.direction)))
        return [Line(axis.start - axis.direction * reach, axis.start + axis.direction * reach), circle.to_polyline(n=96)]

    def _draw(self, beams, geometries):
        items = []
        motions = self.explode_motions(beams)
        for index, (beam, geometry, motion) in enumerate(zip(beams, geometries, motions)):
            name = self.spec.roles[index].replace("_", " ")
            color = BEAM_COLORS[index % len(BEAM_COLORS)]
            items.append((geometry, motion, dict(name=name, facecolor=color, linecolor=EDGE_COLOR, show_points=False)))
            if self.display["show_blanks"]:
                items.append((beam.blank, motion, dict(name=name + " blank", facecolor=BLANK_COLOR, linecolor=BLANK_COLOR, opacity=0.2, show_points=False)))
            if self.display["show_centerlines"]:
                items.append((beam.centerline, motion, dict(name=name + " centerline", linecolor=Color.red(), linewidth=2)))
        still = Slide(Vector(0, 0, 0))
        for geometry in self._fasteners():
            items.append((geometry, still, dict(name="fastener", facecolor=FASTENER_COLOR, show_lines=False, show_points=False)))
        for line, width in zip(self._rotation_axis(), (3, 1)):
            items.append((line, still, dict(name="rotation axis", linecolor=AXIS_COLOR, linewidth=width)))

        scene = self.viewer.scene
        running = self.viewer.running
        self.viewer.running = False  # add and remove objects without rebuilding the GPU buffers for each of them
        try:
            for obj, _ in self.objects:
                scene.remove(obj)
            self.objects = []
            for item, motion, kwargs in items:
                obj = scene.add(item, **kwargs)
                obj.transformation = motion.at(self.display["explode"])
                self.objects.append((obj, motion))
        finally:
            self.viewer.running = running
        if running:
            self.viewer.renderer.rebuild_buffers()
            self.viewer.renderer.update()

    def _report(self, beams, errors, elapsed):
        lines = []
        skipped = 0
        for index, beam in enumerate(beams):
            color = BEAM_COLORS[index % len(BEAM_COLORS)].hex
            role = self.spec.roles[index].replace("_", " ")
            features = ", ".join(type(feature).__name__.replace("Proxy", "") for feature in beam.features) or "no features"
            lines.append('<span style="color:{}">&#9632;</span> <b>{}</b>: {}'.format(color, role, features))
            # features that fail to apply don't raise, the beam keeps them in `debug_info` and is drawn without them
            for error in beam.debug_info:
                skipped += 1
                lines.append('<span style="color:{}">&nbsp;&nbsp;&nbsp;not applied: {}</span>'.format(ERROR_COLOR, self._message(error)))
        for error in errors:
            lines.append('<span style="color:{}"><b>{}</b>: {}</span>'.format(ERROR_COLOR, type(error).__name__, self._message(error)))
        self.info.text = "<br>".join(lines)
        problems = len(errors) + skipped
        status = "{} problem(s)".format(problems) if problems else "ok"
        self.status("{}: {}  |  rebuilt in {:.0f} ms".format(self.spec.name, status, elapsed * 1000))

    @staticmethod
    def _message(error):
        text = getattr(error, "message", None) or getattr(error, "debug_info", None) or str(error)
        return str(text).replace("<", "&lt;").replace(">", "&gt;")

    def status(self, text):
        """Writes into the viewer's status bar (its "Ready..." label)."""
        label = self.viewer.ui.statusbar.widget.findChild(QLabel)
        if label is not None:
            label.setText(text)
        else:
            self.viewer.ui.statusbar.widget.showMessage(text)

    # ----------------------------------------------------------------------
    # code
    # ----------------------------------------------------------------------

    def code(self):
        """A script that rebuilds the current beams and joint."""

        def point(p):
            return "Point({:.1f}, {:.1f}, {:.1f})".format(p.x, p.y, p.z)

        lines = [
            "from compas.geometry import Line",
            "from compas.geometry import Point",
            "from compas.geometry import Vector",
            "from compas_timber.connections import {}".format(self.spec.cls.__name__),
            "from compas_timber.elements import Beam",
            "from compas_timber.model import TimberModel",
            "",
            "model = TimberModel()",
        ]
        for role, (line, width, height, _) in zip(self.spec.roles, self.layout):
            lines.append(
                "{} = Beam.from_centerline(Line({}, {}), width={:.1f}, height={:.1f}, z_vector=Vector(0, 0, 1))".format(role, point(line.start), point(line.end), width, height)
            )
            lines.append("model.add_element({})".format(role))
        arguments = ["model"] + list(self.spec.roles)
        arguments += ["{}={!r}".format(name, value) for name, value in self.joint_kwargs().items()]
        lines.append("{}.create({})".format(self.spec.cls.__name__, ", ".join(arguments)))
        lines.append("errors = model.process_joinery()")
        return "\n".join(lines)

    def copy_code(self):
        code = self.code()
        QApplication.clipboard().setText(code)
        print(code)
        self.status("Copied the code for {} to the clipboard".format(self.spec.name))


if __name__ == "__main__":
    config = Config()
    config.window.title = "compas_timber Joint Explorer"
    config.window.width = 1500
    config.window.height = 950
    config.ui.sidedock.show = True
    config.ui.sidebar.show = False
    config.renderer.gridsize = (3000.0, 30, 3000.0, 30)

    viewer = Viewer(config=config)
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [2100.0, 1300.0, 1500.0]  # looking into the joint, from the side of the main beam
    viewer.renderer.camera.target = [0.0, 0.0, 0.0]
    viewer.renderer.camera.pandelta = 0.05

    explorer = JointExplorer(viewer, "T-Dovetail")
    viewer.show()
