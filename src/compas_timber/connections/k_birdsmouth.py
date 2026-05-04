from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import cross_vectors

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import DoubleCut
from compas_timber.fabrication import Lap
from compas_timber.fabrication.jack_cut import JackRafterCut
from compas_timber.utils import intersection_line_line_param

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class KBirdsmouthJoint(Joint):
    """Represents a T-Birdsmouth type joint which joins two beams, one of them at it's end (main) and the other one along it's centerline (cross).

    This joint type is compatible with beams in T topology.

    Please use `TBirdsmouth.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    mill_depth : float
        The depth of the pockets to be milled on the cross beam.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        Second beam to be joined.
    mill_depth : float
        The depth of the pockets to be milled on the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_K

    @property
    def __data__(self):
        data = super(KBirdsmouthJoint, self).__data__
        data["mill_depth"] = self.mill_depth
        return data

    def __init__(self, cross_beam=None, main_beam_a=None, main_beam_b=None, mill_depth=None, **kwargs):
        super(KBirdsmouthJoint, self).__init__(elements=(cross_beam, main_beam_a, main_beam_b), **kwargs)
        self.mill_depth = mill_depth
        self.features = []  # TODO: remove?

    @property
    def beams(self):
        return self.elements

    @property
    def main_beams(self):
        return self.elements[1:]

    @property
    def cross_beam(self):
        return self.element_a

    @property
    def main_beam_a(self):
        return self.element_b

    @property
    def main_beam_b(self):
        return self.elements[2]

    @property
    def cross_ref_side_indices(self):
        indices = []
        for main_beam in self.main_beams:
            ref_side_dict = beam_ref_side_incidence(main_beam, self.cross_beam, ignore_ends=True)
            ref_side_indices = sorted(ref_side_dict, key=ref_side_dict.get)[:2]
            indices.append(ref_side_indices)
        # sort each pair so the shared (common) index is always first
        common = set(indices[0]) & set(indices[1])
        if common:
            common_idx = next(iter(common))
            indices = [sorted(pair, key=lambda i: i != common_idx) for pair in indices]
        return indices

    def _get_cutting_planes(self):
        all_cutting_planes = []
        for pair in self.cross_ref_side_indices:
            cutting_planes = [self.cross_beam.ref_sides[index] for index in pair]
            all_cutting_planes.append(cutting_planes)

        if self.mill_depth:
            for cutting_planes in all_cutting_planes:
                cutting_planes[0].translate(-cutting_planes[0].normal * self.mill_depth)
        return all_cutting_planes

    def _get_miter_planes(self):
        # default bisector miter plane
        vA = Vector(*self.main_beam_a.frame.xaxis)  # frame.axis gives a reference, not a copy
        vB = Vector(*self.main_beam_b.frame.xaxis)
        # intersection point (average) of both centrelines
        try:
            p = self.location
        except ValueError:
            p = None

        if not p:
            [pxA, tA], [pxB, tB] = intersection_line_line_param(
                self.main_beam_a.centerline,
                self.main_beam_b.centerline,
                max_distance=float("inf"),
                limit_to_segments=False,
            )
            # TODO: add error-trap + solution for I-miter joints

            p = Point((pxA.x + pxB.x) * 0.5, (pxA.y + pxB.y) * 0.5, (pxA.z + pxB.z) * 0.5)

        # makes sure they point outward of a joint point
        vA = self.point_centerline_towards_joint(self.main_beam_a, p)
        vB = self.point_centerline_towards_joint(self.main_beam_b, p)

        # bisector
        v_bisector = vA + vB
        v_bisector.unitize()

        # get frame
        v_perp = Vector(*cross_vectors(v_bisector, vA))
        v_normal = Vector(*cross_vectors(v_bisector, v_perp))

        plnA = Plane(p, v_normal)
        plnB = Plane(p, v_normal * -1.0)

        return plnB, plnA

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        Raises
        ------
        BeamJoiningError
            If the extension could not be calculated.

        """
        assert self.main_beams and self.cross_beam
        for beam in self.main_beams:
            start_a, end_a = None, None
            miter_plane = self._get_miter_planes()[0]
            try:
                start_a, end_a = beam.extension_to_plane(miter_plane)
            except Exception as ex:
                raise BeamJoiningError(self.elements, self, debug_info=str(ex))
            beam.add_blank_extension(start_a, end_a, self.guid)

    def add_features(self):
        """Adds the required trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """

        assert self.main_beams and self.cross_beam  # should never happen

        if self.features:
            for beam in self.main_beams:
                beam.remove_features(self.features)
            self.cross_beam.remove_features(self.features)

        # generate double cut feature for each main beam
        for main_beam, cutting_planes in zip(self.main_beams, self._get_cutting_planes()):
            main_feature = DoubleCut.from_planes_and_beam(cutting_planes, main_beam)
            main_beam.add_features(main_feature)
            self.features.append(main_feature)

        # generate miter cut features for each main beam
        miter_planes = self._get_miter_planes()
        for main_beam, miter_plane in zip(self.main_beams, miter_planes):
            miter_feature = JackRafterCut.from_plane_and_beam(miter_plane, main_beam)
            main_beam.add_features(miter_feature)
            self.features.append(miter_feature)

        if self.mill_depth:
            main_beam = self.main_beams[0]
            main_ref_side_index = self.features[0].ref_side_index
            lap_cutting_plane = main_beam.ref_sides[main_ref_side_index]
            lap_length = main_beam.get_dimensions_relative_to_side(main_ref_side_index)[1]
            common_ref_side_index = self.cross_ref_side_indices[0][0]

            cross_feature = Lap.from_plane_and_beam(
                lap_cutting_plane,
                self.cross_beam,
                lap_length,
                self.mill_depth,
                ref_side_index=common_ref_side_index,
            )

            self.cross_beam.add_features(cross_feature)
            self.features.append(cross_feature)
