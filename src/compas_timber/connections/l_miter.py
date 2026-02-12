import math

from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors
from compas.geometry import dot_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.geometry import is_point_behind_plane
from compas.tolerance import TOL

from compas_timber.connections.utilities import beam_ref_side_incidence
from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.utils import intersection_line_line_param

from .joint import Joint
from .solver import JointTopology
from .utilities import point_centerline_towards_joint


class LMiterJoint(Joint):
    """Represents an L-Miter type joint which joins two beam in their ends, trimming them with a plane
    at the bisector angle between the beams' centerlines.

    This joint type is compatible with beams in L topology.

    Please use `LMiterJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    cutoff : bool, optional
        If True, the beams will be trimmed with a plane perpendicular to the bisector (miter) plane of the beams.
    miter_plane : :class:`~compas.geometry.Plane`, optional
        A plane that defines the miter cut location and orientation.
        If not provided, it will be calculated automatically.
        If provided, miter_type will be automatically set to `MiterType.USER_DEFINED`.
    miter_type : :class: `~compas_timber.connections.MiterType`, optional
        one of `MiterType.BISECTOR`, `MiterType.REF_SURFACES`, or `MiterType.USER_DEFINED`.
        If `USER_DEFINED`, a `miter_plane` must be provided.
    clean : bool, optional
        if True, cleaning cuts will be applied to each beam based on the back sides of the other beam.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    cutoff : bool, optional
        If True, the beams will be trimmed with a plane perpendicular to the bisector (miter) plane of the beams.
    miter_plane : :class:`~compas.geometry.Plane`, optional
        A plane that defines the miter cut location and orientation.
    miter_type : :class: `~compas_timber.connections.MiterType`
        one of `MiterType.BISECTOR`, `MiterType.REF_SURFACES`, or `MiterType.USER_DEFINED`.
    clean : bool, optional
        if True, cleaning cuts will be applied to each beam based on the back sides of the other beam.
    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L

    @property
    def __data__(self):
        data = super(LMiterJoint, self).__data__
        data["beam_a_guid"] = self.beam_a_guid
        data["beam_b_guid"] = self.beam_b_guid
        data["cutoff"] = self.cutoff
        data["ref_side_miter"] = self.ref_side_miter
        data["miter_plane"] = self.miter_plane
        data["clean"] = self.clean

        return data

    def __init__(self, beam_a=None, beam_b=None, cutoff=None, miter_plane=None, ref_side_miter=False, clean=False, **kwargs):
        super(LMiterJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = kwargs.get("beam_a_guid", None) or str(beam_a.guid)
        self.beam_b_guid = kwargs.get("beam_b_guid", None) or str(beam_b.guid)
        self.miter_plane = miter_plane
        self.ref_side_miter = ref_side_miter
        self.cutoff = cutoff
        self.clean = clean
        self.features = []
        self._back_a_index = None
        self._back_b_index = None
                
    @property
    def elements(self):
        return [self.beam_a, self.beam_b]

    def _get_cut_planes_from_miter_plane(self, miter_plane):
        # create two cutting planes from the butt plane
        pln_a = miter_plane
        pln_b = Plane(miter_plane.point, -miter_plane.normal)
        if dot_vectors(Vector.from_start_end(miter_plane.point, self.beam_a.centerline.midpoint), miter_plane.normal) > 0:
            pln_a, pln_b = pln_b, pln_a
        return pln_a, pln_b

    def _get_cut_planes_from_ref_sides(self):
        # get the cutting planes from the reference sides of the beams
        assert self.beam_a and self.beam_b

        ref_sides_a: dict[int,float] = beam_ref_side_incidence(self.beam_b, self.beam_a)
        self._back_a_index = max(ref_sides_a, key=ref_sides_a.get)
        back_a = Plane.from_frame(self.beam_a.ref_sides[self._back_a_index])
        front_a = Plane.from_frame(self.beam_a.ref_sides[(self._back_a_index+2)%4])

        ref_sides_b = beam_ref_side_incidence(self.beam_a, self.beam_b)
        self._back_b_index = max(ref_sides_b, key=ref_sides_b.get)
        back_b = Plane.from_frame(self.beam_b.ref_sides[self._back_b_index])
        front_b = Plane.from_frame(self.beam_b.ref_sides[(self._back_b_index+2)%4])

        inside_x = intersection_plane_plane(front_a, front_b)
        outside_x = intersection_plane_plane(back_a, back_b)

        return Plane.from_points([outside_x[0], outside_x[1], inside_x[0]])

    def _get_cutting_planes(self):
        assert self.beam_a and self.beam_b
        # user defined miter plane
        if self.miter_plane:
            return self._get_cut_planes_from_miter_plane(self.miter_plane)
        # ref_side_miter = True
        elif self.ref_side_miter:
            miter_plane = self._get_cut_planes_from_ref_sides()
            return self._get_cut_planes_from_miter_plane(miter_plane)
        # miter_type = MiterType.BISECTOR
        vA = Vector(*self.beam_a.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.beam_b.frame.xaxis)
        # intersection point (average) of both centrelines
        p = self.location
        if not p:
            [pxA, tA], [pxB, tB] = intersection_line_line_param(
                self.beam_a.centerline,
                self.beam_b.centerline,
                max_distance=float("inf"),
                limit_to_segments=False,
            )
            # TODO: add error-trap + solution for I-miter joints

            p = Point((pxA.x + pxB.x) * 0.5, (pxA.y + pxB.y) * 0.5, (pxA.z + pxB.z) * 0.5)

        # makes sure they point outward of a joint point
        tA, _ = self.beam_a.endpoint_closest_to_point(p)
        if tA == "end":
            vA *= -1.0
        tB, _ = self.beam_b.endpoint_closest_to_point(p)
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

        return plnA, plnB

    def _get_cutoff_plane(self):
        """Returns a plane that is perpendicular to the miter plane at the intersection point of the two centerlines."""
        cutting_plane = self._get_cutting_planes()[0]
        cross_vect = cross_vectors(self.beam_a.centerline.direction, self.beam_b.centerline.direction)

        cutoff_plane = cutting_plane.rotated(math.pi / 2, cross_vect, point=cutting_plane.point)
        if cutoff_plane.normal.dot(point_centerline_towards_joint(*self.elements)) < 0:
            cutoff_plane.xaxis = -cutoff_plane.xaxis
        return cutoff_plane

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.beam_a and self.beam_b
        start_a, start_b = None, None
        try:
            if self.cutoff:
                plane_a = self._get_cutoff_plane()
                plane_b = plane_a.copy()
            else:
                plane_a, plane_b = self._get_cutting_planes()
            start_a, end_a = self.beam_a.extension_to_plane(plane_a)
            start_b, end_b = self.beam_b.extension_to_plane(plane_b)
        except AttributeError as ae:
            # I want here just the plane that caused the error
            geometries = [plane_b] if start_a is not None and plane_b else [plane_a] if plane_a else []
            raise BeamJoiningError(self.elements, self, debug_info=str(ae), debug_geometries=geometries)
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
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
            miter_plane_a, miter_plane_b = self._get_cutting_planes()
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))

        cut1 = JackRafterCutProxy.from_plane_and_beam(miter_plane_a, self.beam_a)
        cut2 = JackRafterCutProxy.from_plane_and_beam(miter_plane_b, self.beam_b)
        self.beam_a.add_features(cut1)
        self.beam_b.add_features(cut2)
        self.features = [cut1, cut2]

        # add cutoffs if necessary
        if self.cutoff:
            cutoff_plane = self._get_cutoff_plane()
            for beam in self.elements:
                cutoff = JackRafterCutProxy.from_plane_and_beam(cutoff_plane, beam)
                beam.add_features(cutoff)
                self.features.append(cutoff)

        if self.clean:
            def get_valid_trim_planes(ref_side_beam, beam_to_trim, miter_plane, back_index):
                trim_planes = []
                vector = Vector.from_start_end(beam_to_trim.centerline.midpoint, self.location)
                for i, frame in enumerate(ref_side_beam.ref_sides[0:4]):
                    if i == back_index:
                        # if self.ref_side_miter == True, one of the ref sides is used to generate the miter plane, so it isn't used for trimming. 
                        continue

                    test_plane = Plane.from_frame(frame)
                    #only use the outside ref_sides ie those facing away from the beam to be trimmed.
                    if not TOL.is_positive(dot_vectors(vector, test_plane.normal)):
                        continue
                    use_plane = False
                    #parse planes that don't actually intersect beam geometry
                    #if any edge intersection is behind another plane, then this plane will trim the geometry and should be applied
                    for edge in beam_to_trim.ref_edges:
                        pt = intersection_line_plane(edge, test_plane)
                        for plane in [miter_plane] + trim_planes:
                            if is_point_behind_plane(pt, plane):
                                trim_planes.append(test_plane)
                                use_plane = True
                                break
                        if use_plane:
                            break
                return trim_planes

            back_a = get_valid_trim_planes(self.beam_a, self.beam_b, miter_plane_b, self._back_a_index)
            back_b = get_valid_trim_planes(self.beam_b, self.beam_a, miter_plane_a, self._back_b_index)

            clean_cuts_a = [JackRafterCutProxy.from_plane_and_beam(cut, self.beam_a) for cut in back_b]
            clean_cuts_b = [JackRafterCutProxy.from_plane_and_beam(cut, self.beam_b) for cut in back_a]

            self.beam_a.add_features(clean_cuts_a)
            self.beam_b.add_features(clean_cuts_b)
            self.features.extend(clean_cuts_a)
            self.features.extend(clean_cuts_b)

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model[self.beam_a_guid]
        self.beam_b = model[self.beam_b_guid]
