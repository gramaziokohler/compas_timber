import pytest
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.connections import TOliGinaJoint
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def beams():
    """Create test fixtures with beams in T-topology."""
    main_centerline = Line(Point(0, 0, 0), Point(1000, 0, 0))
    main_beam = Beam.from_centerline(main_centerline, width=80, height=100)

    cross_centerline = Line(Point(500, -300, 0), Point(500, 300, 0))
    cross_beam = Beam.from_centerline(cross_centerline, width=80, height=100)

    return main_beam, cross_beam


def test_add_features_tracks_all_beam_features(beams):
    """joint.features must include the oli/date/gina text features, not just the tenon and mortise."""
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = TOliGinaJoint.create(model, main_beam, cross_beam)
    joint.add_extensions()

    joint.add_features()

    total_applied = len(main_beam.features) + len(cross_beam.features)
    assert total_applied > 0
    assert len(joint.features) == total_applied


def test_clear_features_removes_all_beam_features(beams):
    main_beam, cross_beam = beams
    model = TimberModel()
    model.add_element(main_beam)
    model.add_element(cross_beam)
    joint = TOliGinaJoint.create(model, main_beam, cross_beam)
    joint.add_extensions()
    joint.add_features()

    joint.clear_features()

    assert joint.features == []
    assert main_beam.features == []
    assert cross_beam.features == []
