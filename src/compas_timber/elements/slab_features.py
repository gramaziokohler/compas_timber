from compas.geometry import Brep
from compas.geometry import NurbsCurve
from compas.geometry import distance_line_line
from compas.geometry import Plane

from compas.data import Data

from compas_timber.utils import correct_polyline_direction

class SlabFeature(Data):
    def __init__(self,name=None):
        self.name=name

    def __data__(self):
        return {"name": self.name}

class Opening(SlabFeature):
    def __init__(self, outline_a, outline_b, name=None):
        super(Opening, self).__init__(name=name)
        self.outline_a = outline_a
        self.outline_b = outline_b

    @property
    def __data__(self):
        data = super(Opening, self).__data__
        data["outline_a"] = self.outline_a
        data["outline_b"] = self.outline_b
        return data

    @property
    def volume(self):
        outline_a = correct_polyline_direction(self.outline_a, self.frame.normal, clockwise=True)
        outline_b = correct_polyline_direction(self.outline_b, self.frame.normal, clockwise=True)
        plate_geo = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (outline_a, outline_b)])
        plate_geo.cap_planar_holes()
        return plate_geo


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
    NONE = "NONE"
    
class SlabConnectionInterface(object):
    def __init__(self, polyline, frame, edge_index, topology, opposite_slab_planes, interface_role=None):
        self.polyline = polyline
        self.frame = frame
        self.edge_index = edge_index  # index of the edge in the plate outline where the interface is located
        self.topology = topology  # TODO: don't like this here
        self.opposite_slab_planes = opposite_slab_planes  # planes of the opposite slab at the interface
        self.interface_role = interface_role if interface_role else InterfaceRole.NONE


    def __repr__(self):
        return "SlabConnectionInterface({0}, {1})".format(
            self.interface_role,
            JointTopology.get_name(self.topology),
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

class LinearService(SlabFeature):
    def __init__(self, polyline, name=None):
        super(LinearService, self).__init__(name=name)
        self.polyline=polyline

class VolumetricService(SlabFeature):
    def __init__(self, volume, name=None):
        super(VolumetricService, self).__init__(name=name)
        self.volume=volume