from __future__ import annotations

from typing import Optional
from typing import Union

from compas.datastructures import Mesh  # noqa: F401
from compas.geometry import Box
from compas.geometry import Brep  # noqa: F401
from compas.geometry import Frame  # noqa: F401
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import centroid_points
from compas.geometry import distance_point_point
from compas.geometry import normal_polygon
from compas.tolerance import TOL
from compas_model.elements import reset_computed

from compas_timber.base import TimberElement
from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import FreeContour
from compas_timber.utils import get_polyline_normal_vector
from compas_timber.utils import polylines_from_brep_face

from .plate_geometry import PlateGeometry


class Plate(TimberElement):
    """
    A class to represent timber plates (plywood, CLT, etc.) defined by polylines on top and bottom faces of material.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    length : float
        Length of the plate.
    width : float
        Width of the plate.
    thickness : float
        Thickness of the plate.
    outline_a : :class:`~compas.geometry.Polyline`, optional
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`, optional
        A line representing the associated outline of this plate. This should have the same number of points as outline_a.
    openings : list[:class:`~compas.geometry.Polyline`], optional
        A list of Polyline objects representing openings in this plate.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this plate.
    length : float
        Length of the plate.
    width : float
        Width of the plate.
    height : float
        Height of the plate (same as thickness).
    thickness : float
        Thickness of the plate.
    outline_a : :class:`~compas.geometry.Polyline`
        A line representing the principal outline of this plate.
    outline_b : :class:`~compas.geometry.Polyline`
        A line representing the associated outline of this plate.
    is_plate : bool
        Always True for plates.
    blank : :class:`~compas.geometry.Box`
        A feature-less box representing the material stock geometry to produce this plate.
    blank_length : float
        Length of the plate blank.
    features : list[:class:`~compas_timber.fabrication.BTLxProcessing`]
        List of features applied to this plate.
    key : int, optional
        Once plate is added to a model, it will have this model-wide-unique integer key.

    """

    @property
    def __data__(self):
        data = super().__data__
        data["thickness"] = data.pop("height")
        data.update(self.plate_geometry.__data__)
        return data

    def __init__(
        self,
        frame: Frame,
        length: float,
        width: float,
        thickness: float,
        local_outline_a: Optional[Polyline] = None,
        local_outline_b: Optional[Polyline] = None,
        openings: Optional[list[Polyline]] = None,
        **kwargs,
    ) -> None:
        super(Plate, self).__init__(frame=frame, length=length, width=width, height=thickness, **kwargs)
        local_outline_a = local_outline_a or Polyline([Point(0, 0, 0), Point(length, 0, 0), Point(length, width, 0), Point(0, width, 0), Point(0, 0, 0)])
        local_outline_b = local_outline_b or Polyline([Point(p[0], p[1], thickness) for p in local_outline_a.points])
        self.plate_geometry = PlateGeometry(local_outline_a=local_outline_a, local_outline_b=local_outline_b, openings=openings)
        self._outline_feature = None
        self._opening_features = None
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []
        self._planes = []

    def __repr__(self):
        # type: () -> str
        return "Plate(outline_a={!r}, outline_b={!r})".format(self.plate_geometry.outline_a, self.plate_geometry.outline_b)

    def __str__(self):
        # type: () -> str
        return "Plate {}, {} ".format(self.plate_geometry.outline_a, self.plate_geometry.outline_b)

    # ==========================================================================
    # Computed attributes
    # ==========================================================================

    @property
    def is_plate(self):
        return True

    @property
    def blank(self):
        if not self._blank:
            box = self.plate_geometry.compute_aabb()
            box.xsize += 2 * self.attributes.get("blank_extension", 0.0)
            box.ysize += 2 * self.attributes.get("blank_extension", 0.0)
            self._blank = box.transformed(self.modeltransformation)
        return self._blank

    @property
    def blank_length(self):
        return self.blank.xsize

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
        return {i: plane.transformed(self.modeltransformation) for i, plane in self.plate_geometry.edge_planes.items()}

    def set_extension_plane(self, edge_index: int, plane: Plane) -> None:
        """Sets an extension plane for a specific edge of the plate. This is called by plate joints."""
        self.plate_geometry.set_extension_plane(edge_index, plane.transformed(self.transformation_to_local()))

    def apply_edge_extensions(self) -> None:
        """adjusts segments of the outlines to lay on the edge planes created by plate joints."""
        self.plate_geometry.apply_edge_extensions()

    def remove_blank_extension(self, edge_index: Optional[int] = None):
        """Removes any extension plane for the given edge index."""
        self.plate_geometry.remove_blank_extension(edge_index)

    @property
    def features(self):
        if not self._outline_feature:
            # TODO FreeContour from Plate
            self._outline_feature = FreeContour.from_top_bottom_and_elements(self.outline_a, self.outline_b, self, interior=False)
        if not self._opening_features:
            # TODO remove openings from PlateGeometry, implement as feature.
            self._opening_features = [
                FreeContour.from_polyline_and_element(o.transformed(Transformation.from_frame(self.frame)), self, interior=True) for o in self.plate_geometry.openings
            ]
        return [self._outline_feature] + self._opening_features + self._features

    @features.setter
    def features(self, features):
        # type: (list[FreeContour]) -> None
        """Sets the features of the plate."""
        self._features = features

    @reset_computed
    def reset(self):
        """Resets the element to its initial state by removing all features, extensions, and debug_info."""
        self.plate_geometry.reset()  # reset outline_a and outline_b
        self._features = []
        self._outline_feature = None
        self._opening_features = None
        self.debug_info = []

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

    def compute_elementgeometry(self, include_features: Optional[bool] = True) -> Union[Brep, Mesh]:
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
        return plate_geo.transformed(Transformation.from_frame(self.frame))

    @classmethod
    def from_outlines(cls, outline_a: Polyline, outline_b: Polyline, openings: Optional[list[Polyline]] = None, **kwargs):
        """
        Constructs a Plate from two polyline outlines. To be implemented to instantialte Plates and Panels.

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
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate geometry with the given outlines.
        """
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, openings)
        kwargs.update(args)
        return cls(**kwargs)

    @classmethod
    def from_outline_thickness(cls, outline: Polyline, thickness: float, vector: Optional[Vector] = None, openings: Optional[list[Polyline]] = None, **kwargs):
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
        **kwargs : dict, optional
            Additional keyword arguments to be passed to the constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate geometry with the given outline and thickness.
        """
        # this ensure the plate geometry can always be computed
        if TOL.is_zero(thickness):
            thickness = TOL.absolute

        offset_vector = get_polyline_normal_vector(outline, vector)  # gets vector perpendicular to outline
        offset_vector *= thickness
        outline_b = Polyline(outline).translated(offset_vector)
        return cls.from_outlines(outline, outline_b, openings=openings, **kwargs)

    @classmethod
    def from_face(cls, brep: Brep, thickness: float, vector: Optional[Vector] = None, **kwargs):
        """Creates a plate from a single-face brep.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            A single-face brep representing the plate surface.
        thickness : float
            The thickness of the plate.
        vector : :class:`~compas.geometry.Vector`, optional
            The vector in which the plate is extruded.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Plate` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object representing the plate with the given brep face and thickness.
        """

        if len(brep.faces) > 1:
            raise ValueError("Can only use single-face breps to create a Plate. This brep has {}".format(len(brep.faces)))
        face = brep.faces[0]
        outer_polyline, inner_polylines = polylines_from_brep_face(face)
        if not outer_polyline:
            raise ValueError("no outer loop for brep face was found")
        return cls.from_outline_thickness(outer_polyline, thickness, vector=vector, openings=inner_polylines, **kwargs)

    @classmethod
    def from_brep(cls, brep: Brep, **kwargs):
        """Creates a plate from a brep by automatically detecting two parallel faces.

        This method analyzes the brep to identify two parallel faces with matching edge counts
        and uses them as the top and bottom faces of the plate. It prioritizes faces with the
        maximum number of edges (typically the primary faces) and verifies they are planar and
        spatially separated.

        Parameters
        ----------
        brep : :class:`~compas.geometry.Brep`
            The brep representing the plate geometry. Must have at least 2 parallel faces.
        **kwargs : dict, optional
            Additional keyword arguments.
            These are passed to the :class:`~compas_timber.elements.Plate` constructor.

        Returns
        -------
        :class:`~compas_timber.elements.Plate`
            A Plate object created from the two parallel faces of the brep.

        Raises
        ------
        ValueError
            If the brep does not have at least 2 parallel faces with matching edge counts,
            or if polylines cannot be extracted from the faces.
        """
        if len(brep.faces) < 2:
            raise ValueError("Brep must have at least 2 faces. This brep has {}".format(len(brep.faces)))

        faces_data = []
        for i, face in enumerate(brep.faces):
            try:
                outer, inner = polylines_from_brep_face(face)
            except (AttributeError, TypeError) as e:
                raise ValueError("Failed to extract polylines from face {}: {}".format(i, str(e)))
            if outer:
                faces_data.append({'outer': outer, 'inner': inner, 'edge_count': len(outer.points) - 1})

        if len(faces_data) < 2:
            raise ValueError("Could not extract valid outlines from at least 2 faces")

        def _get_normal(polyline):
            if len(polyline.points) < 4:
                return None
            pts = list(polyline.points)[:-1]
            try:
                normal_data = normal_polygon(pts)
                if isinstance(normal_data, (list, tuple)) and len(normal_data) == 3:
                    return Vector(*normal_data)
                return normal_data if isinstance(normal_data, Vector) else None
            except Exception:
                return None

        faces_with_normals = []
        for face_data in faces_data:
            normal = _get_normal(face_data['outer'])
            if normal:
                outer_pts = list(face_data['outer'].points)[:-1]
                centroid = centroid_points(outer_pts)
                plane = Plane(centroid, normal)
                is_planar = all(abs(plane.distance_to_point(pt)) < TOL.absolute for pt in outer_pts)
                faces_with_normals.append({**face_data, 'normal': normal, 'is_planar': is_planar, 'centroid': centroid})

        if len(faces_with_normals) < 2:
            raise ValueError("Could not compute normals for at least 2 extracted faces")

        face_a_data = None
        face_b_data = None
        planar_candidates = [f for f in faces_with_normals if f['is_planar']]

        if len(planar_candidates) >= 2:
            for edge_target in sorted(set(f['edge_count'] for f in planar_candidates), reverse=True):
                candidates = [f for f in planar_candidates if f['edge_count'] == edge_target]
                for i, face_i in enumerate(candidates):
                    for face_j in candidates[i + 1:]:
                        dot = face_i['normal'].dot(face_j['normal'])
                        abs_dot = abs(dot)
                        offset_vector = Vector.from_start_end(face_i['centroid'], face_j['centroid'])
                        normal_separation = abs(offset_vector.dot(face_i['normal'].unitized()))

                        if abs_dot > 0.95 and normal_separation > max(TOL.absolute, normal_separation * TOL.relative):
                            face_a_data = face_i
                            face_b_data = face_j
                            break
                    if face_a_data:
                        break
                if face_a_data:
                    break

        if face_a_data is None:
            for edge_target in sorted(set(f['edge_count'] for f in faces_with_normals), reverse=True):
                candidates = [f for f in faces_with_normals if f['edge_count'] == edge_target]
                for i, face_i in enumerate(candidates):
                    for face_j in candidates[i + 1:]:
                        dot = face_i['normal'].dot(face_j['normal'])
                        abs_dot = abs(dot)
                        if abs_dot > 0.85:
                            face_a_data = face_i
                            face_b_data = face_j
                            break
                    if face_a_data:
                        break
                if face_a_data:
                    break

        if face_a_data is None or face_b_data is None:
            error_parts = ["Could not find 2 parallel faces with matching edge counts"]
            if faces_with_normals:
                edge_counts = sorted(set(f['edge_count'] for f in faces_with_normals))
                error_parts.append("Found {} faces with edge counts: {}".format(len(faces_with_normals), edge_counts))
                if len(faces_with_normals) >= 2:
                    dot_products = []
                    for i, f1 in enumerate(faces_with_normals):
                        for f2 in faces_with_normals[i+1:]:
                            dot = f1['normal'].dot(f2['normal'])
                            dot_products.append((abs(dot), f1['edge_count'], f2['edge_count']))
                    if dot_products:
                        best_dot, ec1, ec2 = max(dot_products)
                        error_parts.append("Best face pair has |dot|={:.3f} with edge counts {}/{}".format(best_dot, ec1, ec2))
            raise ValueError(". ".join(error_parts))

        def _align_polylines(poly_a, poly_b):
            points_a = list(poly_a.points)[:-1]
            points_b = list(poly_b.points)[:-1]
            if len(points_a) != len(points_b):
                return poly_b
            n = len(points_a)
            best_offset = 0
            best_reverse = False
            min_dist = float('inf')
            for reverse in [False, True]:
                b_points = points_b[::-1] if reverse else points_b
                for offset in range(n):
                    total_dist = sum(distance_point_point(points_a[k], b_points[(k + offset) % n]) for k in range(n))
                    if total_dist < min_dist:
                        min_dist = total_dist
                        best_offset = offset
                        best_reverse = reverse
            b_points = points_b[::-1] if best_reverse else points_b
            aligned_points = [b_points[(k + best_offset) % n] for k in range(n)]
            aligned_points.append(aligned_points[0])
            return Polyline(aligned_points)

        aligned_outer_b = _align_polylines(face_a_data['outer'], face_b_data['outer'])
        openings = face_a_data['inner'] if face_a_data['inner'] else None
        return cls.from_outlines(face_a_data['outer'], aligned_outer_b, openings=openings, **kwargs)
