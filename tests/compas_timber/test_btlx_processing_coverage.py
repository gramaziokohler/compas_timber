"""Every processing of the BTLx 2.3.0 schema, through every serialization this package has."""

import json
import xml.etree.ElementTree as ET

import pytest
from compas.data import json_dumps
from compas.data import json_loads
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.tolerance import Tolerance
from compas_pb import pb_dump_bts
from compas_pb import pb_load_bts

from compas_timber import fabrication as fab
from compas_timber.btlx import BTLxReader
from compas_timber.elements import Beam
from compas_timber.model import TimberModel

SCHEMA_PROCESSINGS = """
BirdsMouth Chamfer Connector CrampContour DoubleCut Dovetail DovetailMortise DovetailTenon Drilling FreeContour FreeSurface FrenchRidgeLap GlueArea HipValleyRafterNotch House
HouseMortise InsulationArea JackRafterCut JapaneseMortise JapaneseTenon Lap LockoutArea LogHouseFront LogHouseHalfLap LogHouseJoint LongitudinalCut Marking MillContour Mortise
NailContour PatternContour PenContour Planing PlaningArea PlasterArea Pocket ProcessingGroup ProfileCambered ProfileFront ProfileHead RidgeValleyCut RoundArch SawContour SawCut
ScarfJoint ScrewContour SimpleScarf Slot Sphere StepJoint StepJointNotch Tenon Text TriangleCut TyroleanDovetail Variant
""".split()

CLOSED = Polyline([[100.0, 10.0, 0.0], [200.0, 10.0, 0.0], [200.0, 50.0, 0.0], [100.0, 50.0, 0.0], [100.0, 10.0, 0.0]])
OPEN = Polyline([[10.0, 10.0, 0.0], [110.0, 10.0, 0.0], [110.0, 50.0, 0.0]])


def _hole():
    return fab.Drilling(start_x=100.0, start_y=50.0, diameter=10.0)


def samples():
    area = fab.SimpleContour(CLOSED)
    path = fab.SimpleContour(OPEN, nail_length=60.0, nail_spacing=[None, 100.0, 100.0])
    patch = fab.NurbsPatch([[0.0, 0.0, -5.0], [100.0, 0.0, -5.0], [0.0, 100.0, -5.0], [100.0, 100.0, -5.0]], [1.0] * 4, [0.0, 1.0], [0.0, 1.0], 1, 1, 2, 2)
    return [
        fab.RidgeValleyCut(start_x=100.0),
        fab.SawCut(start_x=100.0, tool_position="left", machining_limits=fab.SawCutMachiningLimits()),
        fab.TriangleCut(start_x=100.0, normal_1_x=1.0, normal_2_y=1.0),
        fab.Chamfer(start_x=100.0, depth=5.0),
        fab.Planing(start_x=100.0, depth=2.0),
        fab.Sphere(start_x=100.0),
        fab.Marking(start_x=100.0),
        fab.HipValleyRafterNotch(orientation="end", start_x=100.0),
        fab.LogHouseHalfLap(orientation="end", start_x=100.0),
        fab.LogHouseJoint(start_x=100.0),
        fab.LogHouseFront(orientation="end", start_x=100.0),
        fab.House(orientation="end", start_x=900.0, subprocessings=[fab.Tenon(orientation="end", start_x=900.0)]),
        fab.HouseMortise(start_x=100.0, subprocessings=[fab.Mortise(start_x=100.0)]),
        fab.JapaneseTenon(orientation="end", start_x=900.0),
        fab.JapaneseMortise(orientation="end", start_x=100.0),
        fab.ScarfJoint(orientation="end", start_x=900.0, inclination=30.0, num_drill_hole=2),
        fab.Dovetail(orientation="end", start_x=900.0, slope=10.0),
        fab.TyroleanDovetail(orientation="end", start_x=900.0, slope=10.0, angle=90.0, frosch=fab.Frosch(10.0, 5.0)),
        fab.ProfileFront(orientation="end", start_x=900.0),
        fab.ProfileCambered(orientation="end", start_x=100.0, length=500.0),
        fab.RoundArch(start_x=100.0),
        fab.ProfileHead(orientation="end", start_x=900.0, arc1=fab.ProfileArc(radius=30.0)),
        fab.SawContour(fab.Contour(CLOSED, 50.0, inclination=[0.0] * 4), tool_position="left"),
        fab.MillContour(fab.Contour(CLOSED, 50.0, inclination=[0.0] * 4), tool_position="left"),
        fab.NailContour(contour=path),
        fab.CrampContour(contour=fab.SimpleContour(OPEN, nail_length=50.0, cramp_width=11.0, nail_spacing=[None, 100.0, 100.0])),
        fab.ScrewContour(contour=fab.SimpleContour(OPEN, screw_length=80.0, screw_diameter=6.0, nail_spacing=[None, 150.0, 150.0])),
        fab.PenContour(contour=fab.SimpleContour(OPEN)),
        fab.GlueArea(contour=area, glue_type="PU", glue_amount=120.0),
        fab.PlaningArea(contour=area, depth=2.0),
        fab.PlasterArea(contour=area, thickness=15.0),
        fab.InsulationArea(contour=area, part_ref_guid="{12345678-1234-1234-1234-123456789abc}"),
        fab.LockoutArea(contour=area, for_sawing=False),
        fab.FreeSurface(surface=patch),
        fab.ProcessingGroup(subprocessings=[_hole()]),
        fab.Connector(connector_info=fab.ConnectorInfo("plate", Frame.worldXY(), [fab.ConnectorParameter("Depth", 15.0)]), subprocessings=[_hole()]),
        fab.Variant(start_x=100.0, parameters=[fab.VariantParameter("A", 1.5)]),
        fab.PatternContour(
            insertion_patterns=fab.InsertionPatterns([fab.InsertionPattern(_hole())]),
            contour=fab.NodeContour([0.0, 0.0, 0.0], [fab.NodeContourSegment([300.0, 0.0, 0.0], 100.0)]),
        ),
    ]


