import copy

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.geometry import Vector
from compas.geometry import close

from compas_timber.elements import Beam
from compas_timber.fabrication import JackRafterCut


@pytest.fixture
def beam():
    frame = Frame(Point(1, 2, 3), Vector(1, 0, 0), Vector(0, 1, 0))
    return Beam(frame=frame, length=1000.0, width=100.0, height=60.0)


def create_empty():
    _ = Beam()


def test_beam_constructor():
    frame = Frame.worldXY()
    length = 1000.0
    width = 100.0
    height = 60.0

    beam = Beam(frame=frame, length=1000.0, width=100.0, height=60.0)

    assert beam.frame == frame
    assert beam.length == length
    assert beam.width == width
    assert beam.height == height
    assert beam._blank_extensions == {}
    assert beam.transformation == Transformation.from_frame(frame)


def test_create_from_endpoints():
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    B = Beam.from_endpoints(P1, P2, width=0.1, height=0.2)
    assert close(B.length, 1.0)  # the resulting beam length should be 1.0
    assert B.frame is not None


def test_create_from_centerline():
    P1 = Point(0, 0, 0)
    P2 = Point(1, 0, 0)
    line = Line(P1, P2)
    B = Beam.from_centerline(line, width=0.1, height=0.2)
    assert close(B.length, 1.0)  # the resulting beam length should be 1.0
    assert B.frame is not None


def test__eq__():
    F1 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))
    F2 = Frame(Point(0, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0))

    # checking if beams from identical input values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.17)
    B2 = Beam(F2, length=1.0, width=0.1, height=0.17)
    assert B1 is not B2

    # checking for numerical imprecision artefacts
    # algebraically it equals 0.17, but numerically 0.16999999999999993,  https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html
    h = 10.1 - 9.93
    B2 = Beam(F2, length=1.0, width=0.1, height=h)

    # checking if beams from equivalent imput values are identical
    B1 = Beam(F1, length=1.0, width=0.1, height=0.2)
    B2 = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), z_vector=Vector(0, 0, 1), width=0.1, height=0.2)


def test_deepcopy(beam):
    B1 = beam
    B2 = copy.deepcopy(B1)

    assert B2 is not B1
    assert B2.frame is not B1.frame
    assert B2.width is B1.width


def test_serialization_beam_with_joinery_processings(beam):
    cut = JackRafterCut()

    beam.add_feature(cut)

    deserialized = json_loads(json_dumps(beam))

    assert isinstance(deserialized, Beam)
    assert len(deserialized.features) == 0


def test_serialization_beam_with_nonjoinery_processings(beam):
    cut = JackRafterCut(is_joinery=False)

    beam.add_feature(cut)

    deserialized = json_loads(json_dumps(beam))

    assert isinstance(deserialized, Beam)
    assert len(deserialized.features) == 1


# ==========================================================================
# Blank Extension & Transformation Tests
# ==========================================================================


def test_beam_length_consistency_after_add_blank_extension(beam):
    """Test that length remains consistent after adding blank extensions."""
    length_before = beam.length
    blank_length_before = beam.blank_length
    beam.add_blank_extension(0.1, 0.2, joint_key=1)

    assert length_before == blank_length_before  # those should be the same without extensions
    assert beam.length == length_before  # this should not change after adding extensions
    assert beam.blank_length != blank_length_before  # this should change after adding extensions


def test_add_blank_extension_with_joint_key(beam):
    """Test adding extension with joint_key."""
    beam.add_blank_extension(0.1, 0.2, joint_key=1)

    assert beam._blank_extensions[1] == (0.1, 0.2)
    start, end = beam._resolve_blank_extensions()
    assert start == 0.1
    assert end == 0.2


def test_add_extension_with_joint_key_none(beam):
    """Test adding extension with joint_key=None."""
    beam.add_blank_extension(0.1, 0.2)

    assert beam._blank_extensions[None] == (0.1, 0.2)


