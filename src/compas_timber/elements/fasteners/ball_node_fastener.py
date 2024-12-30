from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed

from compas_timber.elements import CutFeature
from compas_timber.elements import Fastener
from compas_timber.elements import FastenerTimberInterface


class BallNodeFastener(Fastener):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    #TODO: finish this docstring

    Parameters
    ----------
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this fastener.
    elements : list(:class:`~compas_timber.parts.Element`)
        The elements that are connected with this fastener.

    """

    @property
    def __data__(self):
        data = super(Fastener, self).__data__
        return data

    def __init__(self, node_point, ball_diameter=100, base_interface=None, **kwargs):
        super(BallNodeFastener, self).__init__(**kwargs)
        self.node_point = node_point
        self.ball_diameter = ball_diameter
        self._base_interface = base_interface
        self._interface_shape = None
        self.interfaces = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "ball node fastener with {} interfaces".format(len(self.interfaces))

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_fastener(self):
        return True

    @property
    def base_interface(self):
        return self._base_interface if self._base_interface else self._default_interface()

    @base_interface.setter
    def base_interface(self, base_interface):
        self._base_interface = base_interface

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    def __str__(self):
        return "Ball Node Fastener"

    def _default_interface(self):
        height = self.ball_diameter
        thickness = height / 10.0
        shape = Cylinder(height / 8.0, height * 2.0, Frame(Point(height * 1.0, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)))
        cut_feature = CutFeature(Plane((height * 2.0, 0, 0), (-1, 0, 0)))
        outline_points = [
            Point(height * 2.0, -height / 2, -thickness / 2),
            Point(height * 2.0, height / 2, -thickness / 2),
            Point(height * 4.0, height / 2, -thickness / 2),
            Point(height * 4.0, -height / 2, -thickness / 2),
            Point(height * 2.0, -height / 2, -thickness / 2),
        ]

        return FastenerTimberInterface(outline_points, thickness, shapes=[shape], features=[cut_feature])

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_geometry(self):
        # type: () -> compas.geometry.Geometry
        """Returns the geometry of the fastener including all interfaces."""
        geometry = Brep.from_sphere(Sphere(self.ball_diameter / 2.0, point=self.node_point))

        for interface in self.interfaces:
            interface_geometry = self.interface_shape.transformed(Transformation.from_frame(interface.frame))
            geometry += interface_geometry
        return geometry

    # TODO: implement compute_aabb()
    # TODO: implement compute_obb()

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.shape.to_mesh()

    @property
    def interface_plate(self):
        """Generate a plate from outline_points, thickness, and holes."""
        outline_points = correct_polyline_direction(self.base_interface.outline_points, Vector(0, 0, 1))
        outline = NurbsCurve.from_points(outline_points, degree=1)
        holes = self.base_interface.holes
        thickness = self.base_interface.thickness
        if not outline:
            return None
        plate = Brep.from_extrusion(outline, Vector(0.0, 0.0, 1.0) * thickness)
        for hole in holes:
            frame = Frame(hole["point"], Vector(1, 0, 0), Vector(0, 1, 0))
            hole = Brep.from_cylinder(Cylinder(hole["diameter"] / 2, thickness * 2, frame))
            plate -= hole
        return plate

    @property
    def interface_shape(self):
        """Return a Brep representation of the interface located at the WorldXY origin."""
        if not self._interface_shape:
            geometries = []
            if self.interface_plate:
                geometries.append(self.interface_plate)
            for shape in self.base_interface.shapes:
                if isinstance(shape, Brep):
                    geometries.append(shape)
                else:
                    geometries.append(shape.to_brep())
            if geometries:
                self._interface_shape = geometries[0]
                for geometry in geometries[1:]:
                    self._interface_shape += geometry
        return self._interface_shape


def correct_polyline_direction(polyline, normal_vector):
    """Corrects the direction of a polyline to be counter-clockwise around a given vector.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The polyline to correct.

    Returns
    -------
    :class:`compas.geometry.Polyline`
        The corrected polyline.

    """
    angle_sum = 0
    for i in range(len(polyline) - 1):
        u = Vector.from_start_end(polyline[i - 1], polyline[i])
        v = Vector.from_start_end(polyline[i], polyline[i + 1])
        angle = angle_vectors_signed(u, v, normal_vector)
        angle_sum += angle
    if angle_sum > 0:
        polyline = polyline[::-1]
    return polyline
