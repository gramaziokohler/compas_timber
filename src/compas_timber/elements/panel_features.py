from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import NurbsCurve
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import distance_line_line
from compas.geometry import intersection_line_plane

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import correct_polyline_direction


class PanelFeature(Data):
    # TODO: should this inherit from Element?
    def __init__(self, frame, name=None):
        super(PanelFeature, self).__init__()
        self.transformation = Transformation.from_frame(frame)
        self.name = name

    @property
    def __data__(self):
        data = {"frame": self.frame}
        return data

    @property
    def frame(self):
        return Frame.from_transformation(self.transformation)

    def transform(self, transformation):
        self.transformation = transformation * self.transformation

    def transformed(self, transformation):
        new = self.copy()
        new.transform(transformation)
        return new


class Opening(PanelFeature):
    def __init__(self, frame, outline_a, outline_b, opening_type=None, name="Opening"):
        super(Opening, self).__init__(frame=frame, name=name)
        self._outline_a = outline_a
        self._outline_b = outline_b
        self.opening_type = opening_type or OpeningType.WINDOW
        self._shape = None

    @property
    def outline_a(self):
        return self._outline_a.transformed(self.transformation)

    @property
    def outline_b(self):
        return self._outline_b.transformed(self.transformation)

    @property
    def geometry(self):
        return [self.outline_a, self.outline_b]

    @property
    def __data__(self):
        data = super(Opening, self).__data__
        data["outline_a"] = self._outline_a
        data["outline_b"] = self._outline_b
        return data

    @property
    def shape(self):
        if not self._shape:
            positive_vector = Vector.from_start_end(self._outline_a[0], self._outline_b[0])
            outline_a = correct_polyline_direction(self._outline_a, positive_vector, clockwise=True)
            outline_b = correct_polyline_direction(self._outline_b, positive_vector, clockwise=True)
            self._shape = Brep.from_loft([NurbsCurve.from_points(pts, degree=1) for pts in (outline_a, outline_b)])
            self._shape.cap_planar_holes()
        return self._shape

    def apply(self, panel_geometry, panel):
        """Applies the opening to the given panel geometry.

        Parameters
        ----------
        panel_geometry : :class:`compas.geometry.Brep`
            The geometry of the panel to which the opening will be applied.
        panel : :class:`compas_timber.elements.Panel`
            The panel element.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The modified panel geometry with the opening applied.

        Raises
        ------
        :class:`compas_timber.errors.FeatureApplicationError`
            If the opening cannot be applied to the panel geometry.

        """
        try:
            panel_geometry -= self.shape.transformed(self.transformation)
            return panel_geometry
        except Exception as e:
            raise FeatureApplicationError(panel_geometry, self.shape, f"Failed to apply opening to panel geometry: {e}")

    @classmethod
    def from_outline_panel(cls, outline, panel, opening_type=None, project_horizontal=False, name=None):
        """Creates an opening from a single outline and a panel.

        The outline defined locally relative to the panel frame. The outline is projected
        onto the outline_a side of the panel.

        Parameters
        ----------
        outline : :class:`compas.geometry.Polyline`
            The outline of the opening.
        panel : :class:`compas_timber.elements.Panel`
            The panel in which the opening is located.
        name : str, optional
            The name of the opening.

        Returns
        -------
        :class:`Opening`
            The created opening.
        """
        # project outline onto top and bottom faces of panel
        outline.transform(panel.modeltransformation.inverse())
        box = Box.from_points(outline.points)
        frame = Frame(box.points[0], Vector(1, 0, 0), Vector(0, 1, 0))
        pts_a = []
        pts_b = []
        if project_horizontal:
            vector = Vector(panel.frame.normal[0], panel.frame.normal[1], 0).transformed(panel.modeltransformation.inverse())
            for pt in outline.points:
                line = Line.from_point_and_vector(pt, vector)
                intersection_a = intersection_line_plane(line, Plane.worldXY())
                if intersection_a:
                    pts_a.append(intersection_a)
                else:
                    raise ValueError("Could not project opening outline point onto panel inner plane.")
                intersection_b = intersection_line_plane(line, Plane(Point(0, 0, panel.thickness), Vector(0, 0, 1)))
                if intersection_b:
                    pts_b.append(intersection_b)
                else:
                    raise ValueError("Could not project opening outline point onto panel outer plane.")
        else:
            for pt in outline.points:
                pts_a.append(Point(pt[0], pt[1], 0))  # project to panel.planes[0]/panel.outline_a
                pts_b.append(Point(pt[0], pt[1], panel.thickness))
        pl_a = Polyline(pts_a).transformed(Transformation.from_frame(frame).inverse())
        pl_b = Polyline(pts_b).transformed(Transformation.from_frame(frame).inverse())
        return cls(frame, pl_a, pl_b, opening_type=opening_type, name=name)


class OpeningType(object):
    """Constants for different types of openings in walls.

    Attributes
    ----------
    DOOR : str
        Constant for door openings.
    WINDOW : str
        Constant for window openings.
    """

    DOOR = "door"
    WINDOW = "window"


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


class PanelConnectionInterface(PanelFeature):
    def __init__(self, polyline, frame, edge_index, topology, interface_role=None, name="PanelConnectionInterface"):
        super(PanelConnectionInterface, self).__init__(frame=frame, name=name)
        self._polyline = polyline
        self.edge_index = edge_index  # index of the edge in the plate outline where the interface is located
        self.topology = topology  # TODO: don't like this here
        self.interface_role = interface_role if interface_role else InterfaceRole.NONE

    @property
    def __data__(self):
        data = super(PanelConnectionInterface, self).__data__
        data["polyline"] = self._polyline
        data["frame"] = self.frame
        data["edge_index"] = self.edge_index
        data["topology"] = self.topology
        data["interface_role"] = self.interface_role
        return data

    @property
    def polyline(self):
        return self._polyline.transformed(self.transformation)

    @property
    def geometry(self):
        return [self.polyline]

    def __repr__(self):
        return "PanelConnectionInterface({0}, {1})".format(
            self.interface_role,
            self.topology,
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


class LinearService(PanelFeature):
    def __init__(self, frame, polyline, name="LinearService"):
        super(LinearService, self).__init__(frame=frame, name=name)
        self._polyline = polyline

    @property
    def polyline(self):
        return self._polyline.transformed(self.transformation)

    @property
    def __data__(self):
        data = super(LinearService, self).__data__
        data["polyline"] = self._polyline
        return data

    @property
    def geometry(self):
        return [self.polyline]


class VolumetricService(PanelFeature):
    def __init__(self, frame, volume, name="VolumetricService"):
        super(VolumetricService, self).__init__(frame=frame, name=name)
        self._volume = volume

    def __data__(self):
        data = super(VolumetricService, self).__data__
        data["volume"] = self.volume
        return data

    @property
    def volume(self):
        return self._volume.transformed(self.transformation)

    @property
    def geometry(self):
        return [self.volume]
