import math

from compas.geometry import Cone
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Sphere as SphereGeometry
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_brep import Brep

from compas_timber.geometry import brep_difference_first

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing


class Sphere(ParametricProcessing):
    """Mills a section of a sphere out of the element, centered on an axis parallel to the element's axis.

    The element keeps the sphere section. On both sides of it the removal runs out to the surface of the element in a cone.

    Parameters
    ----------
    orientation : str
        `start` if the sphere lies towards the element's end from the start point, `end` if it lies towards the element's start.
    start_x : float
        Distance along the reference edge to the point of the sphere on its axis.
    start_y : float
        Distance from the reference edge to the axis of the sphere.
    start_depth : float
        Distance from the reference side to the axis of the sphere.
    length : float
        Length, along the axis, of the sphere section.
    radius : float
        Radius of the sphere.
    start_offset : float
        Distance along the axis, from the start point to the sphere section.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "Sphere"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 60.0, (-50000.0, 50000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 60.0, (-50000.0, 50000.0), scales=True),
        "Length": AttributeSpec("length", float, 50.0, (0.0, 50000.0), scales=True),
        "Radius": AttributeSpec("radius", float, 50.0, (0.0, 50000.0), scales=True),
        "StartOffset": AttributeSpec("start_offset", float, 0.0, (0.0, 50000.0), scales=True),
    }

    @classmethod
    def from_sphere_and_element(cls, sphere, element, ref_side_index=0, **kwargs):
        """Construct a Sphere processing which keeps the whole of a sphere.

        Parameters
        ----------
        sphere : :class:`~compas.geometry.Sphere`
            The sphere.
        element : :class:`~compas_timber.base.TimberElement`
            The element to cut.
        ref_side_index : int, optional
            The index of the reference side the parameters refer to.
        **kwargs : dict, optional
            Additional keyword arguments of the processing.

        Returns
        -------
        :class:`~compas_timber.fabrication.Sphere`

        """
        center = element.ref_sides[ref_side_index].to_local_coordinates(sphere.frame.point)
        return cls(
            start_x=center.x - sphere.radius,
            start_y=center.y,
            start_depth=-center.z,
            length=2.0 * sphere.radius,
            radius=sphere.radius,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, sphere, element, **kwargs):
        """Construct a Sphere processing from a sphere, see :meth:`from_sphere_and_element`."""
        return cls.from_sphere_and_element(sphere, element, **kwargs)

    def _circle_radius(self, distance):
        """The radius of the sphere's circle at a distance along the axis from its start point."""
        return math.sqrt(distance * (2.0 * self.radius - distance))

    def volumes_from_params_and_element(self, element):
        """The volumes around the sphere section and around the two cones next to it.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the sphere section does not fit on the sphere.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volumes, in model coordinates.

        """
        near = self.start_offset
        far = near + self.length
        if far > 2.0 * self.radius:
            raise ValueError("The section of the Sphere ends beyond the sphere. Offset and length: {}, diameter: {}".format(far, 2.0 * self.radius))

        # Z runs along the axis, from the start point to the sphere
        side = 1.0 if self.orientation == OrientationType.START else -1.0
        axis_frame = Frame(Point(self.start_x, self.start_y, -self.start_depth), Vector(0.0, side, 0.0), Vector(0.0, 0.0, 1.0))
        to_model = Transformation.from_frame(element.ref_sides[self.ref_side_index]) * Transformation.from_frame(axis_frame)

        reach = element.width + element.height + abs(self.start_y) + abs(self.start_depth) + self.radius
        sphere = Brep.from_sphere(SphereGeometry(self.radius, point=[0.0, 0.0, self.radius]))
        section = Brep.from_cylinder(Cylinder(reach, self.length, Frame([0.0, 0.0, 0.5 * (near + far)], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))

        # shortcut: the opening angles of the cones (A1, A2) are machine settings and not in BTLx, so this is the 90 degrees of the figure. Upgrade if machines must be matched
        near_radius = self._circle_radius(near)
        far_radius = self._circle_radius(far)
        near_cone = Cone(3.0 * reach + near_radius, 3.0 * reach + near_radius, Frame([0.0, 0.0, near - 3.0 * reach], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]))
        far_cone = Cone(3.0 * reach + far_radius, 3.0 * reach + far_radius, Frame([0.0, 0.0, far + 3.0 * reach], [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]))
        near_side = Brep.from_cylinder(Cylinder(reach, 2.0 * reach, Frame([0.0, 0.0, near - reach], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))
        far_side = Brep.from_cylinder(Cylinder(reach, 2.0 * reach, Frame([0.0, 0.0, far + reach], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))

        volumes = [
            brep_difference_first(section, sphere),
            brep_difference_first(near_side, Brep.from_cone(near_cone)),
            brep_difference_first(far_side, Brep.from_cone(far_cone)),
        ]
        return [volume.transformed(to_model) for volume in volumes]
