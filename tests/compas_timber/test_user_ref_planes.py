import xml.etree.ElementTree as ET

import pytest

from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxPart
from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication.btlx import UserReferencePlane


@pytest.fixture
def beam():
    return Beam(Frame.worldXY(), length=1000, width=100, height=200)


@pytest.fixture
def custom_frame():
    return Frame(Point(500, 50, 100), Vector(0, 1, 0), Vector(0, 0, 1))


########################################################################
# UserReferencePlane
########################################################################


def test_user_ref_plane_construction(custom_frame):
    urp = UserReferencePlane(frame=custom_frame, ID=100)
    assert urp.ID == 100
    assert urp.frame is custom_frame


def test_user_ref_plane_id_must_be_int(custom_frame):
    with pytest.raises(TypeError):
        UserReferencePlane(frame=custom_frame, ID=100.0)


def test_user_ref_plane_id_must_be_gte_100(custom_frame):
    with pytest.raises(ValueError):
        UserReferencePlane(frame=custom_frame, ID=99)


########################################################################
# TimberElement API
########################################################################


def test_add_user_ref_plane_auto_id(beam, custom_frame):
    id_ = beam.add_user_ref_plane(custom_frame)
    assert id_ == 100


def test_add_second_user_ref_plane_auto_id(beam, custom_frame):
    beam.add_user_ref_plane(Frame.worldXY())
    id_ = beam.add_user_ref_plane(custom_frame)
    assert id_ == 101


def test_add_user_ref_plane_explicit_id(beam, custom_frame):
    id_ = beam.add_user_ref_plane(custom_frame, ID=150)
    assert id_ == 150


def test_add_user_ref_plane_duplicate_id_raises(beam, custom_frame):
    beam.add_user_ref_plane(custom_frame, ID=100)
    with pytest.raises(ValueError):
        beam.add_user_ref_plane(Frame.worldXY(), ID=100)


def test_get_user_ref_plane_returns_frame(beam, custom_frame):
    beam.add_user_ref_plane(custom_frame, ID=100)
    result = beam.get_user_ref_plane(100)
    assert result is custom_frame


def test_get_user_ref_plane_missing_returns_none(beam):
    assert beam.get_user_ref_plane(999) is None


def test_remove_user_ref_plane(beam, custom_frame):
    beam.add_user_ref_plane(custom_frame, ID=100)
    beam.remove_user_ref_plane(100)
    assert beam.get_user_ref_plane(100) is None
    assert len(beam.user_ref_planes) == 0


def test_user_ref_planes_multiple(beam):
    f1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    f2 = Frame(Point(100, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1))
    beam.add_user_ref_plane(f1)
    beam.add_user_ref_plane(f2)
    assert len(beam.user_ref_planes) == 2
    assert beam.user_ref_planes[0].ID == 100
    assert beam.user_ref_planes[1].ID == 101


########################################################################
# BTLxProcessing.ref_side_index validation
########################################################################


@pytest.mark.parametrize("valid", [0, 1, 5, 100, 101, 255])
def test_ref_side_index_valid(valid):
    cut = JackRafterCut(ref_side_index=valid)
    assert cut.ref_side_index == valid


@pytest.mark.parametrize("invalid", [6, 50, 99])
def test_ref_side_index_invalid(invalid):
    with pytest.raises(ValueError):
        JackRafterCut(ref_side_index=invalid)


########################################################################
# et_user_reference_planes XML export
########################################################################


def test_et_user_reference_planes_xml_structure(beam, custom_frame):
    beam.add_user_ref_plane(custom_frame, ID=100)
    part = BTLxPart(beam, order_num=1)

    xml_elem = part.et_user_reference_planes

    assert xml_elem.tag == "UserReferencePlanes"
    children = list(xml_elem)
    assert len(children) == 1
    assert children[0].get("ID") == "100"
    position = children[0].find("Position")
    assert position is not None
    assert position.find("ReferencePoint") is not None
    assert position.find("XVector") is not None
    assert position.find("YVector") is not None


def test_et_user_reference_planes_multiple(beam):
    beam.add_user_ref_plane(Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), ID=100)
    beam.add_user_ref_plane(Frame(Point(100, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), ID=101)
    part = BTLxPart(beam, order_num=1)

    xml_elem = part.et_user_reference_planes
    ids = [child.get("ID") for child in xml_elem]
    assert ids == ["100", "101"]


def test_et_user_reference_planes_world_to_local_round_trip(beam, custom_frame):
    """Plane stored in world coords is exported in part-local coords and can be recovered."""
    beam.add_user_ref_plane(custom_frame, ID=100)
    part = BTLxPart(beam, order_num=1)

    xml_elem = part.et_user_reference_planes
    ref_point_el = xml_elem.find("UserReferencePlane/Position/ReferencePoint")
    xvec_el = xml_elem.find("UserReferencePlane/Position/XVector")
    yvec_el = xml_elem.find("UserReferencePlane/Position/YVector")

    local_point = Point(float(ref_point_el.get("X")), float(ref_point_el.get("Y")), float(ref_point_el.get("Z")))
    xaxis = Vector(float(xvec_el.get("X")), float(xvec_el.get("Y")), float(xvec_el.get("Z")))
    yaxis = Vector(float(yvec_el.get("X")), float(yvec_el.get("Y")), float(yvec_el.get("Z")))

    # Reverse the export transform: local → world
    T_back = Transformation.from_frame(beam.ref_frame)
    recovered = Frame(local_point, xaxis, yaxis).transformed(T_back)

    assert TOL.is_close(recovered.point.x, custom_frame.point.x)
    assert TOL.is_close(recovered.point.y, custom_frame.point.y)
    assert TOL.is_close(recovered.point.z, custom_frame.point.z)
    assert TOL.is_close(abs(recovered.xaxis.dot(custom_frame.xaxis)), 1.0)
    assert TOL.is_close(abs(recovered.yaxis.dot(custom_frame.yaxis)), 1.0)
