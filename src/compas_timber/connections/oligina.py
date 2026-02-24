from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import intersection_line_line
from compas.geometry import intersection_line_plane
from compas.tolerance import TOL

from compas_timber.connections import JointTopology
from compas_timber.connections import TenonMortiseJoint
from compas_timber.fabrication import Text

from .utilities import beam_ref_side_incidence_with_vector


class OliGinaJoint(TenonMortiseJoint):
    SUPPORTED_TOPOLOGY = [JointTopology.TOPO_T, JointTopology.TOPO_L]
    TEXT_HEIGHT_FACTOR = 0.4

    # fmt: off
    def __init__(
        self,
        main_beam,
        cross_beam,
        **kwargs
    ):
        super(OliGinaJoint, self).__init__(main_beam, cross_beam, **kwargs)


    @property
    def main_beam(self):
        return self.element_a

    @property
    def cross_beam(self):
        return self.element_b

    def add_features(self):
        super(OliGinaJoint, self).add_features()
        self.cross_beam.add_feature(self._make_oli_text())
        self.cross_beam.add_feature(self._make_date_text())
        self.main_beam.add_feature(self._make_gina_text())

    def _make_oli_text(self):
        # on cross beam
        # Find face: the one facing the main beam
        # find start_x: joint position plus offset by estimate size of text (and a bit) in direction of the start point
        ref_side_index = self.main_beam_ref_side_index
        p1, _ = intersection_line_line(self.main_beam.centerline, self.cross_beam.centerline, tol=TOL.absolute)
        assert p1

        plane = Plane(p1, self.cross_beam.centerline.direction)
        ref_side = self.cross_beam.ref_sides[ref_side_index]
        p1 = intersection_line_plane(Line.from_point_and_vector(ref_side.point, ref_side.xaxis), plane, tol=TOL.absolute)
        assert p1
        p1 = Point(*p1)

        translation_vector = -ref_side.xaxis
        offset = self.main_beam.width * 3.0
        p1.translate(translation_vector * offset)

        local_p1 = ref_side.to_local_coordinates(p1)
        start_x = local_p1.x

        text_height = self.cross_beam.height * self.TEXT_HEIGHT_FACTOR
        start_y = self.cross_beam.height * 0.2
        return Text("Oliver", start_x=start_x, start_y=start_y, text_height=text_height, ref_side_index=self.main_beam_ref_side_index)

    def _make_gina_text(self):
        # on main beam
        # Find face: the one facing the start point of cross beam
        # find start_x: joint position plus small offset in the direction away from the cross beam
        self.main_beam_ref_side_index
        incidence_vector = -self.cross_beam.centerline.direction
        ref_side_dict = beam_ref_side_incidence_with_vector(self.main_beam, incidence_vector, ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)  # type: ignore

        start_x = self.cross_beam.width * 2.0
        text_height = self.cross_beam.height * self.TEXT_HEIGHT_FACTOR
        start_y = self.cross_beam.height * 0.2
        return Text("Gina", start_x=start_x, start_y=start_y, text_height=text_height, ref_side_index=ref_side_index)


    def _make_date_text(self):
        # on cross beam
        # Find face: facing upwards
        # find start_x: joint position plus
        ref_side_dict = beam_ref_side_incidence_with_vector(self.cross_beam, Vector.Zaxis(), ignore_ends=True)
        ref_side_index = min(ref_side_dict, key=ref_side_dict.get)  # type: ignore

        p1, _ = intersection_line_line(self.main_beam.centerline, self.cross_beam.centerline, tol=TOL.absolute)
        assert p1

        plane = Plane(p1, self.cross_beam.centerline.direction)
        ref_side = self.cross_beam.ref_sides[ref_side_index]
        p1 = intersection_line_plane(Line.from_point_and_vector(ref_side.point, ref_side.xaxis), plane, tol=TOL.absolute)
        assert p1
        p1 = Point(*p1)

        translation_vector = -ref_side.xaxis
        offset = self.main_beam.width * 2.0
        p1.translate(translation_vector * offset)

        local_p1 = ref_side.to_local_coordinates(p1)
        start_x = local_p1.x

        start_y = self.cross_beam.height * 0.2
        return Text("3.5.2025", start_x=start_x, start_y=start_y, ref_side_index=ref_side_index)
