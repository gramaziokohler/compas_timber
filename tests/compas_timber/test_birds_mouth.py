import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import is_point_on_plane
from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication.birds_mouth import BirdsMouth
from compas_timber.fabrication.btlx import OrientationType


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


@pytest.fixture
def beam():
    """Beam 80 x 200 x 1000 mm along the +X axis.

    Corresponds to Grasshopper output:
        Beam 80.000 x 200.000 x 1000.000
        at Frame(Point(0, 0, 0), xaxis=(1,0,0), yaxis=(0,1,0))
    """
    return Beam.from_centerline(
        Line(Point(0.0, 0.0, 0.0), Point(1000.0, 0.0, 0.0)),
        width=80,
        height=200,
    )


@pytest.fixture
def notch_planes():
    """Two cutting planes defining a birds mouth notch verified in Grasshopper.

    Expected BTLx params when applied to `beam`:
        Orientation=start, StartX=525.419, StartY=0.000, StartDepth=36.752,
        Angle=45.000, Inclination1=45.000, Inclination2=135.000,
        Depth=36.752, Width=80.000
    """
    return [
        Plane(
            Point(472.3402264539873, -27.6597812114272, 92.05492956046777),
            Vector(0.5, 0.5000000000000002, 0.7071067811865476),
        ),
        Plane(
            Point(520.3693375887088, 20.36932992329436, 102.36517986799373),
            Vector(-0.5000000000000004, -0.49999999999999967, 0.7071067811865476),
        ),
    ]


def test_birds_mouth_from_planes_params(tol, beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam)

    assert bm.orientation == OrientationType.START
    assert tol.is_close(bm.start_x, 525.419)
    assert tol.is_close(bm.start_y, 0.0)
    assert tol.is_close(bm.start_depth, 36.752)
    assert tol.is_close(bm.angle, 45.0)
    assert tol.is_close(bm.inclination_1, 45.0)
    assert tol.is_close(bm.inclination_2, 135.0)
    assert tol.is_close(bm.depth, 36.752)
    assert tol.is_close(bm.width, 80.0)
    assert bm.face_limited_front is False
    assert bm.face_limited_back is False


def test_birds_mouth_planes_round_trip(tol, beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam)
    reconstructed = bm.planes_from_params_and_beam(beam)

    assert len(reconstructed) == 2
    for reconstructed_plane, input_plane in zip(reconstructed, notch_planes):
        assert reconstructed_plane.is_parallel(input_plane, tol=tol.absolute)
        assert is_point_on_plane(reconstructed_plane.point, input_plane, tol=tol.absolute)


def test_birds_mouth_face_limited_front(beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam, start_y=20.0)

    assert bm.face_limited_front is True
    assert bm.face_limited_back is False


def test_birds_mouth_face_limited_back(beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam, width=60.0)

    assert bm.face_limited_front is False
    assert bm.face_limited_back is True


def test_birds_mouth_serialization(tol, beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam)
    restored = json_loads(json_dumps(bm))

    assert restored.ref_side_index == bm.ref_side_index
    assert restored.orientation == bm.orientation
    assert tol.is_close(restored.start_x, bm.start_x)
    assert tol.is_close(restored.start_y, bm.start_y)
    assert tol.is_close(restored.start_depth, bm.start_depth)
    assert tol.is_close(restored.angle, bm.angle)
    assert tol.is_close(restored.inclination_1, bm.inclination_1)
    assert tol.is_close(restored.inclination_2, bm.inclination_2)
    assert tol.is_close(restored.depth, bm.depth)
    assert tol.is_close(restored.width, bm.width)
    assert restored.face_limited_front == bm.face_limited_front
    assert restored.face_limited_back == bm.face_limited_back


def test_birds_mouth_scaled(tol, beam, notch_planes):
    bm = BirdsMouth.from_planes_and_beam(notch_planes, beam)
    scaled = bm.scaled(2.0)

    assert tol.is_close(scaled.start_x, bm.start_x * 2.0)
    assert tol.is_close(scaled.start_depth, bm.start_depth * 2.0)
    assert tol.is_close(scaled.depth, bm.depth * 2.0)
    assert tol.is_close(scaled.width, bm.width * 2.0)
    # angles are not scaled
    assert tol.is_close(scaled.angle, bm.angle)
    assert tol.is_close(scaled.inclination_1, bm.inclination_1)
    assert tol.is_close(scaled.inclination_2, bm.inclination_2)


def test_birds_mouth_requires_two_planes(beam, notch_planes):
    with pytest.raises(ValueError):
        BirdsMouth.from_planes_and_beam([notch_planes[0]], beam)
