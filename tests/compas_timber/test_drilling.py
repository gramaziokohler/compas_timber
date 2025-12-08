import pytest

from collections import OrderedDict

from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Frame
from compas.geometry import Vector
from compas.geometry import Transformation
from compas_timber.elements import Beam
from compas_timber.fabrication import Drilling

from compas_timber.fabrication import DrillingProxy

from compas.tolerance import Tolerance


@pytest.fixture
def tol():
    return Tolerance(unit="MM", absolute=1e-3, relative=1e-3)


@pytest.fixture
def beam():
    width = 60
    height = 120

    centerline = Line(Point(x=17.2361412989, y=36.4787607210, z=0.0), Point(x=1484.82372687, y=473.845866212, z=224.447551130))

    return Beam.from_centerline(centerline, width, height)


DRILL_LINES = [
    Line(
        Point(x=769.9252869559241, y=183.9103745653814, z=182.91342125683593),
        Point(x=-29.735867847271493, y=99.36335854655916, z=-74.9835882181502),
    ),
    Line(
        Point(x=1233.078758241262, y=552.3756631121547, z=288.91634397302835),
        Point(x=919.9733771842132, y=151.9561947529836, z=35.091616107586844),
    ),
    Line(
        Point(x=747.9884601522298, y=438.19140797173657, z=416.2910407751006),
        Point(x=62.620117531360165, y=-133.9315178087012, z=-297.5915556555619),
    ),
    Line(
        Point(x=549.0459501734397, y=358.0728450918177, z=190.93928067145623),
        Point(x=117.57077791770206, y=-96.72507757803294, z=-94.26138958926941),
    ),
    Line(
        Point(x=712.5957370631929, y=591.6395104959516, z=330.53901491852315),
        Point(x=694.906566516725, y=-109.49471332791097, z=-120.55275660775544),
    ),
    Line(
        Point(x=1715.7193335094323, y=809.5933092057367, z=277.9717299471872),
        Point(x=1026.032417459047, y=70.18146558317267, z=136.06982564683088),
    ),
    Line(
        Point(x=1604.4532428762723, y=823.0946268234112, z=389.8317229618566),
        Point(x=1223.458809817892, y=82.35744460148032, z=37.38687836154895),
    ),
    Line(
        Point(x=780.5352181410906, y=284.43338349525266, z=188.11237940727852),
        Point(x=130.37186929558334, y=49.71723981860626, z=-54.07360202511967),
    ),
    Line(
        Point(x=612.7955887531771, y=229.39052801635808, z=76.4764507047125),
        Point(x=-40.775856725868834, y=3.765658454253696, z=5.734117050724166),
    ),
    Line(
        Point(x=1412.161307435791, y=402.895478477511, z=571.5512558675414),
        Point(x=1014.6270421597278, y=383.0146216926868, z=-205.67906667370778),
    ),
]


PROCESS_PARAMS_DICT = [
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "4"),
            ("StartX", "538.972"),
            ("StartY", "88.610"),
            ("Angle", "350.270"),
            ("Inclination", "10.050"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1162.687"),
            ("StartY", "40.527"),
            ("Angle", "23.148"),
            ("Inclination", "31.200"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "487.129"),
            ("StartY", "10.016"),
            ("Angle", "32.697"),
            ("Inclination", "17.964"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "388.896"),
            ("StartY", "40.483"),
            ("Angle", "19.354"),
            ("Inclination", "26.995"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "736.617"),
            ("StartY", "41.339"),
            ("Angle", "55.951"),
            ("Inclination", "53.103"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1479.368"),
            ("StartY", "59.183"),
            ("Angle", "0.903"),
            ("Inclination", "30.072"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "2"),
            ("StartX", "1504.026"),
            ("StartY", "46.769"),
            ("Angle", "23.093"),
            ("Inclination", "41.648"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("StartX", "770.838"),
            ("StartY", "46.876"),
            ("Angle", "356.871"),
            ("Inclination", "10.983"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "5"),
            ("StartX", "42.079"),
            ("StartY", "72.332"),
            ("Angle", "314.408"),
            ("Inclination", "86.515"),
            ("DepthLimited", "yes"),
            ("Depth", "630.324"),
            ("Diameter", "10.000"),
        ]
    ),
    OrderedDict(
        [
            ("Name", "Drilling"),
            ("Process", "yes"),
            ("Priority", "0"),
            ("ProcessID", "0"),
            ("ReferencePlaneID", "3"),
            ("StartX", "1303.163"),
            ("StartY", "22.048"),
            ("Angle", "10.801"),
            ("Inclination", "54.731"),
            ("DepthLimited", "no"),
            ("Depth", "0.000"),
            ("Diameter", "10.000"),
        ]
    ),
]


@pytest.mark.parametrize(
    "drill_line, process_params_dict",
    zip(DRILL_LINES, PROCESS_PARAMS_DICT),
)
def test_drilling(beam, drill_line, process_params_dict):
    diameter = 10.0

    drilling = Drilling.from_line_and_element(drill_line, beam, diameter)

    generated_params = drilling.params.header_attributes
    generated_params.update(drilling.params.as_dict())
    for key, value in process_params_dict.items():
        assert generated_params[key] == value


