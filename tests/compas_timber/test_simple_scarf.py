import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Polyhedron
from compas.geometry import Vector

from compas_timber.elements import Beam
from compas_timber.errors import FeatureApplicationError
from compas_timber.fabrication import SimpleScarf
from compas_timber.fabrication.btlx import OrientationType


@pytest.fixture
def standard_beam():
    return Beam(frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), width=100, height=200, length=1000)


def test_simple_scarf_from_beam_and_side(standard_beam):
    """Test the alternate constructor generation."""
    feature = SimpleScarf.from_beam_and_side(
        beam=standard_beam, side="start", length=300, depth_ref_side=50, depth_opp_side=50, num_drill_hole=2, drill_hole_diam=20, ref_side_index=0
    )

    assert feature.orientation == OrientationType.START
    assert feature.start_x == 0.0
    assert feature.length == 300
    assert feature.depth_ref_side == 50
    assert feature.num_drill_hole == 2
    assert feature.drill_hole_diam_1 == 20
    assert feature.drill_hole_diam_2 == 20


def test_simple_scarf_end_orientation(standard_beam):
    """Test if the X calculation works correctly for the end side."""
    feature = SimpleScarf.from_beam_and_side(
        beam=standard_beam,
        side="end",
        length=300,
        depth_ref_side=50,
        depth_opp_side=50,
    )

    assert feature.orientation == OrientationType.END
    # StartX should be beam length + length/2 for END cuts based on the method
    assert feature.start_x == 1000.0 + (300 / 2)


def test_simple_scarf_validation():
    """Test the setter validation constraints."""
    feature = SimpleScarf()

    with pytest.raises(ValueError):
        feature.length = -50.0  # Must be positive

    with pytest.raises(ValueError):
        feature.num_drill_hole = 3  # Must be between 0 and 2

    with pytest.raises(ValueError):
        feature.orientation = "middle"  # Must be an OrientationType


def test_simple_scarf_scale(standard_beam):
    """Test that geometrical parameters are properly scaled."""
    feature = SimpleScarf(length=200, depth_ref_side=50, depth_opp_side=50, drill_hole_diam_1=20, drill_hole_diam_2=20)
    feature.scale(2.0)

    assert feature.length == 400
    assert feature.depth_ref_side == 100
    assert feature.depth_opp_side == 100
    assert feature.drill_hole_diam_1 == 40
    assert feature.drill_hole_diam_2 == 40


# ---------------------------------------------------------------------------
# Property setter validation
# ---------------------------------------------------------------------------

def test_start_x_validation():
    """start_x must be within [-100000, 100000]."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.start_x = -200000.0
    with pytest.raises(ValueError):
        f.start_x = 200000.0


def test_length_validation():
    """length must be > 0 and <= 50000."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.length = 0.0
    with pytest.raises(ValueError):
        f.length = 60000.0


def test_depth_ref_side_validation():
    """depth_ref_side must be in [0, 50000]."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.depth_ref_side = -1.0
    with pytest.raises(ValueError):
        f.depth_ref_side = 60000.0


def test_depth_opp_side_validation():
    """depth_opp_side must be in [0, 50000]."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.depth_opp_side = -1.0
    with pytest.raises(ValueError):
        f.depth_opp_side = 60000.0


