import pytest

from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Frame
from compas.geometry import Vector
from compas.tolerance import Tolerance

from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxPart


@pytest.fixture
def mock_beam():
    centerline = Line(Point(x=-48.5210457646, y=19.8797883531, z=0.5), Point(x=-38.4606473128, y=23.5837423825, z=1.0))
    return Beam.from_centerline(centerline, width=1.0, height=1.0)


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


def test_beam_ref_faces(mock_beam):
    # https://www.design2machine.com/btlx/btlx_20.pdf page 5
    btlx_part = BTLxPart(mock_beam, 0)

    assert btlx_part.ref_side_from_face(mock_beam.faces[0]) == 2
    assert btlx_part.ref_side_from_face(mock_beam.faces[1]) == 1
    assert btlx_part.ref_side_from_face(mock_beam.faces[2]) == 4
    assert btlx_part.ref_side_from_face(mock_beam.faces[3]) == 3
    assert btlx_part.ref_side_from_face(mock_beam.faces[4]) == 5
    assert btlx_part.ref_side_from_face(mock_beam.faces[5]) == 6


def test_beam_ref_faces_attribute(mock_beam):
    ref_side_frames_expected = (
        Frame(
            point=Point(x=-48.67193560518159, y=20.35704602012424, z=0.0005429194857271558),
            xaxis=Vector(x=0.9374000278319115, y=0.3451241645032913, z=0.04658861337963174),
            yaxis=Vector(x=0.3454993211307862, y=-0.9384189997533969, z=-1.734723475976807e-18),
        ),
        Frame(
            point=Point(x=-48.7156552451492, y=20.340949685829152, z=0.9994570805142728),
            xaxis=Vector(x=0.9374000278319115, y=0.3451241645032913, z=0.04658861337963174),
            yaxis=Vector(x=0.04371963996761174, y=0.016096334295087427, z=-0.9989141610285457),
        ),
        Frame(
            point=Point(x=-48.37015592401841, y=19.402530686075757, z=0.9994570805142728),
            xaxis=Vector(x=0.9374000278319115, y=0.3451241645032913, z=0.04658861337963174),
            yaxis=Vector(x=-0.3454993211307862, y=0.9384189997533969, z=1.734723475976807e-18),
        ),
        Frame(
            point=Point(x=-48.3264362840508, y=19.41862702037084, z=0.000542919485727154),
            xaxis=Vector(x=0.9374000278319115, y=0.3451241645032913, z=0.04658861337963174),
            yaxis=Vector(x=-0.04371963996761174, y=-0.016096334295087427, z=0.9989141610285457),
        ),
        Frame(
            point=Point(x=-48.67193560518159, y=20.35704602012424, z=0.0005429194857271558),
            xaxis=Vector(x=0.3454993211307862, y=-0.9384189997533969, z=-1.734723475976807e-18),
            yaxis=Vector(x=-0.04371963996761173, y=-0.016096334295087424, z=0.9989141610285456),
        ),
        Frame(
            point=Point(x=-38.6552567933492, y=24.04490371522915, z=1.499457080514273),
            xaxis=Vector(x=0.3454993211307862, y=-0.9384189997533969, z=-1.734723475976807e-18),
            yaxis=Vector(x=0.04371963996761173, y=0.016096334295087424, z=-0.9989141610285456),
        ),
    )

    for index in range(6):
        ref_side = mock_beam.ref_sides[index]
        assert ref_side_frames_expected[index] == ref_side
        assert ref_side.name == "RS_{}".format(index + 1)


def test_beam_ref_edges(mock_beam):
    ref_edges_expected = (
        Line(
            Point(x=-48.67193560518159, y=20.35704602012424, z=0.0005429194857271558),
            Point(x=-38.61153715338159, y=24.06100004952424, z=0.5005429194857273),
        ),
        Line(
            Point(x=-48.7156552451492, y=20.340949685829152, z=0.9994570805142728),
            Point(x=-38.6552567933492, y=24.04490371522915, z=1.499457080514273),
        ),
        Line(
            Point(x=-48.37015592401841, y=19.402530686075757, z=0.9994570805142728),
            Point(x=-38.309757472218415, y=23.106484715475755, z=1.499457080514273),
        ),
        Line(
            Point(x=-48.3264362840508, y=19.41862702037084, z=0.000542919485727154),
            Point(x=-38.2660378322508, y=23.12258104977084, z=0.5005429194857273),
        ),
    )
    assert len(mock_beam.ref_edges) == 4

    for index in range(4):
        ref_edge = mock_beam.ref_edges[index]
        assert ref_edges_expected[index] == ref_edge
        assert ref_edge.name == "RE_{}".format(index + 1)


def test_are_these_faces_correct(tol):
    centerline = Line(Point(x=0.0, y=0.0, z=0.0), Point(x=1000.0, y=0.0, z=0.0))
    width = 60
    height = 120

    beam = Beam.from_centerline(centerline, width, height)

    rs_1 = beam.ref_sides[0]
    rs_2 = beam.ref_sides[1]
    rs_3 = beam.ref_sides[2]
    rs_4 = beam.ref_sides[3]
    rs_5 = beam.ref_sides[4]
    rs_6 = beam.ref_sides[5]

    assert tol.is_allclose(rs_1.xaxis, Vector.Xaxis())
    assert tol.is_allclose(rs_1.yaxis, -Vector.Yaxis())
    assert tol.is_allclose(rs_1.zaxis, -Vector.Zaxis())

    assert tol.is_allclose(rs_2.xaxis, Vector.Xaxis())
    assert tol.is_allclose(rs_2.yaxis, -Vector.Zaxis())
    assert tol.is_allclose(rs_2.zaxis, Vector.Yaxis())

    assert tol.is_allclose(rs_3.xaxis, Vector.Xaxis())
    assert tol.is_allclose(rs_3.yaxis, Vector.Yaxis())
    assert tol.is_allclose(rs_3.zaxis, Vector.Zaxis())

    assert tol.is_allclose(rs_4.xaxis, Vector.Xaxis())
    assert tol.is_allclose(rs_4.yaxis, Vector.Zaxis())
    assert tol.is_allclose(rs_4.zaxis, -Vector.Yaxis())

    assert tol.is_allclose(rs_5.xaxis, -Vector.Yaxis())
    assert tol.is_allclose(rs_5.yaxis, Vector.Zaxis())
    assert tol.is_allclose(rs_5.zaxis, -Vector.Xaxis())

    assert tol.is_allclose(rs_6.xaxis, -Vector.Yaxis())
    assert tol.is_allclose(rs_6.yaxis, -Vector.Zaxis())
    assert tol.is_allclose(rs_6.zaxis, Vector.Xaxis())
