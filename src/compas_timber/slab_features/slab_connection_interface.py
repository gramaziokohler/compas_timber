from compas.geometry import Plane
from compas.geometry import distance_line_line

from .slab_features import SlabFeature
from .slab_features import SlabFeatureType


class InterfaceRole(object):
    """
    Enumeration of the possible interface roles.

    Attributes
    ----------
    MAIN : literal("MAIN")
        The interface is the main interface.
    CROSS : literal("CROSS")
        The interface is the cross interface.
    NONE : literal("NONE")
        The interface has no specific role. E.g. when a miter joint is used.
    """

    MAIN = "MAIN"
    CROSS = "CROSS"
    NONE = "NONE"  # TODO: add a "MITER" role?


class SlabConnectionInterface(SlabFeature):
    def __init__(self, polyline, frame, edge_index, topology, interface_role=None, name="SlabConnectionInterface"):
        super(SlabConnectionInterface, self).__init__(frame=frame, slab_feature_type=SlabFeatureType.CONNECTION_INTERFACE, name=name)
        self._polyline = polyline
        self.edge_index = edge_index  # index of the edge in the plate outline where the interface is located
        # self.topology = topology  # TODO: don't like this here
        self.interface_role = interface_role if interface_role else InterfaceRole.NONE

    @property
    def __data__(self):
        data = super(SlabConnectionInterface, self).__data__
        data["polyline"] = self._polyline
        data["frame"] = self.frame
        data["edge_index"] = self.edge_index
        # data["topology"] = self.topology
        data["interface_role"] = self.interface_role
        return data

    @property
    def polyline(self):
        return self._polyline.transformed(self.transformation)

    @property
    def geometry(self):
        return [self.polyline]

    def __repr__(self):
        return "SlabConnectionInterface({0})".format(
            self.interface_role,
            # self.topology,
        )

    def as_plane(self):
        """Returns the interface as a plane.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The plane of the interface.
        """
        return Plane.from_frame(self.frame)

    @property
    def width(self):
        """Returns the width of the interface polyline."""
        return distance_line_line(self.polyline.lines[0], self.polyline.lines[2])
