import math
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import is_colinear_line_line
from compas_model.elements import Element
from compas_model.elements import reset_computed
from compas.tolerance import TOL
from numpy import flip

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import is_polyline_clockwise
from compas_timber.utils import join_polyline_segments
from compas_timber.utils import combine_parallel_segments

from .plate_geometry import PlateGeometry
from .slab_features import Opening


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
        data = Element.__data__.fget(self)
        data.update(PlateGeometry.__data__.fget(self))
        data["length"] = self.length
        data["width"] = self.width
        data["thickness"] = self.height
        data["name"] = self.name
        return data

    def __init__(self, transformation, length, width, thickness, local_outline_a=None, local_outline_b=None, name=None, **kwargs):
        Element.__init__(self, transformation=transformation, **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        PlateGeometry.__init__(self, local_outline_a, local_outline_b)
        self.length = length
        self.width = width
        self.height = thickness
        self.name = name or "Slab"
        self.interfaces = []
        self.attributes = {}
        self.attributes.update(kwargs)

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.transformation, self.outline_a, self.thickness)

    def __str__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.transformation, self.outline_a, self.thickness)

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

    def compute_elementgeometry(self, include_features = True):
        """Compute the geometry of the element at local coordinates."""
        geometry = self.compute_shape()
        if include_features:
            for feature in self.features:
                try:
                    geometry = feature.apply(geometry, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return geometry

    @reset_computed
    def reset_computed_properties(self):
        """Applies a transformation to the element.

        Parameters
        ----------
        transformation : :class:`compas.geometry.Transformation`
            The transformation to apply.

        """
        pass

    @reset_computed
    def transform(self, transformation):
        """Applies a transformation to the element.

        Parameters
        ----------
        transformation : :class:`compas.geometry.Transformation`
            The transformation to apply.

        """
        super().transform(transformation)

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, design_surface_outside=False, recognize_doors=False, horizontal_openings=False, **kwargs):
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
        if design_surface_outside:
            outline_a, outline_b = outline_b, outline_a
        if openings:       
            openings = [(o, "window") for o in openings]
        if recognize_doors:
            outline_a, outline_b, door_openings = extract_door_openings(outline_a, outline_b)
            if door_openings:
                if openings is None:
                    openings = [(o, "door") for o in door_openings]
                else:
                    openings.extend([(o, "door") for o in door_openings])

        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b)
        PlateGeometry._check_outlines(args["local_outline_a"], args["local_outline_b"])
        kwargs.update(args)
        kwargs["transformation"] = Transformation.from_frame(args.pop("frame"))
        slab = cls(**kwargs)
        if openings:
            for polyline, opening_type in openings:
                opening = Opening.from_outline_slab(polyline, slab, opening_type=opening_type, project_horizontal=horizontal_openings)
                slab.add_feature(opening)
        return slab


def extract_door_openings(outline_a, outline_b):
    """Extract door openings from the given outlines.

    Parameters
    ----------
    outline_a : :class:`~compas.geometry.Polyline`
        A polyline representing the principal outline of the plate geometry in parent space.
    outline_b : :class:`~compas.geometry.Polyline`
        A polyline representing the associated outline of the plate geometry in parent space.
        This should have the same number of points as outline_a.

    Returns
    -------
    list[:class:`~compas.geometry.Polyline`]
        A list of polylines representing the door openings.
    """
    combine_parallel_segments(outline_a)
    combine_parallel_segments(outline_b)
    internal_segment_indices_a = get_interior_segment_indices(outline_a)
    internal_segment_indices_b = get_interior_segment_indices(outline_b)
    if set(internal_segment_indices_a) != set(internal_segment_indices_b):
        raise ValueError("The internal segments of outline_a and outline_b do not match.")
    intermediate=[]
    openings = []
    done = False
    while not done:
        for seg_index in internal_segment_indices_a:
            i_a = seg_index
            slab_segments_a = outline_a.lines
            slab_segments_b = outline_b.lines
            door_segments = []
            door_segments_b = []
            for i in range(i_a-2, i_a + 3):
                door_segments.append(slab_segments_a[i % (len(slab_segments_a))])
                door_segments_b.append(slab_segments_b[i % (len(slab_segments_b))])
            parallel = True
            for a,b in zip(door_segments, door_segments_b):
                if angle_vectors(a.direction, b.direction) > TOL.ABSOLUTE:
                    parallel = False
                    break
            if not parallel:
                continue
            side_angle = angle_vectors(door_segments[1].direction, door_segments[3].direction)
            if abs(side_angle - math.pi) > TOL.ABSOLUTE:
                continue
            if not is_colinear_line_line(door_segments[0], door_segments[4], tol=TOL.RELATIVE):
                continue
            vertical = door_segments[1].direction
            vertical.unitize()
            segs_a = []
            segs_b = []
            for i in range(len(slab_segments_a)):
                if slab_segments_a[i] in door_segments:
                    continue
                segs_a.append(slab_segments_a[i])
                segs_b.append(slab_segments_b[i])
            opening = join_polyline_segments(door_segments[1:4])
            opening[0] -= vertical*1.0
            opening[3] -= vertical*1.0
            opening.append(opening.points[0])  # close loop
            openings.append(opening)
            outline_a= join_polyline_segments(segs_a, close_loop=True)
            outline_b= join_polyline_segments(segs_b, close_loop=True)
            internal_segment_indices_a = get_interior_segment_indices(outline_a)
            break
        else:
            done=True
    return outline_a, outline_b, openings

def get_interior_corner_indices(outline):
        """Get the indices of the interior corners of the slab outline."""
        _interior_corner_indices=[]
        vector = Plane.from_points(outline.points).normal
        points = outline.points[0:-1]
        cw = is_polyline_clockwise(outline, vector)
        for i in range(len(points)):
            angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], vector, deg=True)
            if not (cw ^ (angle < 0)):
                _interior_corner_indices.append(i)
        return _interior_corner_indices

def get_interior_segment_indices(polyline):
    """Get the indices of the interior segments of the slab outline."""
    interior_corner_indices = get_interior_corner_indices(polyline)
    edge_count = len(polyline.points) - 1
    _interior_segment_indices=[]
    for i in range(edge_count):
        if i in interior_corner_indices and (i + 1) % edge_count in interior_corner_indices:
            _interior_segment_indices.append(i)
    return _interior_segment_indices