def _without_process_ids(value):
    if isinstance(value, dict):
        return {key: _without_process_ids(item) for key, item in value.items() if key != "process_id"}  # assigned by the writer
    if isinstance(value, list):
        return [_without_process_ids(item) for item in value]
    return value


def _plain(processing):
    return _without_process_ids(json.loads(json_dumps(processing.__data__, minimal=True)))


def _sample_id(processing):
    return processing.PROCESSING_NAME


def test_reader_knows_every_processing_of_the_schema():
    assert sorted(set(SCHEMA_PROCESSINGS) - set(BTLxReader()._processing_types)) == []


def test_samples_cover_every_processing_added_for_btlx_2_3():
    assert len({type(sample) for sample in samples()}) == 38


@pytest.mark.parametrize("processing", samples(), ids=_sample_id)
def test_json_round_trip(processing):
    assert _plain(json_loads(json_dumps(processing))) == _plain(processing)


@pytest.mark.parametrize("processing", samples(), ids=_sample_id)
def test_proto_round_trip(processing):
    other = pb_load_bts(pb_dump_bts(processing))

    assert type(other) is type(processing)
    assert _plain(other) == _plain(processing)


@pytest.mark.parametrize("processing", samples(), ids=_sample_id)
def test_btlx_round_trip(processing, tmp_path):
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_feature(processing)
    model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(beam)
    path = str(tmp_path / "out.btlx")
    fab.BTLxWriter().write(model, path)

    reader = BTLxReader()
    read_model = reader.read(path)

    assert not reader.errors
    other = list(read_model.elements())[0].features[0]
    assert type(other) is type(processing)
    assert _plain(other) == _plain(processing)


def test_nested_processings_get_a_process_id_of_their_own():
    beam = Beam(Frame.worldXY(), 1000.0, 100.0, 200.0)
    beam.add_features([fab.ProcessingGroup(subprocessings=[_hole(), _hole()]), _hole()])
    model = TimberModel(tolerance=Tolerance(unit="MM", absolute=1e-3, relative=1e-3))
    model.add_element(beam)

    root = ET.fromstring(fab.BTLxWriter().model_to_xml(model))

    ids = [element.get("ProcessID") for element in root.iter() if element.get("ProcessID") is not None]
    assert len(ids) == 4
    assert len(set(ids)) == 4
