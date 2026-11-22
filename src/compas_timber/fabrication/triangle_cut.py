from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import intersection_plane_plane_plane
from compas.tolerance import TOL
from compas_brep import Brep

from .btlx import AttributeSpec
from .btlx import ParametricProcessing


class TriangleCut(ParametricProcessing):
    """Cuts the wedge between two planes out of the element.

    Both planes pass through the point given by `start_x`, `start_y` and `start_depth`. Their normals point into the removed wedge.

    Parameters
    ----------
    start_x : float
        Distance of the common point along the reference edge.
    start_y : float
        Distance of the common point from the reference edge.
    start_depth : float
        Distance of the common point below the reference side.
    normal_1_x : float
        X component of the normal of the first plane, in the coordinate system of the reference side, whose Z axis points out of the element.
    normal_1_y : float
        Y component of the normal of the first plane.
    normal_1_z : float
        Z component of the normal of the first plane.
    normal_2_x : float
        X component of the normal of the second plane, in the coordinate system of the reference side.
    normal_2_y : float
        Y component of the normal of the second plane.
    normal_2_z : float
        Z component of the normal of the second plane.
    **kwargs : dict, optional
        Additional keyword arguments of :class:`~compas_timber.fabrication.BTLxProcessing`.

    """

    PROCESSING_NAME = "TriangleCut"  # type: ignore
    ATTRIBUTE_MAP = {
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "StartY": AttributeSpec("start_y", float, 60.0, (-50000.0, 50000.0), scales=True),
        "StartDepth": AttributeSpec("start_depth", float, 60.0, (-50000.0, 50000.0), scales=True),
        "Normal1X": AttributeSpec("normal_1_x", float, 1.0, (-50000.0, 50000.0)),
        "Normal1Y": AttributeSpec("normal_1_y", float, 0.0, (-50000.0, 50000.0)),
        "Normal1Z": AttributeSpec("normal_1_z", float, 0.0, (-50000.0, 50000.0)),
        "Normal2X": AttributeSpec("normal_2_x", float, 1.0, (-50000.0, 50000.0)),
        "Normal2Y": AttributeSpec("normal_2_y", float, 0.0, (-50000.0, 50000.0)),
        "Normal2Z": AttributeSpec("normal_2_z", float, 0.0, (-50000.0, 50000.0)),
    }

    @classmethod
    def from_planes_and_element(cls, planes, element, ref_side_index=0, **kwargs):
        """Construct a TriangleCut from two planes, whose normals point into the volume to remove.

        Parameters
        ----------
        planes : tuple(:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`)
            The two non-parallel planes.
        element : :class:`~compas_timber.base.TimberElement`
            The element to cut.
        ref_side_index : int, optional
            The index of the reference side the parameters refer to.
        **kwargs : dict, optional
            Additional keyword arguments of the processing.

        Returns
        -------
        :class:`~compas_timber.fabrication.TriangleCut`

        """
        ref_side = element.ref_sides[ref_side_index]
        plane_1, plane_2 = planes
        direction = plane_1.normal.cross(plane_2.normal)
        if TOL.is_zero(direction.length):
            raise ValueError("The planes of a TriangleCut must not be parallel.")

        start = ref_side.to_local_coordinates(Point(*intersection_plane_plane_plane(plane_1, plane_2, Plane(ref_side.point, direction))))
        normal_1 = ref_side.to_local_coordinates(plane_1.normal)
        normal_2 = ref_side.to_local_coordinates(plane_2.normal)
        return cls(
            start_x=start.x,
            start_y=start.y,
            start_depth=-start.z,
            normal_1_x=normal_1.x,
            normal_1_y=normal_1.y,
            normal_1_z=normal_1.z,
            normal_2_x=normal_2.x,
            normal_2_y=normal_2.y,
            normal_2_z=normal_2.z,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @classmethod
    def from_shapes_and_element(cls, plane_a, plane_b, element, **kwargs):
        """Construct a TriangleCut from two planes, see :meth:`from_planes_and_element`."""
        return cls.from_planes_and_element((plane_a, plane_b), element, **kwargs)

    def volumes_from_params_and_element(self, element):
        """The wedge between the two planes, large enough to leave the element.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If a normal has no length.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        normal_1 = Vector(self.normal_1_x, self.normal_1_y, self.normal_1_z)
        normal_2 = Vector(self.normal_2_x, self.normal_2_y, self.normal_2_z)
        if not normal_1.length or not normal_2.length:
            raise ValueError("The normals of a TriangleCut must not be zero.")

        start = Point(self.start_x, self.start_y, -self.start_depth)
        size = 2.0 * (element.blank_length + element.width + element.height + abs(self.start_x) + abs(self.start_y) + abs(self.start_depth))
        volume = Brep.from_box(Box(size, size, size, Frame(start, [1.0, 0.0, 0.0], [0.0, 1.0, 0.0])))
        # Brep.trimmed() keeps what is behind the plane, a wedge from identical normals (the default) is simply a half-space
        volume = volume.trimmed(Plane(start, normal_1 * -1.0)).trimmed(Plane(start, normal_2 * -1.0))
        return [volume.transformed(Transformation.from_frame(element.ref_sides[self.ref_side_index]))]
