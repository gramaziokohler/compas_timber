import pytest

from compas.geometry import Point
from compas.geometry import Line

from compas_timber.connections import NBeamKDTreeAnalyzer
from compas_timber.connections import CompositeAnalyzer
from compas_timber.connections import QuadAnalyzer
from compas_timber.connections import TripletAnalyzer
from compas_timber.elements import Beam
from compas_timber.model import TimberModel


@pytest.fixture
def two_triplets_beams():
    height, width = (12, 6)

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
    ]

    return [Beam.from_centerline(centerline=line, height=height, width=width) for line in lines]


@pytest.fixture
def one_triplet_two_quads_beams():
    height, width = (12, 6)

    lines = [
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=300.0, y=200.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=-40.0, y=270.0, z=0.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=0.0, y=20.0, z=160.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=168.58797240614388, y=-95.31137353132192, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=330.0, y=350.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=500.0, y=0.0, z=0.0)),
        Line(Point(x=300.0, y=200.0, z=0.0), Point(x=220.0, y=170.0, z=-120.0)),
        Line(Point(x=-10.0, y=-10.0, z=0.0), Point(x=90.0, y=-220.0, z=0.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=220.0, z=130.0)),
        Line(Point(x=45.89488087618746, y=234.15459672257862, z=0.0), Point(x=0.0, y=260.0, z=-120.0)),
    ]

    return [Beam.from_centerline(centerline=line, height=height, width=width) for line in lines]


def test_analyzer_empty_model():
    with pytest.raises(ValueError):
        _ = NBeamKDTreeAnalyzer(TimberModel())


def test_two_triplet_analyzer(two_triplets_beams):
    model = TimberModel()
    model.add_elements(two_triplets_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=3)

    clusters = analyzer.find()
    assert len(clusters) == 2
    assert all(len(cluster) == 3 for cluster in clusters)


def test_one_triplet_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=3)

    clusters = analyzer.find()
    assert len(clusters) == 1  # We expect two triplets from the provided beams
    assert len(clusters[0]) == 3


def test_two_quads_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = NBeamKDTreeAnalyzer(model, n=4)

    clusters = analyzer.find()
    assert len(clusters) == 2
    assert all(len(cluster) == 4 for cluster in clusters)


def test_composite_analyzer(one_triplet_two_quads_beams):
    model = TimberModel()
    model.add_elements(one_triplet_two_quads_beams)
    model.connect_adjacent_beams()

    analyzer = CompositeAnalyzer.from_model(model=model, analyzers_cls=[QuadAnalyzer, TripletAnalyzer])

    clusters = analyzer.find()

    triplets = [cluster for cluster in clusters if len(cluster) == 3]
    quads = [cluster for cluster in clusters if len(cluster) == 4]
    assert len(triplets) == 1
    assert len(quads) == 2
