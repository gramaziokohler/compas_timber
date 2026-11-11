import math

from compas.geometry import Frame
from compas.geometry import Point
from compas.tolerance import TOL

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .log_house_half_lap import prism


class HipValleyRafterNotch(ParametricProcessing):
    """Represents a Hip Valley Rafter Notch feature to be made on a beam.

    The notch which seats a rafter on two counterparts, e.g. the purlins of the two roof planes meeting at a hip or a valley.
    Its floor is a single plane, which slopes along the rafter only, and is therefore horizontal on a rafter of that slope.
    In the floor, the outline is a chevron of two arms, one running towards the reference edge and one towards the opposite edge. Each arm is as wide as its counterpart.
    Its walls are perpendicular to the floor.

    A chevron which opens towards the rising end of the floor, with angles below 90 degrees, is the notch of a hip rafter. Angles above 90 degrees make that of a valley rafter.

    Parameters
    ----------
    orientation : str
        ``OrientationType.START`` raises the floor towards the end of the part, ``OrientationType.END`` towards the start.
    start_x : float
        The x coordinate in the reference side of the chevron's tip, on the wall which faces away from the rising end of the floor. -100000.0 <= start_x <= 100000.0.
    start_y : float
        The y coordinate in the reference side of the same tip. -50000.0 <= start_y <= 50000.0.
    start_depth : float
        The depth of the same tip below the reference side. 0.0 <= start_depth <= 50000.0.
    angle_ref_edge : float
        The angle in the floor between the arm towards the reference edge and the floor's direction falling away. 0.1 <= angle_ref_edge <= 179.9.
    angle_opp_edge : float
        The angle in the floor between the arm towards the opposite edge and the floor's direction falling away. 0.1 <= angle_opp_edge <= 179.9.
    inclination : float
        The angle between the floor and the reference side, along the part. 0.0 <= inclination <= 180.0.
    width_counter_part_ref_edge_limited : bool
        If True, the arm towards the reference edge stops at ``width_counter_part_ref_edge``. Otherwise, it opens on the rising end of the floor.
    width_counter_part_ref_edge : float
        The width of the arm towards the reference edge, in the floor and perpendicular to the arm. 0.0 <= width_counter_part_ref_edge <= 50000.0.
    width_counter_part_opp_edge_limited : bool
        If True, the arm towards the opposite edge stops at ``width_counter_part_opp_edge``. Otherwise, it opens on the rising end of the floor.
    width_counter_part_opp_edge : float
        The width of the arm towards the opposite edge, in the floor and perpendicular to the arm. 0.0 <= width_counter_part_opp_edge <= 50000.0.
    rafter_nail_hole : bool
        If True, a hole for the rafter nail is requested. It has no effect on the geometry.

    """

    PROCESSING_NAME = "HipValleyRafterNotch"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 0.0, (-50000.0, 50000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 20.0, (0.0, 50000.0), scales=True),
        "AngleRefEdge": AttributeSpec("angle_ref_edge", float, 45.0, (0.1, 179.9)),
        "AngleOppEdge": AttributeSpec("angle_opp_edge", float, 45.0, (0.1, 179.9)),
        "Inclination": AttributeSpec("inclination", float, 30.0, (0.0, 180.0)),
        "WidthCounterPartRefEdgeLimited": AttributeSpec("width_counter_part_ref_edge_limited", bool, False),
        "WidthCounterPartRefEdge": AttributeSpec("width_counter_part_ref_edge", float, 120.0, (0.0, 50000.0), scales=True),
        "WidthCounterPartOppEdgeLimited": AttributeSpec("width_counter_part_opp_edge_limited", bool, False),
        "WidthCounterPartOppEdge": AttributeSpec("width_counter_part_opp_edge", float, 120.0, (0.0, 50000.0), scales=True),
        "RafterNailHole": AttributeSpec("rafter_nail_hole", bool, False),
    }

    def volumes_from_params_and_element(self, element):
        """The material above the floor of the notch, within the chevron.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        # shortcut: rafter_nail_hole is not modelled, the specification gives neither its position nor its size. Upgrade if a machine's interpretation is known.
        ref_side = element.ref_sides[self.ref_side_index]
        reach = element.blank_length + element.width + element.height + abs(self.start_x) + abs(self.start_y) + self.start_depth  # any distance across the element

        inclination = math.radians(self.inclination)
        rise = ref_side.xaxis * math.cos(inclination) * (1.0 if self.orientation == OrientationType.START else -1.0) + ref_side.zaxis * math.sin(inclination)
        floor = Frame(ref_side.to_world_coordinates(Point(self.start_x, self.start_y, -self.start_depth)), rise, ref_side.yaxis)

        # in the floor's coordinates, whose x axis rises and whose y axis points away from the reference edge. Both widths extend towards the floor's rising end.
        ref_angle, opp_angle = math.radians(self.angle_ref_edge), math.radians(self.angle_opp_edge)
        ref_arm = (math.cos(ref_angle) * reach / math.sin(ref_angle), -reach)
        opp_arm = (math.cos(opp_angle) * reach / math.sin(opp_angle), reach)
        ref_normal = (math.sin(ref_angle), math.cos(ref_angle))
        opp_normal = (math.sin(opp_angle), -math.cos(opp_angle))
        ref_width = self.width_counter_part_ref_edge if self.width_counter_part_ref_edge_limited else reach
        opp_width = self.width_counter_part_opp_edge if self.width_counter_part_opp_edge_limited else reach

        determinant = ref_normal[0] * opp_normal[1] - ref_normal[1] * opp_normal[0]
        if TOL.is_zero(determinant):  # the arms are in line, a chevron without a tip
            inner_corners = [(ref_normal[0] * ref_width, ref_normal[1] * ref_width), (opp_normal[0] * opp_width, opp_normal[1] * opp_width)]
            if TOL.is_close(ref_width, opp_width):
                inner_corners.pop()
        else:
            inner_corners = [((ref_width * opp_normal[1] - opp_width * ref_normal[1]) / determinant, (opp_width * ref_normal[0] - ref_width * opp_normal[0]) / determinant)]

        outline = [(0.0, 0.0), ref_arm]
        outline.append((inner_corners[0][0] + ref_arm[0], inner_corners[0][1] + ref_arm[1]))
        outline.extend(inner_corners)
        outline.append((inner_corners[-1][0] + opp_arm[0], inner_corners[-1][1] + opp_arm[1]))
        outline.append(opp_arm)

        height = reach if floor.zaxis.dot(ref_side.zaxis) >= 0.0 else -reach  # towards the outside of the reference side
        return [prism(floor, [(x, y, 0.0) for x, y in outline], height)]
