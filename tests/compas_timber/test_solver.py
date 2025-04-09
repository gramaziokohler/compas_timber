import pytest

from compas.geometry import Point
from compas.geometry import Line

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import JointTopology
from compas_timber.elements import Beam


@pytest.fixture
def beams_L_touching():
    width, height = 10, 20
    line_a = Line(Point(x=0.8918918918918735, y=417.7027027027027, z=0.0), Point(x=133.48648648648646, y=414.1351351351351, z=0.0))
    line_b = Line(Point(x=133.48648648648646, y=414.1351351351351, z=0.0), Point(x=128.72972972972974, y=325.5405405405405, z=0.0))

    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_T_touching():
    width, height = 10, 20
    line_a = Line(Point(x=5.648648648648646, y=241.70270270270268, z=0.0), Point(x=122.78378378378376, y=238.13513513513513, z=0.0))
    line_b = Line(Point(x=105.83783783783781, y=186.40540540540542, z=0.0), Point(x=139.72972972972974, y=289.8648648648649, z=0.0))

    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_X_touching():
    width, height = 10, 20
    line_a = Line(Point(x=15.008008008007948, y=142.83116449783108, z=0.0), Point(x=211.73807140473815, y=39.32766099432757, z=0.0))
    line_b = Line(Point(x=187.5138471805139, y=182.4708041374708, z=0.0), Point(x=43.63663663663664, y=23.912245578912177, z=0.0))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_I_touching():
    width, height = 10, 20
    line_a = Line(Point(x=200.0, y=600.0, z=49.99999999999999), Point(x=400.0, y=600.0, z=49.99999999999999))
    line_b = Line(Point(x=0.0, y=600.0, z=49.99999999999999), Point(x=200.0, y=600.0, z=49.99999999999999))

    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_T_tol_L():
    # T turned to L with the right tolerance setting
    width, height = 10, 20
    line_a = Line(Point(x=342.23323323323336, y=417.7027027027027, z=0.0), Point(x=474.82782782782795, y=414.1351351351351, z=0.0))
    line_b = Line(Point(x=471.15563168543247, y=414.233938618787, z=0.0), Point(x=466.39841844451814, y=325.5405405405405, z=0.0))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_L_tol():
    # not touching but within tolerance will be L
    width, height = 10, 20
    line_a = Line(Point(x=0.8918918918918735, y=417.7027027027027, z=0.0), Point(x=133.48648648648646, y=414.1351351351351, z=0.0))
    line_b = Line(Point(x=136.36354033305062, y=414.1351351351351, z=0.0), Point(x=131.6067835762939, y=325.5405405405405, z=0.0))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_T_tol():
    width, height = 10, 20
    line_a = Line(Point(x=447.1791791791793, y=186.40540540540542, z=0.0), Point(x=481.07107107107123, y=289.8648648648649, z=0.0))
    line_b = Line(Point(x=346.98998998999014, y=241.70270270270268, z=0.0), Point(x=462.25139886799747, y=238.13513513513513, z=0.0))

    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_X_tol():
    width, height = 10, 20
    line_a = Line(Point(x=356.34934934934944, y=142.83116449783108, z=0.0), Point(x=553.0794127460797, y=39.32766099432757, z=0.0))
    line_b = Line(Point(x=528.8551885218553, y=182.4708041374708, z=0.6329114501187825), Point(x=384.9779779779781, y=23.912245578912177, z=0.6329114501187825))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_I_tol():
    width, height = 10, 20
    line_a = Line(Point(x=0.0, y=600.0, z=49.99999999999999), Point(x=200.0, y=600.0, z=49.99999999999999))
    line_b = Line(Point(x=206.807796286557, y=600.0, z=49.99999999999999), Point(x=406.807796286557, y=600.0, z=49.99999999999999))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


@pytest.fixture
def beams_I_overlapping():
    width, height = 10, 20
    line_a = Line(Point(x=0.0, y=600.0, z=49.99999999999999), Point(x=200.0, y=600.0, z=49.99999999999999))
    line_b = Line(Point(x=197.60983696719245, y=600.0, z=49.99999999999999), Point(x=397.60983696719245, y=600.0, z=49.99999999999999))
    return (Beam.from_centerline(line_a, width, height), Beam.from_centerline(line_b, width, height))


def test_solver_L_touching(beams_L_touching):
    beam_a, beam_b = beams_L_touching
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_L
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_T_touching(beams_T_touching):
    beam_a, beam_b = beams_T_touching
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_T
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_X_touching(beams_X_touching):
    beam_a, beam_b = beams_X_touching
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_X
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_I_touching(beams_I_touching):
    beam_a, beam_b = beams_I_touching
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_I
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_T_tol_L(beams_T_tol_L):
    beam_a, beam_b = beams_T_tol_L
    tol = 3.70
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=tol)

    assert topology == JointTopology.TOPO_L
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_L_tol(beams_L_tol):
    beam_a, beam_b = beams_L_tol
    tol = 2.90
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=tol)

    assert topology == JointTopology.TOPO_L
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_T_tol(beams_T_tol):
    beam_a, beam_b = beams_T_tol
    tol = 1.90
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=tol)

    assert topology == JointTopology.TOPO_T
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_X_tol(beams_X_tol):
    beam_a, beam_b = beams_X_tol
    tol = 0.70
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=tol)

    assert topology == JointTopology.TOPO_X
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_I_tol_toofar(beams_I_tol):
    beam_a, beam_b = beams_I_tol
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_UNKNOWN


def test_solver_L_tol_toofar(beams_L_tol):
    beam_a, beam_b = beams_L_tol
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_UNKNOWN


def test_solver_T_tol_toofar(beams_T_tol):
    beam_a, beam_b = beams_T_tol
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_UNKNOWN


def test_solver_X_tol_toofar(beams_X_tol):
    beam_a, beam_b = beams_X_tol
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_UNKNOWN


def test_solver_I_tol(beams_I_tol):
    beam_a, beam_b = beams_I_tol
    tol = 6.85
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b, max_distance=tol)

    assert topology == JointTopology.TOPO_I
    assert beam_a == beam_a
    assert beam_b == beam_b


def test_solver_I_overlapping(beams_I_overlapping):
    beam_a, beam_b = beams_I_overlapping
    solver = ConnectionSolver()
    topology, beam_a, beam_b = solver.find_topology(beam_a, beam_b)

    assert topology == JointTopology.TOPO_UNKNOWN
    assert beam_a == beam_a
    assert beam_b == beam_b
