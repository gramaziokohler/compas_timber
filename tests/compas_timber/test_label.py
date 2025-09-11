
from compas.geometry import Line
from compas.geometry import Point

from compas_timber.elements import Beam
from compas_timber.fabrication import JackRafterCut
from compas_timber.model.model import TimberModel
from compas_timber.planning import Label


def test_label_creation():
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 60, 120)
    label = Label(beam)
    assert label.text == "Beam_None_"  # default text

    beam.attributes["category"] = "test_category"
    assert label.text == "Beam_None_test_category"  # default text with category

    model = TimberModel()
    model.add_element(beam)
    assert label.text == "Beam_0_test_category"  # default text with category and key

    label = Label(beam, "user_text")
    assert label.text == "user_text"  # user defined text


def test_label_engrave_on_beam():
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 60, 120)
    label = Label(beam, "hello_user_text_processing")
    text = label.engrave_on_beam(beam)
    assert text.start_x == 500.0
    assert text.start_y == 30.0
    assert text.text_height == 30.0
    assert text.text == "hello_user_text_processing"

    beam.add_features([JackRafterCut(start_x=100.0), JackRafterCut(orientation="end", start_x=800.0)])
    text = label.engrave_on_beam(beam)
    assert text.start_x == 450.0


def test_label_from_element():
    beam = Beam.from_centerline(Line(Point(0, 0, 0), Point(1000, 0, 0)), 60, 120)
    label = Label.from_element(beam)
    assert label.text == "Beam_None_"

    label = Label.from_element(beam, base_string="base_string")
    assert label.text == "base_string"

    label = Label.from_element(beam, attributes=["height", "width"])
    assert label.text == "_120_60"

    label = Label.from_element(beam, attributes=["height", "width"], base_string="h0_w0", char_to_replace="0")
    assert label.text == "h120_w60"
