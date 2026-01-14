import math
from typing import Optional

from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import distance_point_plane
from compas.tolerance import Tolerance

from compas_timber.connections import Joint
from compas_timber.connections.utilities import beam_ref_side_incidence_with_vector
from compas_timber.errors import FastenerApplicationError
from compas_timber.fasteners.fastener import Fastener
from compas_timber.fasteners.interface import HoleInterface
from compas_timber.fasteners.interface import Interface
from compas_timber.utils import intersection_line_line_param

TOL = Tolerance()


class Dowel(Fastener):
    """Class description"""

    def __init__(self, frame: Frame, height: float, radius: float):
        super().__init__(frame=frame)
        self.height = height
        self.radius = radius
        self.interfaces = []
        self._shape = None


class PlateFastener2(Fastener):
    def __init__(self, frame: Frame, outline: Polyline, thickness: float, interfaces=None):
        super().__init__(frame=frame, interfaces=interfaces)
        self.frame = frame.copy()
        self.target_frame = frame.copy()
        self.outline = outline
        self.thickness = thickness
        self.interfaces = [] if not interfaces else interfaces

    @property
    def __data__(self):
        data = {"frame": self.frame.__data__, "outline": self.outline.__data__, "thickness": self.thickness, "interfaces": [interface.__data__ for interface in self.interfaces]}
        return data

    @classmethod
    def __from_data__(cls, data):
        fastener = cls(frame=Frame.__from_data__(data["frame"]), outline=Polyline.__from_data__(data["outline"]), thickness=data["thickness"])
        interfaces = [HoleInterface.__from_data__(interface) for interface in data["interfaces"]]
        for interface in interfaces:
            fastener.add_interface(interface)
        return fastener

    @property
    def frame(self) -> Frame:
        return self._frame

    @frame.setter
    def frame(self, frame: Frame):
        self._frame = frame

    @property
    def to_joint_transformation(self) -> Frame:
        print("Self Frame", self.frame)
        return Transformation.from_frame_to_frame(self.frame, self.target_frame)

    def add_interface(self, interface: Interface) -> None:
        # difference_transformation = Transformation.from_frame_to_frame(self.frame, interface.frame)
        # interface.difference_to_fastener_frame = difference_transformation
        self.interfaces.append(interface)

    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        """
        Compute the geometry of the element in local coordinates.

        Parameters
        ----------
        include_interfaces : bool, optional
            If True, the interfaces are applied to the the creation of the geometry. Default is True.

        Returns
        -------
        :class:`compas.geometry.Brep`
        """
        # Compute basis geometry
        extrusion = self.frame.zaxis * self.thickness
        geometry = Brep.from_extrusion(self.outline, extrusion)
        # Modify it with the interfaces
        if self.interfaces:
            for interface in self.interfaces:
                geometry = interface.apply_to_fastener_geometry(geometry)
        geometry.transform(self.to_joint_transformation)

        return geometry

    def place_instances(self, joint: Joint) -> None:
        """Adds the fasteners to the joint.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        # get the frame where to pui the fastener on the joint
        frames = self.get_fastener_frames(joint)
        print(frames)
        # build the fastener to append on the joint
        for frame in frames:
            joint_fastener = self.copy()
            joint_fastener.target_frame = Frame(frame.point, frame.xaxis, frame.yaxis)

            for interface, element in zip(joint_fastener.interfaces, joint.elements):
                interface.element = element

            joint.fasteners.append(joint_fastener)

    # NOTE: This methods should be moved inside the joint... the joint sould give the Target Frame
    def get_fastener_frames(self, joint: Joint) -> list[Frame]:
        """Calculates the frames of the fasteners.

        Returns
        -------
        :class:`~compas.geometry.Frame`
            The frames of the fasteners with the x-axis along the main_beam.centerline and the y-axis along the cross_beam.centerline, offset to lay on the beam_faces.

        """
        front_face_index, back_face_index = self.validate_fastener_beam_compatibility(joint)
        beam_a, beam_b = joint.elements[0:2]
        (main_point, main_param), (cross_point, _) = intersection_line_line_param(beam_a.centerline, beam_b.centerline)
        int_point = (main_point + cross_point) * 0.5
        front_face = beam_a.ref_sides[front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(int_point)
        front_frame = Frame(
            front_point,
            beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
            front_face.normal,
        )
        front_frame.rotate(-math.pi / 2, front_frame.xaxis, front_point)
        back_face = beam_a.ref_sides[back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(int_point)

        back_frame = Frame(
            back_point,
            beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
            back_face.normal,
        )
        back_frame.rotate(-math.pi / 2, back_frame.xaxis, back_point)
        return [front_frame, back_frame]

    def validate_fastener_beam_compatibility(self, joint: Joint) -> tuple[int, int]:
        """Checks if the beams are compatible with the joint and sets the front and back face indices.

        returns the front and back face indices of the cross beam.

        Returns
        -------
        tuple[int, int]
            The front and back face indices of the cross beam.

        Raises
        ------
        BeamJoiningError
            If the beams are not compatible.

        """
        beam_a, beam_b = joint.elements[0:2]
        if not TOL.is_zero(angle_vectors(beam_a.frame.xaxis, beam_b.frame.xaxis) - (math.pi * 0.5)):
            raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="Beams are not perpendicular")
        cross_vector = cross_vectors(beam_a.centerline.direction, beam_b.centerline.direction)
        main_faces = beam_ref_side_incidence_with_vector(beam_a, cross_vector)
        cross_faces = beam_ref_side_incidence_with_vector(beam_b, cross_vector)
        front_face_index = min(main_faces, key=main_faces.get)
        cross_face_index = min(cross_faces, key=cross_faces.get)
        if not TOL.is_zero(main_faces[front_face_index]):
            raise FastenerApplicationError(
                elements=[beam_a, beam_b],
                fastener=self,
                message="beam_a is not perpendicular to the cross vector",
            )
        if not TOL.is_zero(cross_faces[cross_face_index]):
            raise FastenerApplicationError(
                elements=[beam_a, beam_b],
                fastener=self,
                message="Cross beam is not perpendicular to the cross vector",
            )
        if not TOL.is_zero(
            distance_point_plane(
                beam_a.ref_sides[front_face_index].point,
                Plane.from_frame(beam_b.ref_sides[cross_face_index]),
            )
        ):
            raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar")
        back_face_index = (front_face_index + 2) % 4
        cross_back_face_index = (cross_face_index + 2) % 4
        if not TOL.is_zero(
            distance_point_plane(
                beam_a.ref_sides[back_face_index].point,
                Plane.from_frame(beam_b.ref_sides[cross_back_face_index]),
            )
        ):
            raise FastenerApplicationError(elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar")
        return front_face_index, back_face_index
