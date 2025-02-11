# TODO: move this to compas_timber.fasteners
from compas.data import Data
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Transformation
from compas.geometry import Vector

from compas_timber.elements.timber import TimberElement
from compas_timber.fabrication import Drilling
from compas_timber.utils import intersection_line_beam_param


class Fastener(TimberElement):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    TODO: we should rethink this class. it is not entirely clear if it's an abstract class or a generic fastener.
    It inherits from TimberElement/Element but does not implement the appropriate methods.

    Parameters
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, shape=None, frame=None, **kwargs):
        super(Fastener, self).__init__(**kwargs)
        self._shape = shape
        self.interfaces = []
        self.frame = frame
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Fastener(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<Fastener {}>".format(self.name)

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame

    @property
    def is_fastener(self):
        return True

    @property
    def key(self):
        # type: () -> int | None
        return self.graph_node

    @property
    def __data__(self):
        return {
            "shape": self._shape,
            "frame": self.frame,
            "interfaces": self.interfaces,
        }

    def compute_geometry(self):
        """returns the geometry of the fastener in the model"""
        return self.shape.transformed(Transformation.from_frame(self.frame))


class FastenerTimberInterface(Data):
    """A class to represent the interface between a fastener and a timber element.

    # TODO: we need to put some thought as to what's the minimal representation of an interface.
    # TODO: the responsibilities of the Fastener-based-joint vs. Fastener vs. FastenerTimberInterface should be perhaps more clearly defined
    # TODO: prehaps it would make sense to move stuff over from here to the BallNodeJoint
    # TODO: while it attempts to be generic, it is tightly coupled with the BallNodeJoint.
    # TODO: what is the differece between the outline and the shapes? they seem to all just result in geometry.

    Parameters
    ----------
    outline_points : List of :class:`~compas.geometry.Point`
        The points of the polyline outline of the fastener geometry.
    thickness : float
        The thickness of the fastener plate.
    holes : list of dict, optional
        The holes of the fastener. Structure is as follows:
        {
        "point": compas.geometry.Point,
        "diameter": float,
        "vector": compas.geometry.Vector, optional, if none, the hole is assumed to be perpendicular to the frame
        "through": bool, optional, if True, the hole goes through the timber element
        }
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
    shapes : :class:`~compas.geometry.Geometry`
        Input for extra geometric elements. These should be solids that can be booleaned with the fastener geometry.
    features : list of :class:`~compas_timber.fabrication.BTLxFromGeometryDefinition
        The features that are applied by this interface to the timber element. The features are defined in world coordinates.

    Attributes
    ----------
    outline_points : List of :class:`~compas.geometry.Point`
        The points of the polyline outline of the fastener geometry.
    thickness : float
        The thickness of the fastener plate.
    holes : list of dict, optional
        The holes of the fastener. Structure is as follows:
        {
        "point": compas.geometry.Point,
        "diameter": float,
        "vector": compas.geometry.Vector, optional, if none, the hole is assumed to be perpendicular to the frame
        "through": bool, optional, if True, the hole goes through the timber element
        }
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
    features : list of :class:`~compas_timber.fabrication.BTLxFromGeometryDefinition
        The features that are applied by this interface to the timber element. This returns the features in world coordinates.


    """

    def __init__(self, outline_points=None, thickness=None, holes=None, shapes=None, frame=None, element=None, features=None):
        super(FastenerTimberInterface, self).__init__()
        self.outline_points = outline_points
        self.thickness = thickness
        self.holes = holes or []
        self.frame = frame or Frame.worldXY()
        self.element = element
        self.shapes = shapes or []
        self.features = []
        if features:
            for feat in features:
                if feat.elements:
                    fc = feat.copy()
                    fc.elements = None
                    self.features.append(fc)
                else:
                    self.features.append(feat)
        self._shape = None

    def __str__(self):
        return "FastenerTimberInterface at {}".format(self.frame)

    @property
    def __data__(self):
        return {
            "outline_points": self.outline_points,
            "thickness": self.thickness,
            "holes": self.holes,
            "frame": self.frame,
            "element": self.element,
            "shapes": self.shapes,
            "features": self.features,
        }

    def get_features(self, element):
        """Add a feature to the interface."""
        features = []
        for hole in self.holes:
            features.append(self._get_hole_feature(hole, element))
        # TODO: this uses the obsolete Feature classes, we should replace these with deffered BTLx
        for feature in self.features:
            feat = feature.transformed(Transformation.from_frame(self.frame))
            features.append(feat.feature_from_element(element))
        return features

    def _get_hole_feature(self, hole, element):
        """Get the line that goes through the timber element. Goes through the element.
        If depth is required, holes should be added as Drilling features to the interface."""
        vector = hole.get("vector", None) or Vector(0.0, 0.0, 1.0)
        drill_line = Line.from_point_and_vector(hole["point"], vector)
        drill_line.transform(Transformation.from_frame(self.frame))
        pts, _ = intersection_line_beam_param(drill_line, element)
        if pts:
            drill_line = Line(*pts)
        # TODO: this uses the obsolete Feature classes, we should replace these with deffered BTLx
        return Drilling.from_line_and_element(drill_line, element, hole["diameter"])
