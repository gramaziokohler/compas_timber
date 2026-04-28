import pytest
from compas.geometry import Frame, Point, Vector
from compas_timber.elements import Beam
from compas_timber.fabrication import SimpleScarf
from compas_timber.fabrication.btlx import OrientationType


@pytest.fixture
def standard_beam():
    return Beam(
        frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)),
        width=100, height=200, length=1000
    )


def test_simple_scarf_from_beam_and_side(standard_beam):
    """Test the alternate constructor generation."""
    feature = SimpleScarf.from_beam_and_side(
        beam=standard_beam,
        side="start",
        length=300,
        depth_ref_side=50,
        depth_opp_side=50,
        num_drill_hole=2,
        drill_hole_diam=20,
        ref_side_index=0
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