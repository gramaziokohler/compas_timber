import math

from compas.geometry import Cylinder
from compas.geometry import Frame
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .dovetail import point_mapper
from .dovetail import prism


class ScarfShapeType(object):
    """Enum for the shape of a :class:`ScarfJoint`.

    Attributes
    ----------
    REFSIDE : literal("refside")
        The ends of the scarf are perpendicular to the reference side.
    BASESIDE : literal("baseside")
        The ends of the scarf are perpendicular to its faces.
    CLASSIC : literal("classic")
        Like `REFSIDE`, but the step is centered on the element, which makes both halves of a joint identical.
    """

    REFSIDE = "refside"
    BASESIDE = "baseside"
    CLASSIC = "classic"


class ScarfJoint(ParametricProcessing):
    """Represents a ScarfJoint feature to be made on an end of an element. This processing trims the element.

    Seen from the side, the end is cut by two parallel faces with a step in between. They fall from the reference side towards the opposite side, away from `start_x`.

    Parameters
    ----------
    orientation : str
        Which end of the element is processed. :attr:`OrientationType.START` or :attr:`OrientationType.END`.
    start_x : float
        Distance from the start of the element to the tip of the scarf on the reference side. -100000.0 < start_x < 100000.0.
    inclination : float, optional
        Angle between the reference side and the faces, in degrees. 0.0 < inclination < 90.0.
    lap_length : float
        Length, along the faces, of the face next to the opposite side. Ignored by the classic shape. 0.0 < lap_length < 50000.0.
    lap_depth : float
        Height of the step, perpendicular to the faces. 0.0 < lap_depth < 50000.0.
    length : float
        Length of the scarf, along the element. 0.0 < length < 50000.0.
    depth_opp_side : float
        Distance from the opposite side to the end of the faces. Ignored by the classic shape. 0.0 < depth_opp_side < 50000.0.
    scarf_shape : str
        The shape of the scarf. One of :class:`ScarfShapeType`.
    num_drill_hole : int
        Number of holes, perpendicular to the reference side. 0 <= num_drill_hole <= 2.
    drill_hole_diam_1 : float
        Diameter of the first hole, the one with the lower x. 0.0 < drill_hole_diam_1 < 1000.0.
    drill_hole_diam_2 : float
        Diameter of the second hole. 0.0 < drill_hole_diam_2 < 1000.0.

    """

    PROCESSING_NAME = "ScarfJoint"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "Inclination": AttributeSpec("inclination", float, None, (0.0, 90.0)),
        "LapLength": AttributeSpec("lap_length", float, 100.0, (0.0, 50000.0), scales=True),
        "LapDepth": AttributeSpec("lap_depth", float, 20.0, (0.0, 50000.0), scales=True),
        "Length": AttributeSpec("length", float, 200.0, (0.0, 50000.0), scales=True),
        "DepthOppSide": AttributeSpec("depth_opp_side", float, 20.0, (0.0, 50000.0), scales=True),
        "ScarfShape": AttributeSpec("scarf_shape", str, ScarfShapeType.REFSIDE, choices=(ScarfShapeType.REFSIDE, ScarfShapeType.BASESIDE, ScarfShapeType.CLASSIC)),
        "NumDrillHole": AttributeSpec("num_drill_hole", int, 0, (0, 2)),
        "DrillHoleDiam1": AttributeSpec("drill_hole_diam_1", float, 20.0, (0.0, 1000.0), scales=True),
        "DrillHoleDiam2": AttributeSpec("drill_hole_diam_2", float, 20.0, (0.0, 1000.0), scales=True),
    }

    def volumes_from_params_and_element(self, element):
        """The volumes this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If `inclination` is not set or 90 degrees, which leaves the faces without a length.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        if self.inclination is None or self.inclination >= 90.0:
            raise ValueError("The inclination of the ScarfJoint must be set and smaller than 90 degrees. Got: {}".format(self.inclination))
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        to_model = point_mapper(self, element)
        margin = width + height + self.length
        section = self._section(height, abs(self.start_x) + element.blank_length + margin, margin)
        volumes = [prism([to_model(a, -margin, d) for a, d in section], [to_model(a, width + margin, d) for a, d in section])]
        return volumes + self._drill_holes(element, to_model, width, height, margin)

    def _section(self, height, end, margin):
        # (along, depth) outline of what is removed, the profile of the scarf is `tip`, `step_start`, `step_end`, `tail`
        sine, cosine = math.sin(math.radians(self.inclination)), math.cos(math.radians(self.inclination))
        if self.scarf_shape == ScarfShapeType.CLASSIC:
            # the step is centered on the diagonal of the scarf
            step_end = (self.length / 2.0 + self.lap_depth / 2.0 * sine, height / 2.0 - self.lap_depth / 2.0 * cosine)
            tail = (self.length, step_end[1] + (self.length - step_end[0]) * sine / cosine)
        else:
            tail = (self.length, height - self.depth_opp_side)
            step_end = (tail[0] - self.lap_length * cosine, tail[1] - self.lap_length * sine)
        step_start = (step_end[0] - self.lap_depth * sine, step_end[1] + self.lap_depth * cosine)
        tip = (0.0, step_start[1] - step_start[0] * sine / cosine)

        top = min(tip[1], 0.0) - margin
        bottom = max(tail[1], height) + margin
        if self.scarf_shape == ScarfShapeType.BASESIDE:
            start = (tip[0] + (tip[1] - top) * sine / cosine, top)
            finish = (tail[0] - (bottom - tail[1]) * sine / cosine, bottom)
        else:
            start = (0.0, top)
            finish = (self.length, bottom)
        return [start, tip, step_start, step_end, tail, finish, (-end, bottom), (-end, top)]

    def _drill_holes(self, element, to_model, width, height, margin):
        # the holes are on the center of the width. The figure places two at the quarters of the length, a single one is assumed at the center
        if self.num_drill_hole == 0:
            return []
        positions = [0.5] if self.num_drill_hole == 1 else [0.25, 0.75]
        if self.orientation == OrientationType.END:
            positions.reverse()
        ref_side = element.ref_sides[self.ref_side_index]
        holes = []
        for position, diameter in zip(positions, (self.drill_hole_diam_1, self.drill_hole_diam_2)):
            if diameter > 0.0:
                frame = Frame(to_model(position * self.length, width / 2.0, height / 2.0), ref_side.xaxis, ref_side.yaxis)
                holes.append(Brep.from_cylinder(Cylinder(diameter / 2.0, height + margin, frame)))
        return holes
