import math
from compas.tolerance import TOL

from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import Rotation
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_line_plane
from compas.itertools import pairwise

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut, JackRafterCut

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class TMultistepJoint(Joint):
    """Represents an T-Step type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).
    Two or more cuts are is made on the main beam and a notch is made on the cross beam to fit the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TStepJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : int
        Shape of the step feature. 0: step, 1: heel, 2: double.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    step_shape : int
        Shape of the step feature. 0: step, 1: heel, 2: double.
    step_depth : float
        Depth of the step cut. Combined with a heel cut it generates a double step cut.
    heel_depth : float
        Depth of the heel cut. Combined with a step cut it generates a double step cut.
    tapered_heel : bool
        If True, the heel cut is tapered.
    tenon_mortise_height : float
        Height of the tenon (main beam) mortise (cross beam) of the Step Joint. If None, the tenon and mortise featrue is not created.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    @property
    def __data__(self):
        data = super(TMultistepJoint, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["step_count"] = self.step_count
        data["face_angle"] = self.face_angle
        data["back_angle"] = self.back_angle
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        step_count=None,
        face_angle=None,
        back_angle=None,
        **kwargs
    ):
        super(TMultistepJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)

        self.step_count = step_count
        self.face_angle = face_angle
        self.back_angle = back_angle

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.cross_beam]

    @property
    def cross_beam_ref_side_index(self):
        ref_side_dict = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_beam_ref_side_index(self):
        cross_beam_ref_side = self.cross_beam.ref_sides[self.cross_beam_ref_side_index]
        ref_side_dict = beam_ref_side_incidence_with_vector(
            self.main_beam, cross_beam_ref_side.normal, ignore_ends=True
        )
        ref_side_index = max(ref_side_dict, key=ref_side_dict.get)
        return ref_side_index

    @property
    def main_extension_plane(self):
        pt, _ = self._get_start_end_points()
        cv = cross_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)

        plane = Plane(pt, cross_vectors(cv, self.cross_beam.frame.xaxis))
        rotation = Rotation.from_axis_and_angle(cv, self.face_angle, pt)
        plane.transform(rotation)
        return plane

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.cross_beam and self.main_beam
        start_a = None
        try:
            plane_a = self.main_extension_plane
            start_a, end_a = self.main_beam.extension_to_plane(plane_a)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ae), debug_geometries=plane_a)
        except Exception as ex:
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.main_beam_guid)

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.main_beam and self.cross_beam  # should never happen

        if self.features:
            self.main_beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # get dimensions for main and cross beams
        cross_features = []
        planes = self._get_cut_planes()
        # planes_copy = [p for p in planes]
        # self.main_beam.add_features(JackRafterCut.from_plane_and_beam(planes_copy.pop(0), self.main_beam))
        # while len(planes_copy) > 1:
        #     pair = planes_copy.pop(0), planes_copy.pop(0)
        #     self.main_beam.add_features(DoubleCut.from_planes_and_beam(pair, self.main_beam))
        planes_copy = [Plane(p.point, -p.normal) for p in planes]
        while len(planes_copy) > 1:
            pair = planes_copy.pop(0), planes_copy.pop(0)
            self.cross_beam.add_features(DoubleCut.from_planes_and_beam(pair, self.cross_beam))


    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]


    def _get_start_end_points(self):

        cv = cross_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)
        
        crsi = self.cross_beam_ref_side_index
        crs = self.cross_beam.ref_sides[crsi]
        previous_ref_side = self.cross_beam.ref_sides[(crsi-1)%4]
        if dot_vectors(previous_ref_side.normal, cv) > 0:
            ref_edge_index = crsi
        else:
            ref_edge_index = (crsi-1)%4

        mrsi = self.main_beam_ref_side_index
        main_inside_face = self.main_beam.ref_sides[mrsi]
        main_outside_face = self.main_beam.ref_sides[(mrsi+2)%4]
        start_point = intersection_line_plane(self.cross_beam.ref_edges[ref_edge_index], Plane.from_frame(main_outside_face))
        end_point = intersection_line_plane(self.cross_beam.ref_edges[ref_edge_index], Plane.from_frame(main_inside_face))

        return Point(*start_point), Point(*end_point)

    def _get_extension_plane(self):
        pt, _ = self._get_start_end_points()
        cv = cross_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)

        plane = Plane(pt, -Vector(*cross_vectors(cv, self.cross_beam.frame.xaxis)))
        rotation = Rotation.from_axis_and_angle(cv, -self.face_angle*math.pi/180, pt)
        plane.transform(rotation)
        return plane

    def _get_cut_planes(self):
        pts = self._get_plane_points()
        cv = cross_vectors(self.main_beam.frame.xaxis, self.cross_beam.frame.xaxis)
        
        planes = []
        for face_pt, back_pt in pairwise(pts):
            face_plane = Plane(face_pt, Vector(*cross_vectors(cv, self.cross_beam.frame.xaxis)))
            back_plane = Plane(back_pt, Vector(*cross_vectors(cv, self.cross_beam.frame.xaxis)))

            face_rotation = Rotation.from_axis_and_angle(cv, -self.face_angle*math.pi/180, face_pt)
            back_rotation = Rotation.from_axis_and_angle(cv, self.back_angle*math.pi/180, back_pt)

            face_plane.transform(face_rotation)
            back_plane.transform(back_rotation)

            planes.extend([face_plane,back_plane])
        return planes



    def _get_plane_points(self):
        start, end = self._get_start_end_points()
        pts = [start]
        for i in range(1, self.step_count):
            shift = (i * (end-start))/self.step_count
            pts.append(start+shift)
        pts.append(end)
        return pts
      
