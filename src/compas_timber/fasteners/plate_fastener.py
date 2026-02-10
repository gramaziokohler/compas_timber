from __future__ import annotations

from functools import singledispatchmethod
from typing import TYPE_CHECKING
from typing import Optional

from compas.data import Data
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import centroid_points
from compas.tolerance import Tolerance

from compas_timber.elements.timber import TimberElement
from compas_timber.fabrication.drilling import Drilling
from compas_timber.fabrication.pocket import Pocket
from compas_timber.fasteners.fastener import Fastener

if TYPE_CHECKING:
    pass

TOL = Tolerance()


class PlateFastenerHole(Data):
    def __init__(self, point: Point, diameter: float, depth: float):
        self.point = point
        self.diameter = diameter
        self.depth = depth

    @property
    def __data__(self):
        data = {"point": self.point.__data__, "diameter": self.diameter, "depth": self.depth}
        return data

    @classmethod
    def __from_data__(cls, data):
        return cls(Point.__from_data__(data["point"]), data["diameter"], data["depth"])


#################################################################################################################
#################################################################################################################
#################################################################################################################


class PlateFastener(Fastener):
    def __init__(
        self,
        frame: Frame,
        outline: Polyline,
        thickness: float,
        holes: Optional[list[PlateFastenerHole]] = None,
        recess: Optional[float] = None,
        recess_offset: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(frame=frame, **kwargs)
        self.outline = outline
        self.thickness = thickness
        self.holes = holes or []
        self.recess = recess
        self.recess_offset = recess_offset

        if self.recess:
            self.recess_frame = self.frame.translated(self.frame.zaxis * self.recess)
        else:
            self.recess_offset = 0
            self.recess_frame = self.frame.copy()

    @property
    def __data__(self):
        data = {
            "frame": self.frame.__data__,
            "outline": self.outline.__data__,
            "thickness": self.thickness,
            "holes": [hole.__data__ for hole in self.holes],
            "recess": self.recess,
            "recess_offset": self.recess_offset,
        }
        return data

    @classmethod
    def __from_data__(cls, data):
        fastener = cls(
            frame=Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"]),
            outline=Polyline.__from_data__(data["outline"]),  # type: ignore
            thickness=data["thickness"],
            holes=[PlateFastenerHole.__from_data__(hole) for hole in data["holes"]],
            recess=data["recess"],
            recess_offset=data["recess_offset"],
        )
        return fastener

    @property
    def to_joint_transformation(self) -> Transformation:
        """
        Computes the transformation from the fastener's local frame to the target frame in the joint.
        """
        return Transformation.from_frame_to_frame(self.recess_frame, self.target_frame)

    @singledispatchmethod
    def add_hole(self, arg) -> PlateFastenerHole:
        """Add a hole to this plate.

        This method supports two calling forms:

        1. Passing an existing PlateFastenerHole:
           `add_hole(hole)` — the hole is appended to `self.holes`.

        2. Passing a Point and numeric parameters to create a new hole:
           `add_hole(point, diameter, depth)` — a new `PlateFastenerHole` is
           created with the given `point`, `diameter`, and `depth`, then appended.

        Parameters
        ----------
        arg : PlateFastenerHole | Point
            Either an existing `PlateFastenerHole` instance to add, or a `Point`
            indicating the hole location (in which case `diameter` and `depth`
            must also be provided).

        diameter : float, optional
            Diameter of the new hole. Required when `arg` is a `Point`.
        depth : float, optional
            Depth of the new hole. Required when `arg` is a `Point`.

        Returns
        -------
        PlateFastenerHole
            The `PlateFastenerHole` instance that was added.

        Raises
        ------
        TypeError
            - If `arg` is neither a `PlateFastenerHole` nor a `Point`.
            - If `arg` is a `Point` but `diameter` or `depth` is not provided.

        Examples
        --------
        # Add an existing hole object:
        >>> pf.add_hole(existing_hole)

        # Create and add a hole at `pt`:
        >>> pf.add_hole(pt, diameter=10.0, depth=5.0)
        """
        raise TypeError(f"Unsupported type: {type(arg)!r}")

    @add_hole.register
    def _(self, hole: "PlateFastenerHole") -> PlateFastenerHole:
        self.holes.append(hole)
        return hole

    @add_hole.register
    def _(self, point: "Point", diameter: Optional[float] = None, depth: Optional[float] = None) -> PlateFastenerHole:
        if diameter is None or depth is None:
            raise TypeError("When passing a Point you must also pass 'diameter' and 'depth'.")
        hole = PlateFastenerHole(point=point, diameter=diameter, depth=depth)
        self.holes.append(hole)
        return hole

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        """
        Compute the geometry of the element in local coordinates.

        Parameters
        ----------
        include_interfaces : bool, optional
            If True, the interfaces are applied to the creation of the geometry. Default is True.

        Returns
        -------
        :class:`compas.geometry.Brep`
        """
        # Compute basis geometry
        extrusion = self.frame.zaxis * self.thickness
        geometry = Brep.from_extrusion(self.outline, extrusion)

        # Apply Holes
        for hole in self.holes:
            frame = self.frame.copy()
            frame.point = hole.point
            cylinder = Cylinder(radius=hole.diameter / 2, height=hole.depth, frame=frame)
            cylinder = Brep.from_cylinder(cylinder)
            geometry -= cylinder

        # Move to Join if target frame
        if self.target_frame:
            geometry.transform(self.to_joint_transformation)

        return geometry

    def apply_processings(self, joint):
        for element in joint.elements:
            if not isinstance(element, TimberElement):
                continue
            drillings = self._create_drillings_features(element)
            if drillings:
                element.features.extend(drillings)
            pocket = self._create_recess_features(element)
            if pocket:
                element.features.append(pocket)

    def _create_drillings_features(self, element):
        processings = []
        for hole in self.holes:
            drilling_line = Line(hole.point, hole.point + hole.depth * -self.frame.zaxis)
            drilling_line.transform(Transformation.from_frame_to_frame(self.frame, self.target_frame))
            try:
                drilling = Drilling.from_line_and_element(line=drilling_line, element=element, diameter=hole.diameter)
                processings.append(drilling)
            except Exception:
                continue
        return processings

    def _create_recess_features(self, element):
        if not self.recess:
            return
        volume = self.recess_volume
        try:
            pocket = Pocket.from_volume_and_element(volume, element)
            return pocket
        except Exception as e:
            print(e)

    @property
    def recess_volume(self):
        moved_outline = self.outline.translated(self.frame.zaxis * self.recess)
        vertices = moved_outline.points[:-1] + self.outline.points[:-1]
        hlen = int(len(vertices) / 2)
        faces = []
        for i in range(hlen):
            face = [i, (i + 1) % hlen, (i + 1) % hlen + hlen, i + hlen]
            faces.append(face)
        faces.append(list(range(hlen - 1, -1, -1)))
        faces.append(list(range(hlen, hlen * 2)))
        self._ensure_faces_outward(vertices, faces)
        polyhedron = Polyhedron(vertices, faces)

        if self.recess_offset:
            polyhedron = self._offset_recess(polyhedron)

        polyhedron.transform(self.to_joint_transformation)
        return polyhedron

    def _offset_recess(self, polyhedron):
        for i, face in enumerate(polyhedron.faces):
            if i >= 4:
                break
            # Get face vertices
            face_verts = [polyhedron.vertices[i] for i in face]
            # Calculate normal from first three vertices
            v0 = face_verts[0]
            v1 = face_verts[1]
            v2 = face_verts[2]
            e1 = Vector.from_start_end(v0, v1)
            e2 = Vector.from_start_end(v0, v2)
            normal = e1.cross(e2)

            # Normalize the normal vector
            normal = normal.unitized()

            # Move each vertex in the face by the offset amount
            for i in range(len(face)):
                vertex_index = face[i]
                offset_vector = normal * self.recess_offset
                polyhedron.vertices[vertex_index] = Point(
                    polyhedron.vertices[vertex_index].x + offset_vector.x,
                    polyhedron.vertices[vertex_index].y + offset_vector.y,
                    polyhedron.vertices[vertex_index].z + offset_vector.z,
                )
        return polyhedron

    @staticmethod
    def _ensure_faces_outward(vertices: list[Point], faces: list[list[int]]):
        """Reorder face indices so face normals point outward.
        Parameters
        ----------
        vertices : list[Point]
            list of Point or 3-tuples
        faces : list[list[int]]
            list of lists of indices

        Returns
        -------
        list[list[int]]
            new faces order
        """
        poly_centroid = Point(*centroid_points(vertices))
        new_faces = []
        for face in faces:
            # vertices
            v0 = vertices[face[0]]
            v1 = vertices[face[1]]
            v2 = vertices[face[2]]
            # vectors
            e1 = Vector.from_start_end(v0, v1)
            e2 = Vector.from_start_end(v0, v2)
            n = e1.cross(e2)
            face_centroid = centroid_points([vertices[i] for i in face])
            outward = Vector.from_start_end(poly_centroid, face_centroid)
            # dots
            if n.dot(outward) < 0:
                new_faces.append(list(reversed(face)))
            else:
                new_faces.append(list(face))
        return new_faces
