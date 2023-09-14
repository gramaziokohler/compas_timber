import os
from copy import deepcopy

import compas
import pytest
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector

from compas_timber.assembly import TimberAssembly
from compas_timber.connections import TButtJoint
from compas_timber.connections import find_neighboring_beams
from compas_timber.parts import Beam

geometry_type = "mesh"


@pytest.fixture
def example_beams():
    path = os.path.abspath(r"data/lines.json")
    centerlines = json_load(path)
    w = 0.12
    h = 0.06
    beams = []
    for index, line in enumerate(centerlines):
        b = Beam.from_centerline(line, w, h, geometry_type="mesh")
        b.key = index
        beams.append(b)
    return beams


def test_create(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    # try create with beams
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1, geometry_type="mesh")
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1, geometry_type="mesh")
    A.add_beam(B1)
    A.add_beam(B2)
    J = TButtJoint.create(A, B1, B2)

    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.joints[0] == J


def test_joint_override_protection(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1, geometry_type="mesh")
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1, geometry_type="mesh")
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1, geometry_type="mesh")
    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    J = TButtJoint.create(A, B1, B2)

    assert A.are_parts_joined([B1, B2])
    assert A.are_parts_joined([B1, B3]) is False

    A.remove_joint(J)
    assert A.are_parts_joined([B1, B2]) is False


def test_deepcopy(mocker):
    # TODO: not sure this make sense at all?
    # Normally you wouldn't deepcopy individual joints (duplicate protection in assembly),
    # but maybe it's needed for deepcopy of assembly?
    mocker.patch("compas_timber.parts.Beam.update_beam_geometry")
    mocker.patch("compas_timber.connections.Joint.add_features")
    A = TimberAssembly()
    B1 = Beam.from_endpoints(Point(0, 0, 0), Point(2, 0, 0), 0.1, 0.2, z_vector=Vector(0, 0, 1), geometry_type="mesh")
    B2 = Beam.from_endpoints(Point(1, 0, 0), Point(1, 1, 0), 0.1, 0.2, z_vector=Vector(0, 0, 1), geometry_type="mesh")
    A.add_beam(B1)
    A.add_beam(B2)
    J = TButtJoint.create(A, B1, B2)
    J_copy = deepcopy(J)

    assert J_copy is not J


if not compas.IPY:

    def test_find_neighbors(example_beams):
        expected_result = [
            set([0, 1]),
            set([0, 3]),
            set([1, 2]),
            set([1, 4]),
            set([1, 5]),
            set([2, 3]),
            set([2, 6]),
            set([3, 4]),
            set([3, 5]),
            set([5, 6]),
        ]
        result = find_neighboring_beams(example_beams)
        # beam objects => sets of keys for easy comparison
        key_sets = []
        for pair in result:
            pair = tuple(pair)
            key_sets.append({pair[0].key, pair[1].key})

        assert len(expected_result) == len(result)
        for pair in key_sets:
            assert pair in expected_result