def test_add_multiple_extensions_different_joint_keys(beam):
    """Test adding multiple extensions with different joint_keys."""
    beam.add_blank_extension(0.1, 0.2, joint_key=1)
    beam.add_blank_extension(0.15, 0.05, joint_key=2)

    assert beam._blank_extensions[1] == (0.1, 0.2)
    assert beam._blank_extensions[2] == (0.15, 0.05)
    start, end = beam._resolve_blank_extensions()
    assert start == 0.15  # max of 0.1 and 0.15
    assert end == 0.2  # max of 0.2 and 0.05


def test_remove_specific_extension_by_joint_key(beam):
    """Test removing specific extension by joint_key."""
    beam.add_blank_extension(0.1, 0.2, joint_key=1)
    beam.add_blank_extension(0.15, 0.05, joint_key=2)

    beam.remove_blank_extension(joint_key=1)

    assert 1 not in beam._blank_extensions
    assert beam._blank_extensions[2] == (0.15, 0.05)


def test_remove_all_extensions(beam):
    """Test removing all extensions with joint_key=None."""
    beam.add_blank_extension(0.1, 0.2, joint_key=1)
    beam.add_blank_extension(0.15, 0.05, joint_key=2)

    beam.remove_blank_extension()

    assert beam._blank_extensions == {}


def test_resolve_blank_extensions_no_extensions(beam):
    """Test _resolve_blank_extensions with no extensions."""
    start, end = beam._resolve_blank_extensions()

    assert start == 0.0
    assert end == 0.0


def test_transformation_with_start_extension(beam):
    """Test beam transformation includes negative translation along x-axis for start extension."""
    # Get transformation before extension
    transformation_before = beam.transformation

    # Add start extension
    beam.add_blank_extension(0.1, 0.0, joint_key=1)

    # Get transformation after extension
    transformation_after = beam.transformation

    # The difference should be a translation along negative x-axis
    expected_translation = Translation.from_vector(-beam.frame.xaxis * 0.1)

    assert transformation_before != transformation_after
    assert transformation_after == transformation_before * expected_translation


def test_transformation_with_end_extension_only(beam):
    """Test beam transformation doesn't change for end extension only."""
    # Get transformation before extension
    transformation_before = beam.transformation

    # Add end extension only
    beam.add_blank_extension(0.0, 0.2, joint_key=1)

    # Get transformation after extension
    transformation_after = beam.transformation

    # Should be the same (no start extension)
    assert transformation_before == transformation_after


def test_transformation_with_multiple_extensions(beam):
    """Test beam transformation uses max start value from multiple extensions."""
    # Get transformation before extensions
    transformation_before = beam.transformation

    # Add multiple extensions with different start values
    beam.add_blank_extension(0.1, 0.0, joint_key=1)
    beam.add_blank_extension(0.15, 0.0, joint_key=2)  # This has the max start
    beam.add_blank_extension(0.0, 5.0, joint_key=3)

    transformation_after = beam.transformation

    # The difference should be based on max start extension (0.15)
    expected_translation = Translation.from_vector(-beam.frame.xaxis * 0.15)

    assert transformation_after != transformation_before
    assert transformation_after == transformation_before * expected_translation


def test_transformation_when_removing_extensions(beam):
    """Test transformation updates automatically when extensions change."""
    # Get initial transformation
    transformation_before = beam.transformation

    # Add extension
    beam.add_blank_extension(0.1, 0.0, joint_key=1)
    transformation_with_extension = beam.transformation

    # Remove extension
    beam.remove_blank_extension(joint_key=1)
    transformation_without_extension = beam.transformation

    # Should be back to original
    assert transformation_without_extension == transformation_before
    assert transformation_with_extension != transformation_without_extension


def test_extension_to_plane(beam):
    """Test extension to a plane."""
    ref_frame_before_extension = beam.ref_frame.copy()

    plane = Plane(Point(0, 0, 0), Vector(-1.000, 0.000, 0.000))
    start, end = beam.extension_to_plane(plane)
    beam.add_blank_extension(start, end, joint_key=0)
    extension_start, extension_end = beam._blank_extensions.get(0)

    assert extension_start == beam.frame.xaxis.dot(Vector.from_start_end(plane.point, beam.frame.point))
    assert extension_end == 0.0
    assert beam.blank_length == beam.length + extension_start + extension_end
    assert ref_frame_before_extension.point != beam.ref_frame.point  # ref_frame should change after extension


