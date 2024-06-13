import pytest

from compas.geometry import Line
from compas.geometry import Point

from compas_timber.elements import Beam
from compas_timber.fabrication import BTLxPart


@pytest.fixture
def mock_beam():
    centerline = Line(Point(x=-48.5210457646, y=19.8797883531, z=0.5), Point(x=-38.4606473128, y=23.5837423825, z=1.0))
    return Beam.from_centerline(centerline, width=1.0, height=1.0)


def test_beam_ref_faces(mock_beam):
    # https://www.design2machine.com/btlx/btlx_20.pdf page 5
    btlx_part = BTLxPart(mock_beam, 0)

    assert btlx_part.ref_side_from_face(mock_beam.faces[0]) == 3
    assert btlx_part.ref_side_from_face(mock_beam.faces[1]) == 2
    assert btlx_part.ref_side_from_face(mock_beam.faces[2]) == 1
    assert btlx_part.ref_side_from_face(mock_beam.faces[3]) == 4
    assert btlx_part.ref_side_from_face(mock_beam.faces[4]) == 5
    assert btlx_part.ref_side_from_face(mock_beam.faces[5]) == 6
