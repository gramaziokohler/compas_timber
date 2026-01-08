from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.panel_features import PanelFeatureType

from .plate_geometry import PlateGeometry


class PanelType(object):
    """Constants for different types of panels.

    Attributes
    ----------
    WALL : str
        Constant for wall panels.
    FLOOR : str
        Constant for floor panels.
    ROOF : str
        Constant for roof panels.
    GENERIC : str
        Constant for generic panels.
    """

    WALL = "wall"
    FLOOR = "floor"
    ROOF = "roof"
    GENERIC = "generic"


class Panel(PlateGeometry, Element):
    """Represents a timber panel element (wall, floor, roof, etc.).

    Serves as container for beams, plates, and other related elements and groups them together to form a panel.
    A panel is often a single unit of prefabricated timber element.
    It is often referred to as an enveloping body.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this panel.
    length : float
        Length of the panel.
    width : float
        Width of the panel.
    thickness : float
        Thickness of the panel.
    local_outline_a: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the principal outline of this panel.
    local_outline_b: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the associated outline of this panel.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this panel.
    name : str, optional
        Name of the panel. Defaults to "Panel".
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this panel.
    length : float
        Length of the panel.
    width : float
        Width of the panel.
    height : float
        Height (thickness) of the panel.
    thickness : float
        Thickness of the panel.
    name : str
        Name of the panel.
    interfaces : list
        List of interfaces associated with this panel.
    attributes : dict
        Dictionary of additional attributes.
    is_group_element : bool
        Always True for panels as they can contain other elements.

    """

    @property
    def __data__(self):
        data = super(PlateGeometry, self).__data__
        data.update(super().__data__)
        data["frame"] = Frame.from_transformation(data.pop("transformation"))
        data["length"] = self.length
        data["width"] = self.width
        data["thickness"] = self.height
        data["name"] = self.name
        data["features"] = [f for f in self.features if f.panel_feature_type != PanelFeatureType.CONNECTION_INTERFACE]
        return data

    def __init__(self, frame, length, width, thickness, local_outline_a=None, local_outline_b=None, openings=None, type=None, **kwargs):
        Element.__init__(self, transformation=Transformation.from_frame(frame) if frame else Transformation(), **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b, openings=openings)
        self.length = length
        self.width = width
        self.height = thickness
        self.type = type or PanelType.GENERIC
        self.attributes = {}
        self.attributes.update(kwargs)

    def __repr__(self):
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    def __str__(self):
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    @property
    def interfaces(self):
        """list[:class:`~compas_timber.panel_features.PanelConnectionInterface`]: The interfaces associated with this panel."""
        return [f for f in self.features if f.panel_feature_type == PanelFeatureType.CONNECTION_INTERFACE]

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        PlateGeometry.reset(self)  # reset outline_a and outline_b
        self._features = []
        self.debug_info = []

    @reset_computed
    def remove_features(self, features=None):
        # type: (Optional[Union["PanelConnectionInterface", list["PanelConnectionInterface"]]]) -> None
        """Removes interfaces from the element.

        Parameters
        ----------
        interfaces : :class:`~compas_timber.panel_features.PanelConnectionInterface` | list[:class:`~compas_timber.panel_features.PanelConnectionInterface`], optional
            The interfaces to be removed. If None, all interfaces will be removed.

        """
        if features is None:
            self._features = []
        else:
            if not isinstance(features, list):
                features = [features]
            self._features = [f for f in self.features if f not in features]

    @property
    def is_group_element(self):
        return True

    def compute_modeltransformation(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()  # type: ignore

    def compute_modelgeometry(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)  # type: ignore
        return super().compute_modelgeometry()  # type: ignore

    def compute_elementgeometry(self, include_features=False):
        """Compute the geometry of the element at local coordinates."""
        return self.compute_shape()

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        """
        Constructs a Panel from two polyline outlines. to be implemented to instantialte Plates and Panels.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the panel geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the panel geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the panel geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        kwargs.update(args)
        return cls(**kwargs)
