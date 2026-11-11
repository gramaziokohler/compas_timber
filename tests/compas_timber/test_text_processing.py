import os
import pytest

from compas.data import json_load
from compas.geometry import Point
from compas.geometry import Line

from compas_timber.elements import Beam
from compas_timber.fabrication import Text
from compas_timber.fabrication import AlignmentType


@pytest.fixture
def expected_curves():
    filepath = os.path.join(os.path.dirname(__file__), "fixtures", "expected_curves.json")
    return json_load(filepath)


def test_curves_for_text(expected_curves):
    centerline = Line(Point(x=5.978260869565261, y=23.913043478260885, z=1814.4912974468011), Point(x=7807.825167262445, y=2305.2803643503457, z=1814.4912974468011))
    width, height = 600, 800
    beam = Beam.from_centerline(centerline, width, height)

    text = Text("some text", text_height=200, ref_side_index=3)

    curves = text.create_text_curves_for_element(beam)

    assert curves == expected_curves
    assert text.text_height == 200

    # defaults
    assert text.alignment_vertical == AlignmentType.BOTTOM
    assert text.alignment_horizontal == AlignmentType.LEFT
    assert text.alignment_multiline == AlignmentType.LEFT
    assert text.start_x == 0.0
    assert text.start_y == 0.0
    assert text.angle == 0.0
    assert not text.stacked_marking
    assert text.text_height_auto


def test_character_dict_ships_with_the_package():
    # the font must live inside the package, or installed copies (not a git clone) cannot draw text
    import compas_timber.fabrication

    package = os.path.dirname(compas_timber.fabrication.__file__)
    assert os.path.isfile(os.path.join(package, "basic_characters.zip"))

    Text._CHARACTER_DICT = {}
    Text._load_character_dict()
    assert Text._CHARACTER_DICT


@pytest.fixture
def labelled_beam():
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 100, 160)
    text = Text(
        "12",
        start_x=500,
        start_y=50,  # the middle of the 100 mm wide reference side
        alignment_vertical=AlignmentType.CENTER,
        alignment_horizontal=AlignmentType.CENTER,
        text_height_auto=False,
        text_height=60,
        ref_side_index=0,
    )
    return beam, text


def test_letters_are_evenly_spaced(labelled_beam):
    beam, text = labelled_beam  # "12": the "1" has more room on its left than the "2"
    face = beam.ref_sides[0]

    curves = text.create_text_curves_for_element(beam)

    # split the curves back into letters, and measure each letter along the text
    ones = len(Text._CHARACTER_DICT["1"]["curves"])
    letters = [curves[:ones], curves[ones:]]
    spans = [[(p - face.point).dot(face.xaxis) for crv in letter for p in crv.points] for letter in letters]
    gap = min(spans[1]) - max(spans[0])

    assert abs(gap - Text.LETTER_SPACING * text.text_height) < 1e-6
    # and wide enough that the engraved strokes of neighbouring letters do not touch
    assert gap > Text.ENGRAVING * text.text_height


def test_text_grooves_follow_the_strokes(labelled_beam):
    beam, text = labelled_beam
    face = beam.ref_sides[0]
    size = text.text_height * Text.ENGRAVING

    curves = text.create_text_curves_for_element(beam)
    grooves = text.grooves_for_element(beam)

    # one groove per straight stroke, centered on the face, reaching `size` into it
    assert len(grooves) == sum(len(curve.points) - 1 for curve in curves)
    for groove in grooves:
        assert abs(face.normal.dot(groove.frame.point - face.point)) < 1e-6
        assert abs(groove.ysize - size) < 1e-6
        assert abs(groove.zsize - 2 * size) < 1e-6


def test_text_apply_subtracts_every_groove(labelled_beam, mocker):
    beam, text = labelled_beam
    mocker.patch("compas_timber.fabrication.text.Brep.from_box", side_effect=lambda box: box)
    difference = mocker.patch("compas_timber.fabrication.text.brep_difference_first", side_effect=lambda geometry, groove: geometry)

    text.apply(mocker.sentinel.geometry, beam)

    assert difference.call_count == len(text.grooves_for_element(beam))


def test_text_apply_skips_strokes_that_miss_the_element(labelled_beam, mocker):
    beam, text = labelled_beam
    mocker.patch("compas_timber.fabrication.text.Brep.from_box", side_effect=lambda box: box)
    # an empty difference (raised as IndexError) means the groove does not touch the element
    mocker.patch("compas_timber.fabrication.text.brep_difference_first", side_effect=IndexError)

    assert text.apply(mocker.sentinel.geometry, beam) is mocker.sentinel.geometry


def test_text_scaled():
    text = Text("some text", text_height=200, ref_side_index=3)

    scaled = text.scaled(2.0)

    assert scaled.text_height == text.text_height * 2.0
    assert scaled.start_x == text.start_x * 2.0
    assert scaled.start_y == text.start_y * 2.0
    assert scaled.angle == text.angle
    assert scaled.stacked_marking == text.stacked_marking
    assert scaled.text_height_auto == text.text_height_auto
    assert scaled.alignment_vertical == text.alignment_vertical
    assert scaled.alignment_horizontal == text.alignment_horizontal
    assert scaled.alignment_multiline == text.alignment_multiline
    assert scaled.ref_side_index == text.ref_side_index
    assert scaled.text == text.text
