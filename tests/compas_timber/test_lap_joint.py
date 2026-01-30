import pytest

from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Point
from compas.geometry import Line

from compas_timber.elements import Beam
from compas_timber.connections import LLapJoint
from compas_timber.connections import TLapJoint
from compas_timber.connections import XLapJoint
from compas_timber.connections import LFrenchRidgeLapJoint
from compas_timber.model import TimberModel


@pytest.fixture
def beam_a():
    line = Line(Point(x=4.29781540252867, y=35.42482180056156, z=0.0), Point(x=194.13139833231588, y=90.20267160119664, z=0.0))
    return Beam.from_centerline(line, width=10.0, height=20.0)


@pytest.fixture
def beam_b():
    line = Line(Point(x=4.29781540252867, y=35.42482180056156, z=0.0), Point(x=11.853380892271431, y=-121.35316211160092, z=0.0))
    return Beam.from_centerline(line, width=10.0, height=20.0)


def test_create_lap(beam_a, beam_b):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    joint = LLapJoint.create(model, beam_a, beam_b, flip_lap_side=True, cut_plane_bias=0.5)

    assert len(model.joints) == 1
    assert isinstance(joint, LLapJoint)


def test_create_lap_serialize(beam_a, beam_b):
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    joint = LLapJoint.create(model, beam_a, beam_b, flip_lap_side=True, cut_plane_bias=0.5)

    model = json_loads(json_dumps(model))

    assert len(model.joints) == 1
    assert isinstance(joint, LLapJoint)

    deserialized_joint = list(model.joints)[0]
    assert isinstance(deserialized_joint, LLapJoint)
    assert deserialized_joint.beam_a is not None
    assert deserialized_joint.beam_b is not None


def test_standard_lap_joint_cut_plane_bias_serialization(beam_a, beam_b):
    """Test that standard lap joints (LLapJoint) correctly serialize and deserialize cut_plane_bias."""
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    # Create joint with custom cut_plane_bias
    joint = LLapJoint.create(model, beam_a, beam_b, flip_lap_side=True, cut_plane_bias=0.3)

    # Verify the joint has the correct cut_plane_bias
    assert joint.cut_plane_bias == 0.3

    # Check that cut_plane_bias is included in serialization
    joint_data = joint.__data__
    assert "cut_plane_bias" in joint_data
    assert joint_data["cut_plane_bias"] == 0.3

    # Serialize and deserialize the model
    serialized = json_dumps(model)
    deserialized_model = json_loads(serialized)

    # Verify the deserialized joint maintains cut_plane_bias
    deserialized_joint = list(deserialized_model.joints)[0]
    assert isinstance(deserialized_joint, LLapJoint)
    assert deserialized_joint.cut_plane_bias == 0.3


def test_french_ridge_lap_joint_serialization_no_cut_plane_bias(beam_a, beam_b):
    """Test that French Ridge Lap joints do NOT serialize cut_plane_bias."""
    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    # Create French Ridge Lap joint
    joint = LFrenchRidgeLapJoint.create(model, beam_a, beam_b, flip_lap_side=True, drillhole_diam=12.0)

    # Verify joint properties
    assert joint.flip_lap_side is True
    assert joint.drillhole_diam == 12.0

    # Check that cut_plane_bias is NOT included in serialization
    joint_data = joint.__data__
    assert "cut_plane_bias" not in joint_data
    assert "drillhole_diam" in joint_data
    assert joint_data["drillhole_diam"] == 12.0
    assert joint_data["flip_lap_side"] is True

    # Serialize and deserialize the model - this should NOT fail
    serialized = json_dumps(model)
    deserialized_model = json_loads(serialized)

    # Verify the deserialized joint
    deserialized_joint = list(deserialized_model.joints)[0]
    assert isinstance(deserialized_joint, LFrenchRidgeLapJoint)
    assert deserialized_joint.flip_lap_side is True
    assert deserialized_joint.drillhole_diam == 12.0


def test_different_lap_joints_serialization_behavior():
    """Test that different lap joint types have different serialization behavior."""
    # Create beams for standard lap joint
    line1 = Line(Point(0, 0, 0), Point(100, 0, 0))
    line2 = Line(Point(0, 0, 0), Point(0, 100, 0))
    beam1 = Beam.from_centerline(line1, width=20.0, height=20.0)
    beam2 = Beam.from_centerline(line2, width=20.0, height=20.0)

    model = TimberModel()
    model.add_element(beam1)
    model.add_element(beam2)

    # Create standard lap joint with cut_plane_bias
    lap_joint = LLapJoint.create(model, beam1, beam2, cut_plane_bias=0.7)

    # Create French Ridge lap joint
    french_lap_joint = LFrenchRidgeLapJoint.create(model, beam1, beam2, drillhole_diam=15.0)

    # Check serialization differences
    lap_data = lap_joint.__data__
    french_data = french_lap_joint.__data__

    # Standard joint should have cut_plane_bias
    assert "cut_plane_bias" in lap_data
    assert lap_data["cut_plane_bias"] == 0.7
    assert "drillhole_diam" not in lap_data

    # French joint should have drillhole_diam but not cut_plane_bias
    assert "cut_plane_bias" not in french_data
    assert "drillhole_diam" in french_data
    assert french_data["drillhole_diam"] == 15.0

    # Both should have common lap joint properties
    for data in [lap_data, french_data]:
        assert "beam_a_guid" in data
        assert "beam_b_guid" in data
        assert "flip_lap_side" in data


