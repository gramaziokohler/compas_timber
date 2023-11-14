from compas.geometry import close
from compas.geometry import allclose
from compas.geometry import Point

from compas_timber.parts import Beam


def test_add_extend_start_feature():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.10, end=0.0)

    assert close(beam.blank.xsize, 1.1)


def test_add_extend_end_feature():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)

    beam.add_blank_extension(start=0.0, end=0.10)

    assert close(beam.blank.xsize, 1.1)
    # TODO: assert was extended at end and not at start


def test_extend_both_start_end():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)

    beam.add_blank_extension(start=0.10, end=0.10)

    assert close(beam.blank.xsize, 1.2)


def test_accumulate_extension():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.0, end=0.10)
    beam.add_blank_extension(start=0.0, end=0.20)

    # max extension is used
    assert close(beam.blank.xsize, 1.20)


def test_remove_parametric_extension():
    start = Point(0.0, 0.0, 0.0)
    end = Point(1.0, 0.0, 0.0)
    beam = Beam.from_endpoints(start, end, 0.06, 0.12)
    beam.add_blank_extension(start=0.0, end=0.10)

    assert close(beam.blank.xsize, 1.10)
