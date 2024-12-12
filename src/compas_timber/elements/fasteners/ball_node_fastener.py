from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Sphere
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

    def add_interface(self, beam, interface):
        # type: (compas_timber.parts.Beam, FastenerTimberInterface) -> None
        """Adds an interface to the fastener.

        Parameters
        ----------
        beam : :class:`~compas_timber.parts.Beam`
            The beam to which the interface is added.
        interface : :class:`~compas_timber.elements.FastenerTimberInterface`
            The interface to be added.

        """
        interface = interface.copy()
        interface.element = beam
        pt = beam.centerline.closest_point(self.node_point)

        # TODO: this is where the interface is places relative to the beam, a bit hidden here..
        interface.frame = Frame(pt, Vector.from_start_end(pt, beam.midpoint), beam.frame.zaxis)
        self.interfaces.append(interface)

    def compute_collision_mesh(self):
        # type: () -> compas.datastructures.Mesh
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.shape.to_mesh()