def test_drill_hole_diam_1_validation():
    """drill_hole_diam_1 must be > 0 and <= 1000."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.drill_hole_diam_1 = 0.0
    with pytest.raises(ValueError):
        f.drill_hole_diam_1 = 2000.0


def test_drill_hole_diam_2_validation():
    """drill_hole_diam_2 must be > 0 and <= 1000."""
    f = SimpleScarf()
    with pytest.raises(ValueError):
        f.drill_hole_diam_2 = 0.0
    with pytest.raises(ValueError):
        f.drill_hole_diam_2 = 2000.0


# ---------------------------------------------------------------------------
# num_drill_hole_str
# ---------------------------------------------------------------------------

def test_num_drill_hole_str_returns_string():
    """num_drill_hole_str must return a plain integer string, not a float string."""
    for n in [0, 1, 2]:
        f = SimpleScarf(num_drill_hole=n)
        assert f.num_drill_hole_str == str(n)
        assert isinstance(f.num_drill_hole_str, str)
        assert "." not in f.num_drill_hole_str


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

def test_simple_scarf_data_roundtrip():
    """All fields must survive a json_dumps / json_loads round-trip."""
    f = SimpleScarf(
        orientation=OrientationType.START,
        start_x=0.0,
        length=300.0,
        depth_ref_side=50.0,
        depth_opp_side=40.0,
        num_drill_hole=1,
        drill_hole_diam_1=20.0,
        drill_hole_diam_2=25.0,
    )
    copy = json_loads(json_dumps(f))
    assert copy.orientation == f.orientation
    assert copy.start_x == f.start_x
    assert copy.length == f.length
    assert copy.depth_ref_side == f.depth_ref_side
    assert copy.depth_opp_side == f.depth_opp_side
    assert copy.num_drill_hole == f.num_drill_hole
    assert copy.drill_hole_diam_1 == f.drill_hole_diam_1
    assert copy.drill_hole_diam_2 == f.drill_hole_diam_2


# ---------------------------------------------------------------------------
# Alternative constructors
# ---------------------------------------------------------------------------

def test_define_orientation_invalid_side():
    """_define_orientation must raise for any side other than 'start' or 'end'."""
    with pytest.raises(ValueError):
        SimpleScarf._define_orientation("middle")


def test_from_beam_and_side_invalid_num_drill_hole(standard_beam):
    """from_beam_and_side must raise when num_drill_hole is out of [0, 1, 2]."""
    with pytest.raises(ValueError):
        SimpleScarf.from_beam_and_side(
            beam=standard_beam,
            side="start",
            length=300,
            depth_ref_side=50,
            depth_opp_side=50,
            num_drill_hole=5,
        )


def test_calculate_start_x_start(standard_beam):
    """_calculate_start_x returns 0.0 for START orientation."""
    assert SimpleScarf._calculate_start_x(standard_beam, OrientationType.START, 300) == 0.0


# ---------------------------------------------------------------------------
# volume_from_params_and_beam
# ---------------------------------------------------------------------------

def test_volume_from_params_and_beam_start(standard_beam):
    """Volume for START orientation must be a Polyhedron with 12 vertices and 10 faces."""
    feature = SimpleScarf(orientation=OrientationType.START, start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    vol = feature.volume_from_params_and_beam(standard_beam)
    assert isinstance(vol, Polyhedron)
    assert len(vol.vertices) == 12
    assert len(vol.faces) == 10


def test_volume_from_params_and_beam_end(standard_beam):
    """Volume for END orientation must also be a Polyhedron with reversed face winding."""
    feature = SimpleScarf(orientation=OrientationType.END, start_x=1150.0, length=300, depth_ref_side=50, depth_opp_side=50)
    vol = feature.volume_from_params_and_beam(standard_beam)
    assert isinstance(vol, Polyhedron)
    assert len(vol.vertices) == 12
    assert len(vol.faces) == 10
    # Verify winding is reversed vs START by comparing face[0] vertex order
    start_feature = SimpleScarf(orientation=OrientationType.START, start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    start_vol = start_feature.volume_from_params_and_beam(standard_beam)
    assert vol.faces[0] != start_vol.faces[0]


# ---------------------------------------------------------------------------
# drill_hole_volumes_from_params_and_beam
# ---------------------------------------------------------------------------

def test_drill_hole_volumes_zero(standard_beam):
    """Returns an empty list when num_drill_hole is 0."""
    f = SimpleScarf.from_beam_and_side(standard_beam, "start", 300, 50, 50, num_drill_hole=0)
    assert f.drill_hole_volumes_from_params_and_beam(standard_beam) == []


def test_drill_hole_volumes_one_start(standard_beam):
    """Returns one Cylinder positioned at the beam start."""
    f = SimpleScarf.from_beam_and_side(standard_beam, "start", 300, 50, 50, num_drill_hole=1, drill_hole_diam=30)
    vols = f.drill_hole_volumes_from_params_and_beam(standard_beam)
    assert len(vols) == 1
    assert isinstance(vols[0], Cylinder)


def test_drill_hole_volumes_one_end(standard_beam):
    """Returns one Cylinder positioned at the beam end."""
    f = SimpleScarf.from_beam_and_side(standard_beam, "end", 300, 50, 50, num_drill_hole=1, drill_hole_diam=30)
    vols = f.drill_hole_volumes_from_params_and_beam(standard_beam)
    assert len(vols) == 1
    assert isinstance(vols[0], Cylinder)


def test_drill_hole_volumes_two_start(standard_beam):
    """Returns two Cylinders offset along the beam for START orientation."""
    f = SimpleScarf.from_beam_and_side(standard_beam, "start", 300, 50, 50, num_drill_hole=2, drill_hole_diam=20)
    vols = f.drill_hole_volumes_from_params_and_beam(standard_beam)
    assert len(vols) == 2
    assert all(isinstance(v, Cylinder) for v in vols)


def test_drill_hole_volumes_two_end(standard_beam):
    """Returns two Cylinders offset along the beam for END orientation."""
    f = SimpleScarf.from_beam_and_side(standard_beam, "end", 300, 50, 50, num_drill_hole=2, drill_hole_diam=20)
    vols = f.drill_hole_volumes_from_params_and_beam(standard_beam)
    assert len(vols) == 2
    assert all(isinstance(v, Cylinder) for v in vols)


# ---------------------------------------------------------------------------
# scale
# ---------------------------------------------------------------------------

def test_scale_includes_start_x():
    """scale() must also scale start_x."""
    f = SimpleScarf(start_x=100.0, length=200, depth_ref_side=50, depth_opp_side=50, drill_hole_diam_1=20, drill_hole_diam_2=20)
    f.scale(2.0)
    assert f.start_x == 200.0


# ---------------------------------------------------------------------------
# apply() — all branches via mocks
# ---------------------------------------------------------------------------

def test_apply_raises_on_brep_conversion_error():
    """apply() must raise FeatureApplicationError when Brep.from_mesh fails."""
    feature = SimpleScarf(start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    mock_beam = MagicMock()
    mock_geometry = MagicMock()

    with patch.object(feature, "volume_from_params_and_beam", return_value=MagicMock()):
        with patch.object(feature, "drill_hole_volumes_from_params_and_beam", return_value=[]):
            with patch("compas_timber.fabrication.simple_scarf.Brep.from_mesh", side_effect=Exception("conversion failed")):
                with pytest.raises(FeatureApplicationError):
                    feature.apply(mock_geometry, mock_beam)


def test_apply_raises_on_boolean_difference_index_error():
    """apply() must raise FeatureApplicationError when boolean difference raises IndexError."""
    feature = SimpleScarf(start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    mock_beam = MagicMock()
    mock_geometry = MagicMock()

    with patch.object(feature, "volume_from_params_and_beam", return_value=MagicMock()):
        with patch.object(feature, "drill_hole_volumes_from_params_and_beam", return_value=[]):
            with patch("compas_timber.fabrication.simple_scarf.Brep.from_mesh", return_value=MagicMock()):
                with patch("compas_timber.fabrication.simple_scarf.Brep.from_boolean_difference", side_effect=IndexError()):
                    with pytest.raises(FeatureApplicationError):
                        feature.apply(mock_geometry, mock_beam)


def test_apply_raises_when_no_result_contains_midpoint():
    """apply() must raise FeatureApplicationError when no result Brep contains the midpoint."""
    feature = SimpleScarf(start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    mock_beam = MagicMock()
    mock_geometry = MagicMock()
    non_matching = MagicMock()
    non_matching.contains.return_value = False

    with patch.object(feature, "volume_from_params_and_beam", return_value=MagicMock()):
        with patch.object(feature, "drill_hole_volumes_from_params_and_beam", return_value=[]):
            with patch("compas_timber.fabrication.simple_scarf.Brep.from_mesh", return_value=MagicMock()):
                with patch("compas_timber.fabrication.simple_scarf.Brep.from_boolean_difference", return_value=[non_matching]):
                    with pytest.raises(FeatureApplicationError):
                        feature.apply(mock_geometry, mock_beam)


def test_apply_returns_matching_brep():
    """apply() must return the first result Brep whose contains() returns True."""
    feature = SimpleScarf(start_x=0.0, length=300, depth_ref_side=50, depth_opp_side=50)
    mock_beam = MagicMock()
    mock_geometry = MagicMock()
    matching = MagicMock()
    matching.contains.return_value = True

    with patch.object(feature, "volume_from_params_and_beam", return_value=MagicMock()):
        with patch.object(feature, "drill_hole_volumes_from_params_and_beam", return_value=[]):
            with patch("compas_timber.fabrication.simple_scarf.Brep.from_mesh", return_value=MagicMock()):
                with patch("compas_timber.fabrication.simple_scarf.Brep.from_boolean_difference", return_value=[matching]):
                    result = feature.apply(mock_geometry, mock_beam)
    assert result is matching
