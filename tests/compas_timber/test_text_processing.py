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