def test_extension_to_frame(beam):
    """Test extension to a frame."""
    ref_frame_before_extension = beam.ref_frame.copy()

    plane = Frame.from_plane(Plane(Point(0, 0, 0), Vector(-1.000, 0.000, 0.000)))
    start, end = beam.extension_to_plane(plane)
    beam.add_blank_extension(start, end, joint_key=0)
    extension_start, extension_end = beam._blank_extensions.get(0)

    assert extension_start == beam.frame.xaxis.dot(Vector.from_start_end(plane.point, beam.frame.point))
    assert extension_end == 0.0
    assert beam.blank_length == beam.length + extension_start + extension_end
    assert ref_frame_before_extension.point != beam.ref_frame.point  # ref_frame should change after extension


def test_frame_from_transformation_sync():
    """Test that setting transformation updates the frame accordingly."""
    beam = Beam(frame=Frame.worldXY(), length=1000.0, width=100.0, height=60.0)

    # Create a transformation and set it
    new_transformation = Transformation.from_frame(Frame(Point(100, 200, 300), Vector(0, 1, 0), Vector(0, 0, 1)))
    beam.transformation = new_transformation

    # Frame should be updated to match the transformation
    expected_frame = Frame.from_transformation(new_transformation)
    assert beam.frame == expected_frame


def test_frame_after_transform(beam):
    """Test that frame updates correctly after setting transformation."""
    initial_frame = beam.frame.copy()
    initial_transformation = beam.transformation.copy()

    # Set a new transformation
    new_transformation = Translation.from_vector(Vector(10, 20, 30))
    beam.transform(new_transformation)

    expected_frame = initial_frame.transformed(new_transformation)
    expected_transformation = initial_transformation * new_transformation

    assert beam.frame == expected_frame
    assert beam.transformation == expected_transformation


def test_frame_unchanged_by_blank_extensions(beam):
    """Test that beam.frame is NOT affected by blank extensions (core beam definition preserved)."""
    original_frame = beam.frame.copy()
    original_transformation = beam.transformation.copy()

    # Add blank extensions (simulating joining operations)
    beam.add_blank_extension(50.0, 30.0, joint_key=1)
    beam.add_blank_extension(25.0, 15.0, joint_key=2)

    start, _ = beam._resolve_blank_extensions()

    # Transformation changes due to extensions
    assert beam.transformation != original_transformation
    assert beam.transformation == original_transformation * Translation.from_vector(-beam.frame.xaxis * start)

    # Frame should remain completely unchanged
    assert beam.frame == original_frame


# ==========================================================================
# Geometry Computation Tests
# ==========================================================================


def test_reset_computed_when_adding_features(mocker):
    mocker.patch("compas_timber.elements.Beam.compute_elementgeometry", return_value=mocker.Mock())
    b = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.2)

    b.geometry

    assert b._geometry is not None
    b.add_features(mocker.Mock())

    assert b._geometry is None


def test_compute_geometry_without_features(beam, mocker):
    """Test geometry hasn't applied features."""
    # Mock the geometry creation but not the feature application
    mocker.patch("compas_timber.elements.beam.Brep.from_box", return_value=mocker.Mock(spec=Brep))

    mock_feature = JackRafterCut(is_joinery=False)
    mock_feature.apply = mocker.Mock(wraps=mock_feature.apply)

    beam.add_feature(mock_feature)

    beam.compute_elementgeometry(include_features=False)

    # Check that apply was not called for this feature
    mock_feature.apply.assert_not_called()


def test_geometry_with_features(beam, mocker):
    """Test geometry applies features when requested."""
    # Mock the geometry creation but not the feature application
    mocker.patch("compas_timber.elements.beam.Brep.from_box", return_value=mocker.Mock(spec=Brep))

    mock_feature = JackRafterCut(is_joinery=False)
    mock_feature.apply = mocker.Mock(wraps=mock_feature.apply)

    beam.add_feature(mock_feature)

    beam.compute_elementgeometry(include_features=True)

    # Check that apply was called for this feature
    mock_feature.apply.assert_called()
