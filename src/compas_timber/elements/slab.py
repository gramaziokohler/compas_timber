from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_model.elements import Element
from compas_model.elements import reset_computed

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
        data["name"] = self.name
        data["interfaces"] = self.interfaces
        data["attributes"] = self.attributes
        return data

    def __init__(self, frame, length, width, thickness, outline_a=None, outline_b=None, openings=None, name=None, **kwargs):
        Element.__init__(self, **kwargs)
        self._frame = frame
        self.transformation = Transformation.from_frame(frame)
        outline_a = outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        outline_b = outline_b or Polyline([Point(p[0], p[1], thickness) for p in outline_a.points])
        PlateGeometry.__init__(self, outline_a, outline_b, openings=openings)

        self.length = length
        self.width = width
        self.height = thickness
        self.name = name or "Slab"
        self.interfaces = []
        self.attributes = {}
        self.attributes.update(kwargs)

    @property
    def frame(self):
        if self.model:
            return Element.frame.fget(self)
        else:
            return self._frame

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    def __str__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline_a, self.thickness)

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        PlateGeometry.reset(self)  # reset outline_a and outline_b
        self.interfaces = []
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
            self.interfaces = []
        else:
            if not isinstance(interfaces, list):
                interfaces = [interfaces]
            self.interfaces = [i for i in self.interfaces if i not in interfaces]


    def transformation_to_local(self):
        """Compute the transformation to local coordinates of this element
        based on its position in the spatial hierarchy of the model.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        # type: () -> Transformation
        return self.modeltransformation.inverse()

    @property
    def origin(self):
        assert self.frame
        return self.frame.point.copy()

    @property
    def centerline(self):
        # TODO: temp hack to make this compatible with `find_topology`.
        return self.baseline

    @property
    def is_slab(self):
        """Check if this element is a roof.

        Returns
        -------
        bool
            False for the base Slab class.
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
