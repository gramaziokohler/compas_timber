import math

from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing
from .dovetail import point_mapper
from .dovetail import prism

ARC_SEGMENTS = 12  # shortcut: the round corners of the tenon are faceted, upgrade with true arcs if their surface must be exact


class JapaneseTenon(ParametricProcessing):
    """Represents a JapaneseTenon feature, the gooseneck of a Japanese scarf joint. This processing trims the element.

    At `start_x` the end of the element is cut off, except for a tenon: a neck of `width_1` and `length_1`, followed by a head which tapers from `width_2` to `width_3` along
    `length_2`. The tenon runs from the reference side to `offset` above the opposite side and has a U shaped section.

    Parameters
    ----------
    orientation : str
        Which end of the element is processed. :attr:`OrientationType.START` or :attr:`OrientationType.END`.
    start_x : float
        Distance from the start of the element to the shoulder. -100000.0 < start_x < 100000.0.
    start_y : float
        Distance from the reference edge to the axis of the tenon. -50000.0 < start_y < 50000.0.
    width_1 : float
        Width of the neck on the reference side. 0.0 < width_1 < 100000.0.
    length_1 : float
        Length of the neck. 0.0 < length_1 < 100000.0.
    width_2 : float
        Width of the head on the reference side, at the neck. 0.0 < width_2 < 100000.0.
    length_2 : float
        Length of the head. 0.0 < length_2 < 100000.0.
    width_3 : float
        Width of the head on the reference side, at its end. 0.0 < width_3 < 100000.0.
    cone_angle : float
        Angle of the flanks to the normal of the reference side, in degrees. They narrow with the depth. 0.0 < cone_angle < 30.0.
    middle_plane : float
        Width of the flat part of the tenon's bottom, between the two round corners. 0.0 < middle_plane < 100000.0.
    offset : float
        Distance from the opposite side to the bottom of the neck. 0.0 < offset < 100000.0.
    use_lap : bool
        True if the lower part of the shoulder has a lap.
    lap_offset : float
        Distance from the bottom of the neck down to the lap. 0.0 < lap_offset < 100000.0.
    lap_depth : float
        Length of the lap along the element. 0.0 < lap_depth < 100000.0.

    """

    PROCESSING_NAME = "JapaneseTenon"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 50.0, (-50000.0, 50000.0), scales=True),
        "Width1": AttributeSpec("width_1", float, 40.0, (0.0, 100000.0), scales=True),
        "Length1": AttributeSpec("length_1", float, 50.0, (0.0, 100000.0), scales=True),
        "Width2": AttributeSpec("width_2", float, 60.0, (0.0, 100000.0), scales=True),
        "Length2": AttributeSpec("length_2", float, 50.0, (0.0, 100000.0), scales=True),
        "Width3": AttributeSpec("width_3", float, 40.0, (0.0, 100000.0), scales=True),
        "ConeAngle": AttributeSpec("cone_angle", float, 0.0, (0.0, 30.0)),
        "MiddlePlane": AttributeSpec("middle_plane", float, 0.0, (0.0, 100000.0), scales=True),
        "Offset": AttributeSpec("offset", float, 30.0, (0.0, 100000.0), scales=True),
        "UseLap": AttributeSpec("use_lap", bool, True),
        "LapOffset": AttributeSpec("lap_offset", float, 10.0, (0.0, 100000.0), scales=True),
        "LapDepth": AttributeSpec("lap_depth", float, 20.0, (0.0, 100000.0), scales=True),
    }

    # the direction, seen from the shoulder and towards the remaining part, in which the tenon runs and the lap sits
    TENON_DIRECTION = -1.0
    LAP_DIRECTION = 1.0

    def _neck_and_head(self, element, margin):
        """The solids of the neck and the head, in model coordinates."""
        height = element.get_dimensions_relative_to_side(self.ref_side_index)[1]
        to_model = point_mapper(self, element)
        direction = self.TENON_DIRECTION
        overlap = min(self.length_1, self.length_2) / 2.0

        def outline(width, along):
            return [to_model(direction * along, self.start_y + y, depth) for y, depth in self._section(width, height, 2.0 * margin)]

        return [
            prism(outline(self.width_1, -overlap), outline(self.width_1, self.length_1 + overlap)),
            prism(outline(self.width_2, self.length_1), outline(self.width_3, self.length_1 + self.length_2)),
        ]

    def _section(self, width, height, margin):
        # All sections of the tenon share the centers of their round corners, at the ends of the middle plane: in the figure the corners are concentric.
        # Their common level follows from the bottom of the neck, which is at `offset`.
        cone = math.radians(self.cone_angle)
        sine, cosine, tangent = math.sin(cone), math.cos(cone), math.tan(cone)
        center = (height - self.offset - (self.width_1 - self.middle_plane) / 2.0 * cosine) / (1.0 - sine)
        radius = ((width - self.middle_plane) / 2.0 - center * tangent) * cosine
        if radius <= 0.0:
            raise ValueError("The flanks of the {} meet before they reach its middle plane, at width {}.".format(self.PROCESSING_NAME, width))

        side = [(width / 2.0 + margin * tangent, -margin)]
        for i in range(ARC_SEGMENTS + 1):
            angle = cone + (math.pi / 2.0 - cone) * i / ARC_SEGMENTS
            side.append((self.middle_plane / 2.0 + radius * math.cos(angle), center + radius * math.sin(angle)))
        return side + [(-y, depth) for y, depth in reversed(side)]

    def _trim_block(self, element, margin):
        """The part of the end of the element which is trimmed, up to the shoulder and the lap."""
        width, height = element.get_dimensions_relative_to_side(self.ref_side_index)
        to_model = point_mapper(self, element)
        end = abs(self.start_x) + element.blank_length + margin
        section = [(0.0, -margin)]
        if self.use_lap:
            lap_level = height - self.offset + self.lap_offset
            lap = self.LAP_DIRECTION * self.lap_depth
            section += [(0.0, lap_level), (lap, lap_level), (lap, height + margin)]
        else:
            section += [(0.0, height + margin)]
        section += [(-end, height + margin), (-end, -margin)]
        return prism([to_model(a, -margin, d) for a, d in section], [to_model(a, width + margin, d) for a, d in section])

    def volumes_from_params_and_element(self, element):
        """The volumes this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the flanks of a section meet before they reach `middle_plane`.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        margin = sum(element.get_dimensions_relative_to_side(self.ref_side_index)) + self.length_1 + self.length_2 + self.lap_depth
        volumes = [self._trim_block(element, margin)]
        for solid in self._neck_and_head(element, margin):
            volumes = [piece for volume in volumes for piece in Brep.from_boolean_difference(volume, solid)]
        return volumes


class JapaneseMortise(JapaneseTenon):
    """Represents a JapaneseMortise feature, the counterpart of a :class:`JapaneseTenon`. This processing trims the element.

    At `start_x` the end of the element is cut off, except for the lap which stands out by `lap_depth`. The shape of the tenon is removed from the remaining part.

    Parameters
    ----------
    See :class:`JapaneseTenon`.

    """

    PROCESSING_NAME = "JapaneseMortise"  # type: ignore

    TENON_DIRECTION = 1.0
    LAP_DIRECTION = -1.0

    def volumes_from_params_and_element(self, element):
        """The volumes this processing removes from the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the flanks of a section meet before they reach `middle_plane`.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        margin = sum(element.get_dimensions_relative_to_side(self.ref_side_index)) + self.length_1 + self.length_2 + self.lap_depth
        return [self._trim_block(element, margin)] + self._neck_and_head(element, margin)
