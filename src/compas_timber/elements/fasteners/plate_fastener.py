import math

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import cross_vectors
from compas.geometry import distance_point_plane
from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.elements import Fastener
from compas_timber.elements import FastenerApplicationError
from compas_timber.utils import intersection_line_line_param

TOL = Tolerance()


class PlateFastener(Fastener):
    """
    A class to represent flat plate timber fasteners (e.g. steel plates).

    Parameters
    ----------
    shape : :class:`~compas.geometry.Geometry`
        The shape of the fastener at the XY plane origin.
    frame : :class:`~compas.geometry.Frame`
        The frame of the instance of the fastener that is applied to the model.
        The fastener should be defined at the XY plane origin with the x-axis pointing in the direction of the main_beam.
    holes : list of tuple, optional
        The holes of the fastener. Structure is as follows: [(point, diameter), ...]
    angle : float, optional (default=math.pi / 2)
        The angle of the fastener. The angle between the beam elements must be the same.

    Attributes
    ----------
    geometry : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener.

    """

    def __init__(self, shape=None, frame=None, angle=math.pi / 2, **kwargs):
        super(PlateFastener, self).__init__(**kwargs)
        self.frame = frame
        self._shape = shape
        self.angle = angle
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    def __repr__(self):
        # type: () -> str
        return "Plate Fastener(frame={!r}, name={})".format(self.frame, self.name)

    def __str__(self):
        # type: () -> str
        return "<Plate Fastener {} at frame={!r}>".format(self.name, self.frame)

    @classmethod
    def from_outline_thickness_interfaces_cutouts(
        cls, outline, angle=math.pi / 2, thickness=5, interfaces=None, cutouts=None, frame=None, **kwargs
    ):
        """
        Constructs a fastener from an outline, cutouts and thickness.
        This should be constructed on the XY plane and oriented with the x-axis pointing in the direction of the main_beam.centerline.

        Parameters
        ----------
        outline : list of :class:`~compas.geometry.Point`
            The outline of the fastener as a list of points.
        angle : float, optional
            The angle of the fastener. default is math.pi / 2
        thickness : float, optional
            The thickness of the fastener.
        interfaces : list of compas_timber.elements.FastenerTimberInterface, optional
            The connection interfaces to the timber elements
        cutouts : list of list of :class:`~compas.geometry.Point`, optional
            The cutouts of the fastener.
        frame : :class:`~compas.geometry.Frame`, optional
            The frame of the fastener, denoting its location in space.

        Returns
        -------
        :class:`~compas_timber.elements.PlateFastener`

        """
        plate_fastener = cls(**kwargs)
        plate_fastener.outline = outline
        plate_fastener.angle = angle
        plate_fastener.thickness = thickness
        plate_fastener.frame = frame
        for interface in interfaces:
            plate_fastener.add_interface(interface)
        plate_fastener.cutouts = cutouts
        return plate_fastener

    def add_interface(self, interface):
        """Add an interface to the fastener.

        Parameters
        ----------
        interface : :class:`~compas_timber.elements.FastenerTimberInterface`
            The interface to add.

        """
        interface.thickness = self.thickness
        interface.frame = self.frame
        interface.outline = None
        self.interfaces.append(interface)

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        for interface in self.interfaces:
            interface.frame = frame

    @property
    def holes(self):
        for interface in self.interfaces:
            for hole in interface.holes:
                yield hole

    @property
    def shapes(self):
        for interface in self.interfaces:
            for shape in interface.shapes:
                yield shape

    def place_instances(self, joint):
        """Adds the fasteners to the joint.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        frames = self.get_fastener_frames(joint)
        for frame in frames:
            fastener = self.copy()
            fastener.frame = Frame(frame.point, frame.xaxis, frame.yaxis)
            for interface, element in zip(fastener.interfaces, joint.elements):
                interface.element = element
            joint.fasteners.append(fastener)

    def get_fastener_frames(self, joint):
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
        front_face = beam_a.faces[front_face_index]
        front_point = Plane.from_frame(front_face).closest_point(int_point)
        front_frame = Frame(
            front_point,
            beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
            front_face.normal,
        )
        front_frame.rotate(-math.pi / 2, front_frame.xaxis, front_point)
        back_face = beam_a.faces[back_face_index]
        back_point = Plane.from_frame(back_face).closest_point(int_point)

        back_frame = Frame(
            back_point,
            beam_a.centerline.direction if main_param < 0.5 else -beam_a.centerline.direction,
            back_face.normal,
        )
        back_frame.rotate(-math.pi / 2, back_frame.xaxis, back_point)
        return [front_frame, back_frame]

    def validate_fastener_beam_compatibility(self, joint):
        """Checks if the beams are compatible with the joint and sets the front and back face indices.

        returns the front and back face indices of the cross beam.

        Raises
        ------
        BeamJoinningError
            If the beams are not compatible.

        """
        beam_a, beam_b = joint.elements[0:2]
        if not TOL.is_zero(angle_vectors(beam_a.frame.xaxis, beam_b.frame.xaxis) - self.angle):
            raise FastenerApplicationError(
                elements=[beam_a, beam_b], fastener=self, message="Beams are not perpendicular"
            )

        cross_vector = cross_vectors(beam_a.centerline.direction, beam_b.centerline.direction)
        main_faces = Beam.angle_beam_face_vector(beam_a, cross_vector)
        cross_faces = Beam.angle_beam_face_vector(beam_b, cross_vector)

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
                beam_a.faces[front_face_index].point,
                Plane.from_frame(beam_b.faces[cross_face_index]),
            )
        ):
            raise FastenerApplicationError(
                elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar"
            )
        back_face_index = (front_face_index + 2) % 4
        cross_back_face_index = (cross_face_index + 2) % 4
        if not TOL.is_zero(
            distance_point_plane(
                beam_a.faces[back_face_index].point,
                Plane.from_frame(beam_b.faces[cross_back_face_index]),
            )
        ):
            raise FastenerApplicationError(
                elements=[beam_a, beam_b], fastener=self, message="beam faces are not coplanar"
            )
        return front_face_index, back_face_index

    def add_features(self):
        """Adds the geometric features to the beams. TODO: add btlx features in separate function."""
        for beam, interface in zip([self.beam_a, self.beam_b], self.interfaces):
            interface.add_features(beam)

    @property
    def shape(self):
        """Constructs the base shape of the fastener.This is located at the origin of the XY plane with the x-axis pointing in the direction of the main_beam.

        Returns
        -------
        :class:`~compas.geometry.Brep`

        """
        if not self._shape:
            vector = Vector(0, 0, self.thickness)
            self._shape = Brep.from_extrusion(self.outline, vector)
            if self.cutouts:
                print("cutouts", self.cutouts)
                for cutout in self.cutouts:
                    cutout_brep = Brep.from_extrusion(cutout, vector)
                    self._shape -= cutout_brep
            if self.holes:
                for hole in self.holes:
                    cylinder = Brep.from_cylinder(
                        Cylinder(
                            hole["diameter"] * 0.5,
                            self.thickness * 2.0,
                            Frame(hole["point"], Vector(1.0, 0.0, 0.0), Vector(0.0, 1.0, 0.0)),
                        )
                    )
                    self._shape -= cylinder
            if self.shapes:
                for shape in self.shapes:
                    self._shape += shape
        return self._shape

    @property
    def geometry(self):
        """Constructs the geometry of the fastener as oriented in space.

        Returns
        -------
        :class:`~compas.geometry.Brep`

        """
        return self.shape.transformed(Transformation.from_frame(self.frame))
