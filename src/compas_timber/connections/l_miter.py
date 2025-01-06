from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors

from compas_timber._fabrication import JackRafterCut
from compas_timber.errors import BeamJoinningError
from compas_timber.utils import intersection_line_line_param

from .joint import Joint
from .solver import JointTopology


class LMiterJoint(Joint):
    """Represents an L-Miter type joint which joins two beam in their ends, trimming them with a plane
    at the bisector angle between the beams' centerlines.

    This joint type is compatible with beams in L topology.

    Please use `LMiterJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LMiterJoint, self).__data__
        data["beam_a_guid"] = self.beam_a_guid
        data["beam_b_guid"] = self.beam_b_guid
        data["cutoff"] = self.cutoff
        return data

    def __init__(self, beam_a=None, beam_b=None, cutoff=None, **kwargs):
        super(LMiterJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = kwargs.get("beam_a_guid", None) or str(beam_a.guid)
        self.beam_b_guid = kwargs.get("beam_b_guid", None) or str(beam_b.guid)
        self.cutoff = cutoff  # for very acute angles, limit the extension of the tip/beak of the joint
        self.features = []

    @property
    def elements(self):
        return [self.beam_a, self.beam_b]

    def get_cutting_planes(self):
        assert self.beam_a and self.beam_b
        vA = Vector(*self.beam_a.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.beam_b.frame.xaxis)
        # intersection point (average) of both centrelines
        [pxA, tA], [pxB, tB] = intersection_line_line_param(
            self.beam_a.centerline,
            self.beam_b.centerline,
            max_distance=float("inf"),
            limit_to_segments=False,
        )
        # TODO: add error-trap + solution for I-miter joints

        p = Point((pxA.x + pxB.x) * 0.5, (pxA.y + pxB.y) * 0.5, (pxA.z + pxB.z) * 0.5)

        # makes sure they point outward of a joint point
        tA, _ = self.beam_a.endpoint_closest_to_point(pxA)
        if tA == "end":
            vA *= -1.0
        tB, _ = self.beam_b.endpoint_closest_to_point(pxB)
        if tB == "end":
            vB *= -1.0

        # bisector
        v_bisector = vA + vB
        v_bisector.unitize()

        # get frame
        v_perp = Vector(*cross_vectors(v_bisector, vA))
        v_normal = Vector(*cross_vectors(v_bisector, v_perp))

        plnA = Plane(p, v_normal)
        plnB = Plane(p, v_normal * -1.0)

        plnA = Frame.from_plane(plnA)
        plnB = Frame.from_plane(plnB)
        return plnA, plnB

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoinningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b
        start_a, start_b = None, None
        try:
            plane_a, plane_b = self.get_cutting_planes()
            start_a, end_a = self.beam_a.extension_to_plane(plane_a)
            start_b, end_b = self.beam_b.extension_to_plane(plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [plane_b] if start_a is not None else [plane_a]
            raise BeamJoinningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoinningError(self.elements, self, debug_info=str(ex))
        self.beam_a.add_blank_extension(start_a, end_a, self.guid)
        self.beam_b.add_blank_extension(start_b, end_b, self.guid)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        assert self.beam_a and self.beam_b

        if self.features:
            self.beam_a.remove_features(self.features)
            self.beam_b.remove_features(self.features)

        try:
            plane_a, plane_b = self.get_cutting_planes()
        except Exception as ex:
            raise BeamJoinningError(self.elements, self, debug_info=str(ex))

        cut1 = JackRafterCut.from_plane_and_beam(plane_a, self.beam_a)
        cut2 = JackRafterCut.from_plane_and_beam(plane_b, self.beam_b)
        self.beam_a.add_features(cut1)
        self.beam_b.add_features(cut2)
        self.features = [cut1, cut2]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model.element_by_guid(self.main_beam_guid)
        self.cross_beam = model.element_by_guid(self.cross_beam_guid)
