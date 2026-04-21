import pytest
from compas.geometry import Frame, Point, Vector
from compas_timber.elements import Beam
from compas_timber.connections import ISimpleScarf
from compas_timber.fabrication import SimpleScarf
from compas_timber.errors import BeamJoiningError


@pytest.fixture
def main_beam():
    # Beam lying on the X-axis
    return Beam(
        frame=Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)),
        width=100, height=200, length=1000
    )

@pytest.fixture
def cross_beam():
    # Parallel beam starting at the end of the main beam
    return Beam(
        frame=Frame(Point(1000, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)),
        width=100, height=200, length=1000
    )

@pytest.fixture
def non_parallel_beam():
    # Beam that is perpendicular to the main beam
    return Beam(
        frame=Frame(Point(1000, 0, 0), Vector(0, 1, 0), Vector(-1, 0, 0)),
        width=100, height=200, length=1000
    )


def test_i_simple_scarf_create_and_defaults(main_beam, cross_beam):
    """Test creation and auto-calculation of unset attributes."""
    joint = ISimpleScarf(main_beam, cross_beam)
    
    assert isinstance(joint, ISimpleScarf)
    # Check that defaults were calculated properly based on beam height (200)
    assert joint.length == 200 * 3
    assert joint.depth_ref_side == 200 * 0.25
    assert joint.depth_opp_side == 200 * 0.25


def test_i_simple_scarf_compatibility(main_beam, cross_beam, non_parallel_beam):
    """Test the parallel element checking logic."""
    # Should pass for parallel beams
    assert ISimpleScarf.check_elements_compatibility([main_beam, cross_beam]) is True
    
    # Should fail for non-parallel beams
    assert ISimpleScarf.check_elements_compatibility([main_beam, non_parallel_beam]) is False

    # Should raise error if forced
    with pytest.raises(BeamJoiningError):
        ISimpleScarf.check_elements_compatibility([main_beam, non_parallel_beam], raise_error=True)


def test_i_simple_scarf_add_extensions(main_beam, cross_beam):
    """Test if extensions are properly registered in the beams."""
    joint = ISimpleScarf(main_beam, cross_beam, length=150)
    joint.add_extensions()
    
    # Both beams should have an extension registered by this joint's guid
    assert joint.guid in main_beam._blank_extensions
    assert joint.guid in cross_beam._blank_extensions


def test_i_simple_scarf_add_features(main_beam, cross_beam):
    """Test if the correct features are attached to the beams."""
    joint = ISimpleScarf(main_beam, cross_beam)
    joint.add_features()

    assert len(main_beam.features) == 1
    assert len(cross_beam.features) == 1
    
    main_feature = main_beam.features[0]
    cross_feature = cross_beam.features[0]

    assert isinstance(main_feature, SimpleScarf)
    assert isinstance(cross_feature, SimpleScarf)
    
    # Assert features receive the shared joint parameters correctly
    assert main_feature.length == joint.length
    assert cross_feature.length == joint.length