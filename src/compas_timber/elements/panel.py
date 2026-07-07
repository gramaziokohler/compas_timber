from __future__ import annotations

import math
from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

if TYPE_CHECKING:
    from compas.datastructures import Mesh  # noqa: F401
    from compas_brep import Brep  # noqa: F401

    from compas_timber.panel_features import PanelFeature  # noqa: F401

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import is_colinear_line_line
from compas.tolerance import TOL
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.errors import FeatureApplicationError
from compas_timber.panel_features import Opening
from compas_timber.panel_features import OpeningType
from compas_timber.panel_features import PanelFeatureType
from compas_timber.utils import combine_parallel_segments
from compas_timber.utils import get_interior_segment_indices
from compas_timber.utils import get_plate_geometry_outlines_from_brep
from compas_timber.utils import get_polyline_normal_vector
from compas_timber.utils import join_polyline_segments
from compas_timber.utils import polylines_from_brep_face

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


class Panel(Element):
    """Represents a timber panel element (wall, floor, roof, etc.).

    Serves as container for beams, plates, and other related elements and groups them together to form a panel.
    A panel is often a single unit of prefabricated timber element.
    It is often referred to as an enveloping body.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`, optional
        The coordinate system (frame) of this panel. Required when no plate_geometry is provided.
    length : float, optional
        Length of the panel. Required when no plate_geometry is provided.
    width : float, optional
        Width of the panel. Required when no plate_geometry is provided.
    thickness : float, optional
        Thickness of the panel. Required when no plate_geometry is provided.
    plate_geometry : :class:`~compas_timber.elements.PlateGeometry`, optional
        A PlateGeometry object defining the panel shape. When provided, frame and dimensions must not be given.
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
    planes : tuple (:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`)
        The two main planes of the panel (bottom and top).
    normal : :class:`~compas.geometry.Vector`
        The normal vector of the panel.
    edge_planes : dict[int, :class:`~compas.geometry.Plane`]
        The edge planes of the panel by edge index.
    is_group_element : bool
        Always True for panels as they can contain other elements.

    """

    @property
    def __data__(self):
        data = {}
        data["plate_geometry"] = self.plate_geometry
        data["type"] = self.type
        data["features"] = [f for f in self.features if f.panel_feature_type != PanelFeatureType.CONNECTION_INTERFACE]
        data.update(self.attributes)
        return data

    def __init__(
        self,
        frame: Optional[Frame] = None,
        length: Optional[float] = None,
        width: Optional[float] = None,
        thickness: Optional[float] = None,
        plate_geometry: Optional[PlateGeometry] = None,
        type: Optional[str] = None,
        **kwargs,
    ):
        if plate_geometry is not None and any(x is not None for x in [frame, length, width, thickness]):
            raise ValueError("Panel cannot be instantiated with both a PlateGeometry and frame/dimension arguments.")
        if plate_geometry is None:
            if not all(x is not None for x in [frame, length, width, thickness]):
                raise ValueError("Panel must be instantiated with either a PlateGeometry or all of: frame, length, width, thickness.")
            plate_geometry = PlateGeometry.from_frame_and_dims(frame, length, width, thickness)
        super(Panel, self).__init__(transformation=plate_geometry.frame.to_transformation(), **kwargs)  # NOTE: Element wants a transformation, not a frame
        self.plate_geometry = plate_geometry
        self.length = plate_geometry.length
        self.width = plate_geometry.width
        self.height = plate_geometry.thickness
        self.type = type or PanelType.GENERIC
        self.attributes = {}
        self.attributes.update(kwargs)
        self._planes = None

    def __repr__(self) -> str:
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    def __str__(self) -> str:
        return "Panel(name={}, {}, {}, {:.3f})".format(self.name, Frame.from_transformation(self.transformation), self.outline_a, self.thickness)

    @property
    def geometry(self):
        return self.modelgeometry

    @geometry.setter
    def geometry(self, geometry):
        # overriding to please linter but this shouldn't be setable directly.
        raise AttributeError("Geometry is a computed property and cannot be set directly. To modify the geometry, change the outlines, thickness, or features of the panel.")

    @property
    def outlines(self):
        return (self.outline_a, self.outline_b)

    @property
    def outline_a(self):
        return self.plate_geometry.outline_a.transformed(self.modeltransformation)

    @property
    def outline_b(self):
        return self.plate_geometry.outline_b.transformed(self.modeltransformation)

    @property
    def thickness(self):
        return self.height

    @property
    def planes(self):
        if not self._planes:
            planes = (Plane.worldXY(), Plane(Point(0, 0, self.thickness), Vector(0, 0, 1)))
            self._planes = (planes[0].transformed(self.modeltransformation), planes[1].transformed(self.modeltransformation))
        return self._planes

    @property
    def normal(self):
        return Vector(0, 0, 1).transformed(self.modeltransformation)

    @property
    def edge_planes(self):
        # TODO: transform to global?
        return {i: plane.transformed(self.modeltransformation) for i, plane in self.plate_geometry.edge_planes.items()}

    def set_extension_plane(self, edge_index: int, plane: Plane):
        """Sets an extension plane for a specific edge of the plate. This is called by plate joints."""
        self.plate_geometry.set_extension_plane(edge_index, plane.transformed(self.transformation_to_local()))

    def apply_edge_extensions(self):
        """adjusts segments of the outlines to lay on the edge planes created by plate joints."""
        self.plate_geometry.apply_edge_extensions()

    def remove_blank_extension(self, edge_index: Optional[int] = None):
        """Removes any extension plane for the given edge index."""
        self.plate_geometry.remove_blank_extension(edge_index)

    @property
    def features(self) -> list[PanelFeature]:
        return self._features

    @property
    def interfaces(self):
        """list[:class:`~compas_timber.panel_features.PanelConnectionInterface`]: The interfaces associated with this panel."""
        return [f for f in self.features if f.panel_feature_type == PanelFeatureType.CONNECTION_INTERFACE]

    def clear_model_dependent_cache(self):
        """Clear cached attributes that depend on the element's position in the model hierarchy."""
        self._modeltransformation = None
        self._modelgeometry = None
        self._aabb = None
        self._obb = None
        self._collision_mesh = None
        self._planes = None

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.plate_geometry.reset()  # reset outline_a and outline_b
        self._features = [f for f in self._features if not f.is_joinery]
        self.debug_info = []

    @reset_computed
    def reset_joinery(self):
        """Resets the element to its pre-joinery state by removing all joinery features, extensions, and debug_info."""
        self.plate_geometry.reset()  # reset outline_a and outline_b
        self._features = [f for f in self._features if not f.is_joinery]
        self.debug_info = []

    @reset_computed
    def remove_features(self, features: Optional[Union[PanelFeature, list[PanelFeature]]] = None) -> None:
        """Removes features from the element.

        Parameters
        ----------
        features : :class:`~compas_timber.panel_features.PanelFeature` | list[:class:`~compas_timber.panel_features.PanelFeature`], optional
            The features to be removed. If None, all features will be removed.

        """
        if features is None:
            self._features = []
        else:
            feature_list = features if isinstance(features, list) else [features]
            self._features = [f for f in self.features if f not in feature_list]

    @property
    def is_group_element(self):
        return True
        # ==========================================================================

    #  Implementation of abstract methods
    # ==========================================================================

    def compute_aabb(self, inflate: float = 0.0) -> Box:
        """Computes the Axis Aligned Bounding Box (AABB) of the element.

        Parameters
        ----------
        inflate : float, optional
            Offset of box to avoid floating point errors.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the element.

        """
        vertices = self.outline_a.points + self.outline_b.points
        box = Box.from_points(vertices)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate: float = 0.0) -> Box:
        """Computes the Oriented Bounding Box (OBB) of the element.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """

        obb = self.plate_geometry.compute_aabb(inflate)
        obb.transform(self.modeltransformation)
        return obb

    def compute_collision_mesh(self) -> Mesh:
        """Computes the collision geometry of the element.

        Returns
        -------
        :class:`compas.datastructures.Mesh`
            The collision geometry of the element.

        """
        return self.obb.to_mesh()

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

    def transformation_to_local(self):
        """Compute the transformation from model space to local element space."""
        return self.modeltransformation.inverse()

    def compute_elementgeometry(self, include_features: bool = True) -> Brep:
        """Compute the geometry of the element.

        Parameters
        ----------
        include_features : bool, optional
            If ``True``, include the features in the computed geometry.
            If ``False``, return only the plate shape.

        Returns
        -------
        :class:`compas.datastructures.Mesh` | :class:`compas.geometry.Brep`

        """

        # TODO: consider if Brep.from_curves(curves) is faster/better
        plate_geo = self.plate_geometry.compute_shape()
        if include_features:
            for feature in self._features:
                try:
                    plate_geo = feature.apply(plate_geo, self)
                except FeatureApplicationError as error:
                    self.debug_info.append(error)
        return plate_geo

    @classmethod
    def from_outline_thickness(
        cls, outline: Polyline, thickness: float, vector: Optional[Vector] = None, openings: Optional[list[Polyline]] = None, orientation: Optional[Vector] = None, **kwargs
    ):
        """
        Constructs a Plate from a polyline outline and a thickness.
        The outline is the top face of the plate_geometry, and the thickness is the distance to the bottom face.

        Parameters
        ----------
        outline : :class:`~compas.geometry.Polyline`
            A polyline representing the outline of the plate geometry.
        thickness : float
            The thickness of the plate geometry.
        vector : :class:`~compas.geometry.Vector`, optional
            The direction of the thickness vector. If None, the thickness vector is determined from the outline.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of polyline openings to be added to the plate geometry.
        orientation : :class:`~compas.geometry.Vector`, optional
            A vector indicating the desired orientation of the panel's local y-axis. If None, orientation is determined from the outline.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel geometry with the given outline and thickness.
        """
        # this ensure the plate geometry can always be computed
        if TOL.is_zero(thickness):
            thickness = TOL.absolute

        offset_vector = get_polyline_normal_vector(outline, vector)  # gets vector perpendicular to outline
        offset_vector *= thickness
        outline_b = Polyline(outline).translated(offset_vector)
        return cls.from_outlines(outline, outline_b, openings=openings, orientation=orientation, **kwargs)

    @classmethod
    def from_face_thickness(cls, brep: Brep, thickness: float, vector: Optional[Vector] = None, orientation: Optional[Vector] = None, **kwargs):
        """Creates a panel from a single-face brep.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            A single-face brep representing the panel surface.
        thickness : float
            The thickness of the panel.
        vector : :class:`~compas.geometry.Vector`, optional
            The vector in which the panel is extruded.
        orientation : :class:`~compas.geometry.Vector`, optional
            A vector indicating the desired orientation of the panel's local y-axis. If None, orientation is determined from the outline.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Panel` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel with the given brep and thickness.
        """

        if len(brep.faces) > 1:
            raise ValueError("Can only use single-face breps to create a Panel. This brep has {}".format(len(brep.faces)))
        face = brep.faces[0]
        outer_polyline, inner_polylines = polylines_from_brep_face(face)
        return cls.from_outline_thickness(outer_polyline, thickness, vector=vector, openings=inner_polylines, orientation=orientation, **kwargs)

    @classmethod
    def from_brep(cls, brep: Brep, orientation: Optional[Vector] = None, **kwargs):
        """Creates a panel from a brep by automatically detecting two parallel faces.

        This method identifies the two main faces of the brep using topological analysis
        (edge counts and adjacency) and uses them as the top and bottom faces of the panel.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            The brep representing the panel geometry. Must have at least 2 parallel faces.
        orientation : :class:`~compas.geometry.Vector`, optional
            A vector indicating the desired orientation of the panel's local y-axis. If None, orientation is determined from the outline.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Panel` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object created from the two parallel faces of the brep.
        """
        if len(brep.faces) < 2:
            raise ValueError("Brep must have at least 2 faces. This brep has {}".format(len(brep.faces)))
        outline_a, outline_b, openings = get_plate_geometry_outlines_from_brep(brep)
        return cls.from_outlines(outline_a, outline_b, openings=openings, orientation=orientation, **kwargs)

    @classmethod
    def from_outlines(cls, outline_a, outline_b, openings=None, recognize_doors=False, horizontal_openings=False, orientation: Optional[Vector] = None, **kwargs):
        """
        Constructs a Panel from two polyline outlines.

        Parameters
        ----------
        outline_a : :class:`~compas.geometry.Polyline`
            A polyline representing the principal outline of the panel geometry in global space. For exterior walls, this is the interior side.
        outline_b : :class:`~compas.geometry.Polyline`
            A polyline representing the associated outline of the panel geometry in global space. For exterior walls, this is the exterior side.
            This should have the same number of points as outline_a.
        openings : list[:class:`~compas.geometry.Polyline`], optional
            A list of window opening polylines to be added to the panel.
        recognize_doors : bool
            If True, door features will be extracted from the outlines and added as Openings to the Panel.
        horizontal_openings : bool
            If True, openings that are not vertical or horizontal will be extruded horizontally through the Panel.
        orientation : :class:`~compas.geometry.Vector`, optional
            A vector indicating the desired orientation of the panel's local y-axis. If None, orientation is determined from the outline.
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Panel`
            A Panel object representing the panel with the given outlines.
        """

        window_polylines = [o for o in openings] if openings else []
        door_polylines = []
        if recognize_doors:
            outline_a, outline_b, door_openings = extract_door_openings(outline_a, outline_b)
        panel = cls(plate_geometry=PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=orientation), **kwargs)
        for polyline in window_polylines:
            opening = Opening.from_outline_panel(polyline, panel, opening_type=OpeningType.WINDOW, project_horizontal=horizontal_openings)
            panel.add_feature(opening)
        for polyline in door_polylines:
            opening = Opening.from_outline_panel(polyline, panel, opening_type=OpeningType.DOOR, project_horizontal=horizontal_openings)
            panel.add_feature(opening)
        return panel


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
    tuple
        A 3-tuple of (outline_a, outline_b, openings) where outline_a and outline_b are the
        modified panel outlines with door segments removed, and openings is a list of
        :class:`~compas.geometry.Polyline` objects representing the extracted door openings.
    """
    openings = []
    is_door_found = True
    while is_door_found:
        combine_parallel_segments(outline_a)
        combine_parallel_segments(outline_b)
        segments_a = outline_a.lines
        segments_b = outline_b.lines
        n = len(segments_a)
        interior_indices_a = get_interior_segment_indices(outline_a)
        interior_indices_b = get_interior_segment_indices(outline_b)
        interior_indices = set(interior_indices_a) | set(interior_indices_b)

        # walk around the polylines, extract door if found
        for seg_index in interior_indices:
            # collect the 5-segment window centered on the interior segment
            window_indices = [(seg_index + i) % n for i in range(-2, 3)]
            door_segs_a = [segments_a[i] for i in window_indices]
            door_segs_b = [segments_b[i] for i in window_indices]

            # Check the segments for door-ness
            # both outlines must agree on segment directions
            if not all(angle_vectors(a.direction, b.direction) <= TOL.ABSOLUTE for a, b in zip(door_segs_a, door_segs_b)):
                continue
            # the two side segments must be anti-parallel (opposite directions)
            if abs(angle_vectors(door_segs_a[1].direction, door_segs_a[3].direction) - math.pi) > TOL.ABSOLUTE:
                continue
            # the segments left and right from door opening must be collinear (same horizontal line)
            if not is_colinear_line_line(door_segs_a[0], door_segs_a[4], tol=TOL.RELATIVE):
                continue

            # door-like segments found, now extract them
            vertical = door_segs_a[1].direction
            vertical.unitize()

            remaining = {i for i in range(n)} - set(window_indices)
            segs_a = [segments_a[i] for i in sorted(remaining)]
            segs_b = [segments_b[i] for i in sorted(remaining)]

            opening = join_polyline_segments(door_segs_a[1:4])[0][0]
            opening[0] -= vertical * 1.0
            opening[3] -= vertical * 1.0
            opening.append(opening.points[0])  # close loop
            openings.append(opening)

            outline_a = join_polyline_segments(segs_a, close_loop=True)[0][0]
            outline_b = join_polyline_segments(segs_b, close_loop=True)[0][0]

            break  # only extract one door at a time to avoid issues with multiple doors in the same window of segments.
            # After extracting one door, the outlines are updated and the process is repeated until no more doors are found.

        # walked the entire perimeter, no door found
        else:
            is_door_found = False  # no door candidates found in this pass

    return outline_a, outline_b, openings