def test_drilling_scaled():
    drilling = Drilling(start_x=10.0, start_y=20.0, angle=30.0, inclination=40.0, diameter=50.0, depth=60.0, ref_side_index=1)

    scaled = drilling.scaled(2.0)

    assert scaled.start_x == drilling.start_x * 2.0
    assert scaled.start_y == drilling.start_y * 2.0
    assert scaled.angle == drilling.angle
    assert scaled.inclination == drilling.inclination
    assert scaled.diameter == drilling.diameter * 2.0


def test_drilling_transforms_with_beam(tol):
    centerline = Line(Point(x=17.2361412989, y=36.4787607210, z=0.0), Point(x=1484.82372687, y=473.845866212, z=224.447551130))
    width = 60
    height = 120
    beam_a = Beam.from_centerline(centerline, width, height)
    beam_b = Beam.from_centerline(centerline, width, height)

    drill_line = Line(
        Point(x=769.9252869559241, y=183.9103745653814, z=182.91342125683593),
        Point(x=-29.735867847271493, y=99.36335854655916, z=-74.9835882181502),
    )
    diameter = 10.0

    # Create drilling instances
    instance_a = Drilling.from_line_and_element(drill_line, beam_a, diameter)
    instance_b = Drilling.from_line_and_element(drill_line, beam_b, diameter)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # properties should be the same after transformation
    assert tol.is_close(instance_a.start_x, instance_b.start_x)
    assert tol.is_close(instance_a.start_y, instance_b.start_y)
    assert tol.is_close(instance_a.angle, instance_b.angle)
    assert tol.is_close(instance_a.inclination, instance_b.inclination)
    assert instance_a.depth_limited == instance_b.depth_limited
    assert tol.is_close(instance_a.depth, instance_b.depth)
    assert tol.is_close(instance_a.diameter, instance_b.diameter)
    assert tol.is_close(instance_a.ref_side_index, instance_b.ref_side_index)

    # cylinders should transform correctly
    cylinder_a = instance_a.cylinder_from_params_and_element(beam_a)
    cylinder_b = instance_b.cylinder_from_params_and_element(beam_b)

    assert tol.is_close(cylinder_a.radius, cylinder_b.radius)
    cylinder_a.transform(transformation)
    assert tol.is_allclose(cylinder_a.circle.plane.point, cylinder_b.circle.plane.point)
    assert tol.is_allclose(cylinder_a.circle.plane.normal, cylinder_b.circle.plane.normal)


def test_drilling_proxy_transforms_with_beam(tol):
    centerline = Line(Point(x=17.2361412989, y=36.4787607210, z=0.0), Point(x=1484.82372687, y=473.845866212, z=224.447551130))
    width = 60
    height = 120
    beam_a = Beam.from_centerline(centerline, width, height)
    beam_b = Beam.from_centerline(centerline, width, height)

    drill_line = Line(
        Point(x=769.9252869559241, y=183.9103745653814, z=182.91342125683593),
        Point(x=-29.735867847271493, y=99.36335854655916, z=-74.9835882181502),
    )
    diameter = 10.0

    # Create DrillingProxy instances
    instance_a = DrillingProxy.from_line_and_element(drill_line, beam_a, diameter)
    instance_b = DrillingProxy.from_line_and_element(drill_line, beam_b, diameter)

    transformation = Transformation.from_frame(Frame(Point(1000, 555, -69), Vector(1, 4, 5), Vector(6, 1, -3)))
    beam_b.transform(transformation)

    # unproxify to get the actual Drilling instances
    drilling_a = instance_a.unproxified()
    drilling_b = instance_b.unproxified()

    # properties should be the same after transformation
    assert tol.is_close(drilling_a.start_x, drilling_b.start_x)
    assert tol.is_close(drilling_a.start_y, drilling_b.start_y)
    assert tol.is_close(drilling_a.angle, drilling_b.angle)
    assert tol.is_close(drilling_a.inclination, drilling_b.inclination)
    assert drilling_a.depth_limited == drilling_b.depth_limited
    assert tol.is_close(drilling_a.depth, drilling_b.depth)
    assert tol.is_close(drilling_a.diameter, drilling_b.diameter)
    assert tol.is_close(drilling_a.ref_side_index, drilling_b.ref_side_index)

    # cylinders should transform correctly
    cylinder_a = drilling_a.cylinder_from_params_and_element(beam_a)
    cylinder_b = drilling_b.cylinder_from_params_and_element(beam_b)

    cylinder_a.transform(transformation)

    assert tol.is_close(cylinder_a.radius, cylinder_b.radius)
    assert tol.is_allclose(cylinder_a.circle.plane.point, cylinder_b.circle.plane.point)
    assert tol.is_allclose(cylinder_a.circle.plane.normal, cylinder_b.circle.plane.normal)
