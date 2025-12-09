from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.design import SlabConnectionInterface

from .plate_geometry import PlateGeometry


class SlabType(object):
    """Constants for different types of slabs.

    Attributes
    ----------
    WALL : str
        Constant for wall slabs.
    FLOOR : str
        Constant for floor slabs.
    ROOF : str
        Constant for roof slabs.
    GENERIC : str
        Constant for generic slabs.
    """

    WALL = "wall"
    FLOOR = "floor"
    ROOF = "roof"
    GENERIC = "generic"


class Slab(PlateGeometry, Element):
    """Represents a timber slab element (wall, floor, roof, etc.).

    Serves as container for beams, plates, and other related elements and groups them together to form a slab.
    A slab is often a single unit of prefabricated timber element.
    It is often referred to as an enveloping body.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this slab.
    length : float
        Length of the slab.
    width : float
        Width of the slab.
    thickness : float
        Thickness of the slab.
    local_outline_a: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the principal outline of this slab.
    local_outline_b: :class:`~compas.geometry.Polyline`, optional
        A polyline representing the associated outline of this slab.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this slab.
    name : str, optional
        Name of the slab. Defaults to "Slab".
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this slab.
    length : float
        Length of the slab.
    width : float
        Width of the slab.
    height : float
        Height (thickness) of the slab.
    thickness : float
        Thickness of the slab.
    name : str
        Name of the slab.
    interfaces : list
        List of interfaces associated with this slab.
    attributes : dict
        Dictionary of additional attributes.
    is_group_element : bool
        Always True for slabs as they can contain other elements.

    """

    @property
    def __data__(self):
        data = Element.__data__(self)
        data.update(PlateGeometry.__data__(self))
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["name"] = self.name
        return data

    def __init__(self, frame, length, width, thickness, local_outline_a=None, local_outline_b=None, openings=None, type=None, name=None, **kwargs):
        Element.__init__(self, transformation=Transformation.from_frame(frame) if frame else Transformation(), name=name, **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b, openings=openings)
        self.length = length
        self.width = width
        self.height = thickness
        self.interfaces = []
        self.type = type or SlabType.GENERIC
        self.attributes = {}
        self.attributes.update(kwargs)

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    def __str__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    @property
    def interfaces(self):
        """list[:class:`~compas_timber.elements.SlabConnectionInterface`]: The interfaces associated with this slab."""
        return [f for f in self.features if isinstance(f, SlabConnectionInterface)]
     
    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        PlateGeometry.reset(self)  # reset outline_a and outline_b
        self.features = []
        self.debug_info = []

    @reset_computed
    def remove_interfaces(self, interfaces=None):
        # type: (None | SlabConnectionInterface | list[SlabConnectionInterface]) -> None
        """Removes interfaces from the element.

        Parameters
        ----------
        interfaces : :class:`~compas_timber.elements.SlabConnectionInterface` | list[:class:`~compas_timber.elements.SlabConnectionInterface`], optional
            The interfaces to be removed. If None, all interfaces will be removed.

        """
        if interfaces is None:
            self.features = [f for f in self.features if not isinstance(f, SlabConnectionInterface)]
        else:
            if not isinstance(interfaces, list):
                interfaces = [interfaces]
            self.features = [f for f in self.features if f not in interfaces]

    @property
    def is_group_element(self):
        return True

    def compute_modeltransformation(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self):
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()

    def compute_elementgeometry(self, include_features=False):
        """Compute the geometry of the element at local coordinates."""
        return self.compute_shape()

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        """
        Constructs a Slab from two polyline outlines. to be implemented to instantialte Plates and Slabs.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the slab geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the slab geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the slab geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Slab`
            A Slab object representing the slab geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        kwargs.update(args)
        return cls(**kwargs)
