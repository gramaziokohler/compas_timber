from compas.geometry import Point
from compas.geometry import Scale
from compas.geometry import Line
from compas.tolerance import TOL

from compas_timber.model import TimberModel
from compas_timber.elements import Beam


def test_scale_beam_standalone():
    width, height = 0.100, 0.200
    centerline = Line(Point(0, 0, 0), Point(12, 0, 0))
    beam = Beam.from_centerline(centerline, width=width, height=height)

    beam.transform(Scale.from_factors([1000] * 3))

    assert TOL.is_close(beam.width, width * 1000)
    assert TOL.is_close(beam.height, height * 1000)
    assert TOL.is_close(beam.centerline.length, centerline.length * 1000)


def test_scale_beam_in_model():
    model = TimberModel()
    width, height = 0.100, 0.200
    centerline = Line(Point(0, 0, 0), Point(12, 0, 0))
    beam = Beam.from_centerline(centerline, width=width, height=height)

    model.add_element(beam)

    model.transform(Scale.from_factors([1000] * 3))

    assert TOL.is_close(beam.width, width * 1000)
    assert TOL.is_close(beam.height, height * 1000)
    assert TOL.is_close(beam.centerline.length, centerline.length * 1000)
