import pytest
from compas.geometry import Box, Frame, Point, Vector, Polyline, Plane
from compas.tolerance import TOL

from compas_timber.design.slab_populator import SlabPopulator, SlabPopulatorConfigurationSet, AnySlabSelector
from compas_timber.elements import Beam, Slab
from compas_timber.connections import TButtJoint, LButtJoint
from compas_timber.design import CategoryRule


class TestSlab:
    """Helper class to mock a Slab for testing"""
    def __init__(self, outline_a, outline_b, frame=None, thickness=0.2, openings=None):
        self.outline_a = outline_a
        self.outline_b = outline_b
        self.frame = frame or Frame.worldXY()
        self.thickness = thickness
        self.openings = openings or []
        self.interfaces = []
        self.edge_planes = []
        for i in range(len(self.outline_a.lines)):
            line = self.outline_a.lines[i]
            midpt = line.point_at(0.5)
            # Create plane at midpoint of edge with normal pointing outward
            normal = self.frame.zaxis.cross(line.direction)
            normal.unitize()
            self.edge_planes.append(Plane(midpt, normal))


@pytest.fixture
def basic_slab():
    """Creates a simple rectangular slab"""
    outline_a = Polyline([
        Point(0, 0, 0),
        Point(3, 0, 0),
        Point(3, 2, 0),
        Point(0, 2, 0),
        Point(0, 0, 0)
    ])
    outline_b = Polyline([
        Point(0, 0, 0.2),
        Point(3, 0, 0.2),
        Point(3, 2, 0.2),
        Point(0, 2, 0.2),
        Point(0, 0, 0.2)
    ])
    return TestSlab(outline_a, outline_b)


@pytest.fixture
def slab_with_window():
    """Creates a slab with a window opening"""
    outline_a = Polyline([
        Point(0, 0, 0),
        Point(4, 0, 0),
        Point(4, 3, 0),
        Point(0, 3, 0),
        Point(0, 0, 0)
    ])
    outline_b = Polyline([
        Point(0, 0, 0.2),
        Point(4, 0, 0.2),
        Point(4, 3, 0.2),
        Point(0, 3, 0.2),
        Point(0, 0, 0.2)
    ])
    window = Polyline([
        Point(1, 1, 0),
        Point(2, 1, 0),
        Point(2, 2, 0),
        Point(1, 2, 0),
        Point(1, 1, 0)
    ])
    return TestSlab(outline_a, outline_b, openings=[window])


@pytest.fixture
def slab_with_door():
    """Creates a slab with a door opening at the bottom"""
    outline_a = Polyline([
        Point(0, 0, 0),
        Point(4, 0, 0),
        Point(4, 3, 0),
        Point(0, 3, 0),
        Point(0, 0, 0)
    ])
    outline_b = Polyline([
        Point(0, 0, 0.2),
        Point(4, 0, 0.2),
        Point(4, 3, 0.2),
        Point(0, 3, 0.2),
        Point(0, 0, 0.2)
    ])
    door = Polyline([
        Point(1, 0, 0),
        Point(2, 0, 0),
        Point(2, 2, 0),
        Point(1, 2, 0),
        Point(1, 0, 0)
    ])
    return TestSlab(outline_a, outline_b, openings=[door])


@pytest.fixture
def default_config():
    """Default configuration for testing"""
    return SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        wall_selector=AnySlabSelector()
    )


def test_slab_populator_initialization(basic_slab, default_config):
    """Test that SlabPopulator initializes correctly"""
    populator = SlabPopulator(default_config, basic_slab)
    assert populator._slab == basic_slab
    assert populator._config_set == default_config
    assert populator.stud_direction == basic_slab.frame.yaxis
    assert populator.normal == basic_slab.frame.zaxis
    assert populator.frame_thickness == basic_slab.thickness


def test_slab_populator_create_elements_basic(basic_slab, default_config):
    """Test basic element creation in a simple slab"""
    populator = SlabPopulator(default_config, basic_slab)
    elements = populator.create_elements()
    
    # Should have edge beams for each edge (4)
    # Plus several studs based on stud_spacing and slab width
    assert len(populator.beams) > 4
    
    # Check edge beams
    assert len(populator.edge_studs) > 0
    assert len(populator.top_plate_beams) > 0
    assert len(populator.bottom_plate_beams) > 0