def test_lap_joint_architecture_separation():
    """Test that the new architecture properly separates concerns."""
    line1 = Line(Point(0, 0, 0), Point(100, 0, 0))
    line2 = Line(Point(0, 0, 0), Point(0, 100, 0))
    beam1 = Beam.from_centerline(line1, width=20.0, height=20.0)
    beam2 = Beam.from_centerline(line2, width=20.0, height=20.0)

    model = TimberModel()
    model.add_element(beam1)
    model.add_element(beam2)

    # Create different types of joints
    llap = LLapJoint.create(model, beam1, beam2, cut_plane_bias=0.3)
    tlap = TLapJoint.create(model, beam1, beam2, cut_plane_bias=0.6)
    xlap = XLapJoint.create(model, beam1, beam2, cut_plane_bias=0.9)
    frl = LFrenchRidgeLapJoint.create(model, beam1, beam2, drillhole_diam=10.0)

    # Standard lap joints should have cut_plane_bias
    assert hasattr(llap, "cut_plane_bias")
    assert hasattr(tlap, "cut_plane_bias")
    assert hasattr(xlap, "cut_plane_bias")
    assert llap.cut_plane_bias == 0.3
    assert tlap.cut_plane_bias == 0.6
    assert xlap.cut_plane_bias == 0.9

    # French Ridge Lap should have drillhole_diam
    assert hasattr(frl, "drillhole_diam")
    assert frl.drillhole_diam == 10.0

    # All should have common lap properties
    for joint in [llap, tlap, frl]:
        assert hasattr(joint, "beam_a")
        assert hasattr(joint, "beam_b")
        assert hasattr(joint, "flip_lap_side")
        assert hasattr(joint, "beam_a_guid")
        assert hasattr(joint, "beam_b_guid")


def test_create_negative_volumes_with_cut_plane_bias(mocker):
    """Test that add_features() calls _create_negative_volumes() properly with the correct cut_plane_bias parameter."""
    # mock the fabrication classes to avoid creating actual geometry features
    mocker.patch("compas_timber.fabrication.LapProxy.from_volume_and_beam", return_value=mocker.Mock())

    line1 = Line(Point(0, 0, 0), Point(100, 0, 0))
    line2 = Line(Point(50, -50, 0), Point(50, 50, 0))

    beam1 = Beam.from_centerline(line1, width=20.0, height=20.0)
    beam2 = Beam.from_centerline(line2, width=20.0, height=20.0)

    model = TimberModel()
    model.add_elements([beam1, beam2])

    tlap = TLapJoint.create(model, beam1, beam2, cut_plane_bias=0.3)
    xlap = XLapJoint.create(model, beam1, beam2, cut_plane_bias=0.5)
    llap = LLapJoint.create(model, beam1, beam2, cut_plane_bias=0.7)

    for lap in [tlap, xlap, llap]:
        mock_negative_volumes = mocker.patch.object(lap, "_create_negative_volumes", return_value=(mocker.Mock(), mocker.Mock()))
        # Should internally call _create_negative_volumes with the cut_plane_bias
        lap.add_features()
        # Verify that _create_negative_volumes was called exactly once with the correct cut_plane_bias
        mock_negative_volumes.assert_called_once_with(lap.cut_plane_bias)


def test_create_x_lap_serialize():
    beam_a = Beam.from_centerline(Line(Point(0, 0, 0), Point(200, 200, 0)), width=10.0, height=20.0)
    beam_b = Beam.from_centerline(Line(Point(0, 200, 0), Point(200, 0, 0)), width=10.0, height=20.0)

    model = TimberModel()
    model.add_element(beam_a)
    model.add_element(beam_b)

    org_joint = XLapJoint.create(model, beam_a, beam_b, flip_lap_side=True, cut_plane_bias=0.3)

    assert org_joint.__data__["cut_plane_bias"] == 0.3

    model = json_loads(json_dumps(model))

    assert len(model.joints) == 1
    joint: XLapJoint = list(model.joints)[0]
    assert isinstance(joint, XLapJoint)
    assert joint.cut_plane_bias == org_joint.cut_plane_bias
