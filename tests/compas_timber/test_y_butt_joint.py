import os

from compas.data import json_load
from compas.geometry import Vector
from compas.data import json_dumps
from compas.data import json_loads

from compas_timber.connections import YButtJoint
from compas_timber.elements import Beam
from compas_timber.fabrication.double_cut import DoubleCut
from compas_timber.fabrication.jack_cut import JackRafterCut
from compas_timber.fabrication.lap import Lap
from compas_timber.model import TimberModel


def test_create():
    path = os.path.abspath(r"data/y_joint_lines.json")
    lines = json_load(path)
    beams = [Beam.from_centerline(b, z_vector=Vector(0, 0, 1), width=60.0, height=120.0) for b in lines]
    model = TimberModel()
    for b in beams:
        model.add_element(b)
    instance = YButtJoint.create(model, *beams, mill_depth=10.0)
    model.process_joinery()
    model_copy = json_loads(json_dumps(model))

    assert len(instance.elements) == 3
    assert isinstance(instance, YButtJoint)
    assert instance.main_beam == beams[0]
    assert instance.cross_beams == tuple(beams[1:])
    assert instance.mill_depth == 10.0
    assert len(instance.main_beam.features) == 1
    assert isinstance(instance.main_beam.features[0], DoubleCut)
    assert len(instance.cross_beams[0].features) == 2
    assert set([f.__class__ for f in instance.cross_beams[0].features]) == set([JackRafterCut, Lap])
    assert len(list(model_copy.elements())) == 3
    assert set([b.guid for b in model.beams]) == set([b.guid for b in model_copy.beams])