def test_slab_populator_with_custom_dimensions(basic_slab):
    """Test SlabPopulator with custom beam dimensions"""
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        custom_dimensions={"stud": (0.15, 0.2), "edge_stud": (0.2, 0.2)},
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, basic_slab)
    elements = populator.create_elements()
    
    # Check that custom dimensions were applied
    for stud in populator.studs:
        assert stud.width == 0.15
    
    for edge_stud in populator.edge_studs:
        assert edge_stud.width == 0.2


def test_slab_populator_with_sheeting(basic_slab):
    """Test SlabPopulator with inside and outside sheeting"""
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        sheeting_inside=0.05,
        sheeting_outside=0.03,
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, basic_slab)
    elements = populator.create_elements()
    
    # Should have created plates for the sheeting
    assert len(populator.plates) == 2
    
    # Frame thickness should be reduced by sheeting thickness
    assert populator.frame_thickness == 0.12  # 0.2 - 0.05 - 0.03


def test_slab_populator_with_window(slab_with_window, default_config):
    """Test SlabPopulator with a window opening"""
    populator = SlabPopulator(default_config, slab_with_window)
    elements = populator.create_elements()
    
    # Should have created window elements
    assert len(populator._openings) == 1
    window = populator._openings[0]
    
    # Window should have header, sill, and king studs
    assert window.header is not None
    assert window.sill is not None
    assert len(window.king_studs) == 2
    
    # Default config has lintel_posts=True
    assert len(window.jack_studs) == 2


def test_slab_populator_with_door(slab_with_door, default_config):
    """Test SlabPopulator with a door opening"""
    populator = SlabPopulator(default_config, slab_with_door)
    elements = populator.create_elements()
    
    # Should have created door elements
    assert len(populator._openings) == 1
    door = populator._openings[0]
    
    # Door should have header and king studs but no sill
    assert door.header is not None
    assert not hasattr(door, 'sill') or door.sill not in door.beams
    assert len(door.king_studs) == 2


def test_slab_populator_without_lintel_posts(slab_with_window):
    """Test SlabPopulator with lintel_posts=False"""
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        lintel_posts=False,
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, slab_with_window)
    elements = populator.create_elements()
    
    window = populator._openings[0]
    # With lintel_posts=False, there should be no jack studs
    assert len(window.jack_studs) == 0


def test_slab_populator_with_custom_stud_direction(basic_slab):
    """Test SlabPopulator with custom stud direction"""
    custom_direction = Vector(1, 0, 0)
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        stud_direction=custom_direction,
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, basic_slab)
    elements = populator.create_elements()
    
    # Stud direction should match the custom direction
    assert populator.stud_direction.is_parallel(custom_direction, tol=TOL.angle)


def test_slab_populator_joint_generation(basic_slab, default_config):
    """Test that joints are correctly generated"""
    populator = SlabPopulator(default_config, basic_slab)
    elements = populator.create_elements()
    
    # There should be joints between elements
    assert len(populator._joints) > 0
    
    # Check that all joints connect two elements from the populator
    for joint in populator._joints:
        assert joint.element_a in populator.beams
        assert joint.element_b in populator.beams


def test_slab_populator_with_joint_overrides(basic_slab):
    """Test SlabPopulator with joint overrides"""
    # Override the default T-butt joint between stud and top_plate_beam with an L-butt joint
    custom_rules = [
        CategoryRule(LButtJoint, "stud", "top_plate_beam"),
    ]
    
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        joint_overrides=custom_rules,
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, basic_slab)
    elements = populator.create_elements()
    
    # Check that the override was applied
    for joint in populator._joints:
        if (joint.element_a.attributes.get("category") == "stud" and 
            joint.element_b.attributes.get("category") == "top_plate_beam"):
            assert isinstance(joint, LButtJoint)
        elif (joint.element_b.attributes.get("category") == "stud" and 
              joint.element_a.attributes.get("category") == "top_plate_beam"):
            assert isinstance(joint, LButtJoint)


def test_slab_populator_with_edge_stud_offset(basic_slab):
    """Test SlabPopulator with edge_stud_offset"""
    config = SlabPopulatorConfigurationSet(
        stud_spacing=0.4,
        beam_width=0.1,
        edge_stud_offset=0.05,
        wall_selector=AnySlabSelector()
    )
    
    populator = SlabPopulator(config, basic_slab)
    elements = populator.create_elements()
    
    # Check that edge studs have the correct offset
    # Would need to verify visually or with more complex assertions