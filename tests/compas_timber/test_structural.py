import pytest
import pytest_mock

from compas.geometry import Frame
from compas_timber.elements import Beam
from compas_timber.structural import BeamStructuralElementSolver
from compas_timber.connections import Joint
from compas_timber.model import TimberModel


def test_create_segments_from_beam_and_its_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)

    j1_location = beam.centerline.point_at(0)
    j2_location = beam.centerline.point_at(0.5)
    j3_location = beam.centerline.point_at(0.75)
    j4_location = beam.centerline.point_at(1)

    joints = [
        mocker.MagicMock(spec=Joint, location=j1_location),
        mocker.MagicMock(spec=Joint, location=j2_location),
        mocker.MagicMock(spec=Joint, location=j3_location),
        mocker.MagicMock(spec=Joint, location=j4_location),
    ]

    model: TimberModel = mocker.MagicMock(spec=TimberModel)
    model.get_interactions_for_element.return_value = joints

    solver = BeamStructuralElementSolver()
    segments = solver.add_structural_segments(beam, model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 3
    expected_lengths = [3000.0, 1500.0, 1500.0]

    for segment, expected_length in zip(segments, expected_lengths):
        actual_length = segment.segment.length
        assert actual_length == pytest.approx(expected_length)


def test_create_segments_no_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)
    model = mocker.MagicMock()
    model.get_interactions_for_element.return_value = []

    solver = BeamStructuralElementSolver()
    segments = solver.add_structural_segments(beam, model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 1
    assert segments[0].segment.length == pytest.approx(6000.0)


def test_create_segments_joints_at_ends_only(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=6000, width=200, height=400)

    j_start_loc = beam.centerline.start
    j_end_loc = beam.centerline.end

    joints = [
        mocker.MagicMock(spec=Joint, location=j_start_loc),
        mocker.MagicMock(spec=Joint, location=j_end_loc),
    ]
    model = mocker.MagicMock()
    model.get_interactions_for_element.return_value = joints

    solver = BeamStructuralElementSolver()
    segments = solver.add_structural_segments(beam, model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 1
    assert segments[0].segment.length == pytest.approx(6000.0)


def test_create_segments_unsorted_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    # joints at 0.8, 0.2, 0.5
    j1 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.8))
    j2 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.2))
    j3 = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))

    model = mocker.MagicMock()
    model.get_interactions_for_element.return_value = [j1, j2, j3]

    solver = BeamStructuralElementSolver()
    segments = solver.add_structural_segments(beam, model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 4
    # Expected: 0.0 -> 0.2 (200), 0.2 -> 0.5 (300), 0.5 -> 0.8 (300), 0.8 -> 1.0 (200)
    expected_lengths = [200.0, 300.0, 300.0, 200.0]
    for seg, exp in zip(segments, expected_lengths):
        assert seg.segment.length == pytest.approx(exp)


def test_create_segments_project_joints(mocker: pytest_mock.MockerFixture):
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    # joint near centerline, e.g. at z=50 (on surface)
    # centerline is on X axis (by default Beam frame)

    loc_on_center = beam.centerline.point_at(0.5)
    loc_off_center = loc_on_center + [0, 50, 0]  # Shifted

    joint = mocker.MagicMock(spec=Joint, location=loc_off_center)
    model = mocker.MagicMock()
    model.get_interactions_for_element.return_value = [joint]

    solver = BeamStructuralElementSolver()
    segments = solver.add_structural_segments(beam, model)

    model.add_beam_structural_segments.assert_called_once()

    assert len(segments) == 2
    assert segments[0].segment.length == pytest.approx(500.0)
    assert segments[1].segment.length == pytest.approx(500.0)


def test_get_beam_structural_segments(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam1 = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    beam2 = Beam(Frame.worldXY().translated([0, 100, 0]), length=2000, width=100, height=100)
    model.add_element(beam1)
    model.add_element(beam2)

    # Mock interactions to return empty list so we get 1 segment per beam
    mocker.patch.object(model, "get_interactions_for_element", return_value=[])

    solver = BeamStructuralElementSolver()
    solver.add_structural_segments(beam1, model)
    solver.add_structural_segments(beam2, model)

    segments1 = model.get_beam_structural_segments(beam1)
    segments2 = model.get_beam_structural_segments(beam2)

    assert len(segments1) == 1
    assert segments1[0].segment.length == pytest.approx(1000)

    assert len(segments2) == 1
    assert segments2[0].segment.length == pytest.approx(2000)

    # Verify no cross contamination
    assert segments1[0] not in segments2
    assert segments2[0] not in segments1


def test_create_structural_segments_on_model(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    # Mock interactions
    joint = mocker.MagicMock(spec=Joint, location=beam.centerline.point_at(0.5))
    mocker.patch.object(model, "get_interactions_for_element", return_value=[joint])
    mocker.patch.object(TimberModel, "joints", new_callable=mocker.PropertyMock).return_value = {joint}

    model.create_beam_structural_segments()

    segments = model.get_beam_structural_segments(beam)
    assert len(segments) == 2


def test_create_structural_segments_raises_no_joints(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    # joints property returns empty set by default

    with pytest.raises(ValueError, match="No joints in the model"):
        model.create_beam_structural_segments()


def test_create_structural_segments_raises_no_beams(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    joint = mocker.MagicMock(spec=Joint)
    mocker.patch.object(TimberModel, "joints", new_callable=mocker.PropertyMock).return_value = {joint}

    with pytest.raises(ValueError, match="No beams in the model"):
        model.create_beam_structural_segments()


def test_remove_beam_structural_segments(mocker: pytest_mock.MockerFixture):
    model = TimberModel()
    beam = Beam(Frame.worldXY(), length=1000, width=100, height=100)
    model.add_element(beam)

    # Mock interactions to return empty list so we get 1 segment per beam
    mocker.patch.object(model, "get_interactions_for_element", return_value=[])

    solver = BeamStructuralElementSolver()
    solver.add_structural_segments(beam, model)

    assert len(model.get_beam_structural_segments(beam)) == 1

    model.remove_beam_structural_segments(beam)

    assert len(model.get_beam_structural_segments(beam)) == 0
