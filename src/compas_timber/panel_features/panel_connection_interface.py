from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import distance_line_line

from .panel_features import PanelFeature
from .panel_features import PanelFeatureType


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


class PanelConnectionInterface(PanelFeature):
    def __init__(
        self, polyline: Polyline, frame: Frame, edge_index: int | None, interface_role: InterfaceRole | str = InterfaceRole.NONE, name="PanelConnectionInterface", **kwargs
    ):
        super(PanelConnectionInterface, self).__init__(frame=frame, panel_feature_type=PanelFeatureType.CONNECTION_INTERFACE, name=name, **kwargs)
        self._polyline = polyline
        self.edge_index = edge_index  # index of the edge in the plate outline where the interface is located
        self.interface_role = interface_role if interface_role else InterfaceRole.NONE

    @property
    def __data__(self) -> dict:
        data = super(PanelConnectionInterface, self).__data__
        data["polyline"] = self._polyline
        data["edge_index"] = self.edge_index
        data["interface_role"] = self.interface_role
        return data

    @property
    def polyline(self) -> Polyline:
        """Returns the interface polyline in the coordinates of the containing Panel."""
        return self._polyline.transformed(self.transformation)

    @property
    def geometry(self) -> Polyline:
        return self.polyline

    def compute_elementgeometry(self, include_features=False) -> Polyline:
        return self._polyline

    def __repr__(self) -> str:
        return "PanelConnectionInterface({0})".format(
            self.interface_role,
        )

    def as_plane(self) -> Plane:
        """Returns the interface as a plane."""
        return Plane.from_frame(self.frame)

    @property
    def width(self) -> float:
        """Returns the width of the interface polyline."""
        return distance_line_line(self.polyline.lines[0], self.polyline.lines[2])
