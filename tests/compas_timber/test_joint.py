import os
from copy import deepcopy

import compas
import pytest
from compas.data import json_load
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Vector
from compas.geometry import Line

from compas_timber.assembly import TimberAssembly
from compas_timber.connections import TButtJoint
from compas_timber.connections import LButtJoint
from compas_timber.connections import XHalfLapJoint
from compas_timber.connections import THalfLapJoint
from compas_timber.connections import LHalfLapJoint
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
        b = Beam.from_centerline(line, w, h)
        b.key = index
        beams.append(b)
    return beams


@pytest.fixture
def l_topo_beams():
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(x=0.0, y=1.0, z=0.0), Point(x=1.0, y=1.0, z=0.0)),
        Line(Point(x=1.0, y=1.0, z=0.0), Point(x=1.0, y=0.0, z=0.0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


@pytest.fixture
def t_topo_beams():
    w = 0.2
    h = 0.2
    cross = Line(Point(x=1.0, y=2.0, z=0.0), Point(x=3.0, y=2.0, z=0.0))
    main = Line(Point(x=2.0, y=2.0, z=0.0), Point(x=2.0, y=1.0, z=0.0))
    return Beam.from_centerline(main, w, h), Beam.from_centerline(cross, w, h)


@pytest.fixture
def x_topo_beams():
    w = 0.2
    h = 0.2
    lines = [
        Line(Point(x=3.0, y=1.0, z=0.0), Point(x=4.0, y=0.0, z=0.0)),
        Line(Point(x=3.0, y=0.0, z=0.0), Point(x=4.0, y=1.0, z=0.0)),
    ]
    return [Beam.from_centerline(line, w, h) for line in lines]


def test_create(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    # try create with beams
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B1)
    A.add_beam(B2)
    J = TButtJoint.create(A, B1, B2)

    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.joints[0] == J


def test_joint_beam_keys(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    # try create with beams
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B1)
    A.add_beam(B2)
    J = TButtJoint.create(A, B1, B2)

    assert len(list(A.graph.nodes())) == 3
    assert len(list(A.graph.edges())) == 2
    assert A.joints[0] == J


def test_joint_override_protection(mocker):
    mocker.patch("compas_timber.connections.Joint.add_features")
    A = TimberAssembly()
    B1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
    B2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
    B3 = Beam(Frame.worldZX(), length=1.0, width=0.1, height=0.1)
    A.add_beam(B1)
    A.add_beam(B2)
    A.add_beam(B3)
    J = TButtJoint.create(A, B1, B2)

    assert A.are_parts_joined([B1, B2])
    assert A.are_parts_joined([B1, B3]) is False

    A.remove_joint(J)
    assert A.are_parts_joined([B1, B2]) is False


def test_deepcopy(mocker, t_topo_beams):
    mocker.patch("compas_timber.connections.Joint.add_features")
    assembly = TimberAssembly()
    beam_a, beam_b = t_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    t_butt = TButtJoint.create(assembly, beam_a, beam_b)
    assembly_copy = deepcopy(assembly)

    assert assembly_copy is not assembly
    assert assembly_copy.beams
    assert assembly_copy.joints

    t_butt_copy = assembly_copy.joints[0]
    assert t_butt_copy is not t_butt
    assert t_butt_copy.beams


def test_joint_create_t_butt(t_topo_beams):
    assembly = TimberAssembly()
    main_beam, cross_beam = t_topo_beams
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)
    joint = TButtJoint.create(assembly, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.beams


def test_joint_create_l_butt(l_topo_beams):
    assembly = TimberAssembly()
    beam_a, beam_b = l_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = LButtJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_x_half_lap(x_topo_beams):
    assembly = TimberAssembly()
    beam_a, beam_b = x_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = XHalfLapJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_t_lap(t_topo_beams):
    assembly = TimberAssembly()
    main_beam, cross_beam = t_topo_beams
    assembly.add_beam(main_beam)
    assembly.add_beam(cross_beam)
    joint = THalfLapJoint.create(assembly, main_beam, cross_beam)

    assert joint.main_beam is main_beam
    assert joint.cross_beam is cross_beam
    assert joint.beams


def test_joint_create_l_lap(l_topo_beams):
    assembly = TimberAssembly()
    beam_a, beam_b = l_topo_beams
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)
    joint = LHalfLapJoint.create(assembly, beam_a, beam_b)

    assert joint.main_beam is beam_a
    assert joint.cross_beam is beam_b
    assert joint.beams


def test_joint_create_kwargs_passthrough_lbutt():
    assembly = TimberAssembly()
    small = Beam.from_endpoints(Point(0, 0, 0), Point(0, 1, 0), 0.1, 0.1, z_vector=Vector(0, 0, 1))
    large = Beam.from_endpoints(Point(0, 0, 0), Point(1, 0, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    assembly.add_beam(small)
    assembly.add_beam(large)

    # main beam butts by default, first beam is by default main, they are swapped if necessary when small_beam_butts=True
    joint_a = LButtJoint.create(assembly, small, large, small_beam_butts=True)

    assert joint_a.main_beam is small
    assert joint_a.cross_beam is large

    assembly.remove_joint(joint_a)

    joint_b = LButtJoint.create(assembly, small, large, small_beam_butts=False)

    assert joint_b.main_beam is small
    assert joint_b.cross_beam is large

    assembly.remove_joint(joint_b)

    joint_c = LButtJoint.create(assembly, large, small, small_beam_butts=True)

    assert joint_c.main_beam is small
    assert joint_c.cross_beam is large

    assembly.remove_joint(joint_c)

    joint_d = LButtJoint.create(assembly, large, small, small_beam_butts=False)

    assert joint_d.main_beam is large
    assert joint_d.cross_beam is small


def test_joint_create_kwargs_passthrough_xhalflap():
    assembly = TimberAssembly()
    beam_a = Beam.from_endpoints(Point(0.5, 0, 0), Point(0.5, 1, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    beam_b = Beam.from_endpoints(Point(0, 0.5, 0), Point(1, 0.5, 0), 0.2, 0.2, z_vector=Vector(0, 0, 1))
    assembly.add_beam(beam_a)
    assembly.add_beam(beam_b)

    joint = XHalfLapJoint.create(assembly, beam_a, beam_b, cut_plane_bias=0.4)

    assert joint.cut_plane_bias == 0.4


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
