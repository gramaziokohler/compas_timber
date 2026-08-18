import pytest

from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Sphere
from compas_model.elements import Element
from compas_model.models import Model
from compas_pb import pb_dump_bts
from compas_pb import pb_dump_json
from compas_pb import pb_load_bts
from compas_pb import pb_load_json
from compas_timber.elements import Beam
from compas_timber.model import TimberModel
from compas_timber.planning import BuildingPlan
from compas_timber.planning import BuildingPlanModelContainer
from compas_timber.planning import SimpleSequenceGenerator


@pytest.fixture(autouse=True)
def load_serializers():
    import compas_timber.proto.conversions  # noqa: F401


@pytest.fixture
def timber_model():
    model = TimberModel()
    model.add_element(Beam(name="Beam01", length=4000, width=200, height=300, frame=Frame.worldXY()))
    model.add_element(Beam(name="Beam02", length=5000, width=250, height=350, frame=Frame.worldYZ()))
    model.add_element(Beam(name="Beam03", length=5000, width=250, height=350, frame=Frame.worldZX()))
    return model


@pytest.fixture
def just_model():
    model = Model()
    model.add_element(Element(name="Element01", frame=Frame.worldXY(), geometry=Box(100.0).to_mesh()))
    model.add_element(Element(name="Element02", frame=Frame.worldYZ(), geometry=Box(200.0).to_mesh()))
    model.add_element(Element(name="Element03", frame=Frame.worldYZ(), geometry=Box(300.0).to_mesh()))
    model.add_element(Element(name="Element04", frame=Frame.worldYZ(), geometry=Box(400.0).to_mesh()))
    return model


def test_building_plan_timber_model(timber_model):
    element_map = {str(element.guid): element for element in timber_model.elements()}
    plan = SimpleSequenceGenerator(timber_model).result

    geometries_map = {guid: f"{element.name}.obj" for guid, element in element_map.items()}

    json_plan = pb_dump_json({"elements": element_map, "plan": plan, "geometries": geometries_map})
    loaded_plan = pb_load_json(json_plan)

    assert "elements" in loaded_plan
    assert "plan" in loaded_plan
    assert "geometries" in loaded_plan

    for guid, element in loaded_plan["elements"].items():
        assert isinstance(element, Beam)
        assert guid in element_map
        assert guid == str(element.guid)

    assert isinstance(loaded_plan["plan"], BuildingPlan)

    for loaded_step, step in zip(loaded_plan["plan"].steps, plan.steps):
        assert step.element_ids == loaded_step.element_ids


def test_building_plan_justmodel(just_model):
    element_map = {str(element.guid): element for element in just_model.elements()}
    plan = SimpleSequenceGenerator(just_model).result

    geometries_map = {guid: f"{element.name}.obj" for guid, element in element_map.items()}

    json_plan = pb_dump_json({"elements": element_map, "plan": plan, "geometries": geometries_map})
    loaded_plan = pb_load_json(json_plan)

    assert isinstance(loaded_plan, dict)
    assert "elements" in loaded_plan
    assert "plan" in loaded_plan
    assert "geometries" in loaded_plan

    for guid, element in loaded_plan["elements"].items():
        assert isinstance(element, Element)
        assert guid in element_map
        assert guid == str(element.guid)

    assert isinstance(loaded_plan["plan"], BuildingPlan)

    for loaded_step, step in zip(loaded_plan["plan"].steps, plan.steps):
        assert step.element_ids == loaded_step.element_ids


def test_buildingplanmodelcontainer_serialization(just_model):
    element_map = {str(element.guid): element for element in just_model.elements()}
    plan = SimpleSequenceGenerator(just_model).result
    geometries_map = {guid: f"{element.name}.obj" for guid, element in element_map.items()}
    container = BuildingPlanModelContainer(plan, element_map, geometries_map)

    serialized = pb_dump_bts(container)
    loaded_container = pb_load_bts(serialized)

    assert isinstance(loaded_container, BuildingPlanModelContainer)
    assert isinstance(loaded_container.plan, BuildingPlan)
    assert loaded_container.plan.name == container.plan.name
    assert len(loaded_container.plan.steps) == len(container.plan.steps)

    assert set(loaded_container.elements.keys()) == set(container.elements.keys())
    for guid in container.elements:
        assert str(loaded_container.elements[guid].guid) == str(container.elements[guid].guid)
        assert loaded_container.elements[guid].name == container.elements[guid].name

    assert set(loaded_container.geometries.keys()) == set(container.geometries.keys())
    for guid in container.geometries:
        assert loaded_container.geometries[guid] == container.geometries[guid]


def test_buildingplanmodelcontainer_shapes(just_model):
    element_map = {str(element.guid): element for element in just_model.elements()}
    elements = list(just_model.elements())
    plan = SimpleSequenceGenerator(just_model).result
    geometries_map = {
        str(elements[0].guid): f"{elements[0].name}.obj",
        str(elements[1].guid): Box(3.0),
        str(elements[2].guid): Cylinder(2.0, 30.0),
        str(elements[3].guid): Sphere(100.0),
    }
    container = BuildingPlanModelContainer(plan, element_map, geometries_map)

    serialized = pb_dump_bts(container)
    loaded_container = pb_load_bts(serialized)

    assert isinstance(loaded_container, BuildingPlanModelContainer)
    assert isinstance(loaded_container.plan, BuildingPlan)
    assert loaded_container.plan.name == container.plan.name
    assert len(loaded_container.plan.steps) == len(container.plan.steps)

    assert set(loaded_container.elements.keys()) == set(container.elements.keys())
    for guid in container.elements:
        assert str(loaded_container.elements[guid].guid) == str(container.elements[guid].guid)
        assert loaded_container.elements[guid].name == container.elements[guid].name

    assert set(loaded_container.geometries.keys()) == set(container.geometries.keys())

    assert isinstance(loaded_container.geometries[str(elements[0].guid)], str)
    assert isinstance(loaded_container.geometries[str(elements[1].guid)], Box)
    assert isinstance(loaded_container.geometries[str(elements[2].guid)], Cylinder)
    assert isinstance(loaded_container.geometries[str(elements[3].guid)], Sphere)
