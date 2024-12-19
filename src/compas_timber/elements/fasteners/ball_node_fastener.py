from compas.geometry import Brep
from compas.geometry import Sphere
from compas.geometry import Transformation
from compas.geometry import NurbsCurve
from compas.geometry import Vector


from compas_timber.elements.fastener import Fastener


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

    def __init__(self, node_point, ball_diameter=100, **kwargs):
        super(BallNodeFastener, self).__init__(**kwargs)
        self.node_point = node_point
        self.ball_diameter = ball_diameter
        self.interface_params = {}
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

    # @property
    # def shape(self):
    #     # type: () -> Brep
    #     return self.geometry

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    def __str__(self):
        return "Ball Node Fastener"

    # ==========================================================================
    # Implementations of abstract methods
    # ==========================================================================

    def compute_geometry(self):
        # type: () -> compas.geometry.Geometry
        """Returns the geometry of the fastener including all interfaces."""
        geometry = Brep.from_sphere(Sphere(self.ball_diameter / 2.0, point=self.node_point))

        for interface in self.interfaces:
            geometry += interface.geometry
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
        """Generate a plate from outline, thickness, and holes."""
        if not self.outline:
            return None
        if isinstance(self.outline, NurbsCurve):
            outline = self.outline
        else:
            outline = NurbsCurve.from_points(self.outline, degree=1)
        plate = Brep.from_extrusion(outline, Vector(0.0, 0.0, 1.0) * self.thickness)
        for hole in self.holes:
            frame = Frame(hole["point"], self.frame.xaxis, self.frame.yaxis)
            hole = Brep.from_cylinder(Cylinder(hole["diameter"] / 2, self.thickness * 2, frame))
            plate -= hole
        return plate

    @property
    def interface_shape(self):
        """Return a Brep representation of the interface located at the WorldXY origin."""
        if not self._interface_shape:
            geometries = []
            if self.plate:
                geometries.append(self.plate)
            for shape in self.interface_shapes:
                if isinstance(shape, Brep):
                    geometries.append(shape)
                else:
                    geometries.append(shape.to_brep())
            self._interface_shape = geometries[0]
            for geometry in geometries[1:]:
                self._interface_shape += geometry
        return self._interface_shape

    @property
    def geometry(self):
        """returns the geometry of the interface in the model (oriented on the timber element)"""
        return self.shape.transformed(Transformation.from_frame(self.frame))
