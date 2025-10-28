from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_model.elements import Element

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

    Serves as container for beams, joints and other related elements and groups them together to form a slab.
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
    outline_a : :class:`~compas.geometry.Polyline`, optional
        A polyline representing the principal outline of this slab.
    outline_b : :class:`~compas.geometry.Polyline`, optional
        A polyline representing the associated outline of this slab.
    openings : list[:class:`~compas_timber.elements.Opening`], optional
        A list of Opening objects representing openings in this slab.
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
    is_slab : bool
        Always True for slabs.
    is_wall : bool
        False for base Slab class.
    is_floor : bool
        False for base Slab class.
    is_roof : bool
        False for base Slab class.
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

    def __init__(self, frame, length, width, thickness, local_outline_a=None, local_outline_b=None, openings=None, name=None, **kwargs):
        transformation = Transformation.from_frame(frame) if frame else Transformation()
        Element.__init__(self, transformation=transformation, **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b, openings=openings)
        self.length = length
        self.width = width
        self.height = thickness
        self.name = name or "Slab"
        self.interfaces = []
        self.attributes = {}
        self.attributes.update(kwargs)

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    def __str__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    @property
    def is_slab(self):
        """Check if this element is a slab.

        Returns
        -------
        bool
            Always True for slabs.
        """
        return True

    @property
    def is_wall(self):
        """Check if this element is a wall.

        Returns
        -------
        bool
            False for the base Slab class.
        """
        return False

    @property
    def is_floor(self):
        """Check if this element is a floor.

        Returns
        -------
        bool
            False for the base Slab class.
        """
        return False

    @property
    def is_roof(self):
        """Check if this element is a roof.

        Returns
        -------
        bool
            False for the base Slab class.
        """
        return False

    @property
    def is_group_element(self):
        """Check if this element can be used as a container for other elements.

        Returns
        -------
        bool
            Always True for slabs as they can contain other elements.
        """
        return True

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, **kwargs):
        """
        Constructs a PlateGeometry from two polyline outlines. to be implemented to instantialte Plates and Slabs.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the plate geometry in parent space.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the plate geometry in parent space.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of openings to be added to the plate geometry.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.PlateGeometry`
            A PlateGeometry object representing the plate geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        kwargs.update(args)
        return cls(**kwargs)
