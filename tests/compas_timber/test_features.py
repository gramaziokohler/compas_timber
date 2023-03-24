from compas.geometry import close
from compas.geometry import Point

from compas_timber.parts import Beam
from compas_timber.parts import BeamExtensionFeature


def test_add_extend_start_feature():
    start = Point(0., 0., 0.)
    end = Point(1., 0., 0.)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12, geometry_type="mesh")
    extension = BeamExtensionFeature(extend_start_by=0.10, extend_end_by=0.0)

    beam.add_feature(extension, apply=True)

    assert close(beam.length, 1.1)
    assert close(beam.centerline_start.x, -0.10)


def test_add_extend_end_feature():
    start = Point(0., 0., 0.)
    end = Point(1., 0., 0.)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12, geometry_type="mesh")
    extension = BeamExtensionFeature(extend_start_by=0.0, extend_end_by=0.10)

    beam.add_feature(extension, apply=True)

    assert close(beam.length, 1.1)
    assert close(beam.centerline_end.x, 1.1)


def test_extend_both_start_end():
    start = Point(0., 0., 0.)
    end = Point(1., 0., 0.)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12, geometry_type="mesh")
    extension = BeamExtensionFeature(extend_start_by=0.10, extend_end_by=0.10)

    beam.add_feature(extension, apply=True)

    assert close(beam.length, 1.2)
    assert close(beam.centerline_end.x, 1.1)
    assert close(beam.centerline_start.x, -0.10)


def test_accumulate_extension():
    start = Point(0., 0., 0.)
    end = Point(1., 0., 0.)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12, geometry_type="mesh")
    extension_a = BeamExtensionFeature(extend_start_by=0.0, extend_end_by=0.10)
    extension_b = BeamExtensionFeature(extend_start_by=0.0, extend_end_by=0.20)

    beam.add_feature(extension_a)
    beam.add_feature(extension_b)

    errors = beam.apply_features()

    assert not errors
    # max extension is used
    assert close(beam.length, 1.20)
    assert close(beam.centerline_end.x, 1.20)


def test_remove_parametric_extension():
    start = Point(0., 0., 0.)
    end = Point(1., 0., 0.)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12, geometry_type="mesh")
    extension_a = BeamExtensionFeature(extend_start_by=0.0, extend_end_by=0.10)

    beam.add_feature(extension_a)
    errors = beam.apply_features()

    assert not errors
    assert close(beam.length, 1.10)
    assert close(beam.centerline_end.x, 1.10)

