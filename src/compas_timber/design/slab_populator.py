from compas.geometry import Plane
from compas.geometry import Projection
from compas.geometry import angle_vectors_signed
from compas.geometry import is_parallel_vector_vector

from compas_timber.elements import Slab
from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_polyline_clockwise


class SlabSelector(object):
    """Selects slabs based on their attributes."""

    def __init__(self, slab_attr, attr_value):
        self._slab_attr = slab_attr
        self._attr_value = attr_value

    def select(self, slab):
        value = getattr(slab, self._slab_attr, None)
        if value is None:
            return False
        else:
            return value == self._attr_value


class AnySlabSelector(object):
    def select(self, _):
        return True


class SlabPopulator(Slab):
    """Create a timber assembly from a surface.

    Parameters
    ----------
    configuration_set : :class:`WallPopulatorConfigurationSet`
        The configuration for this wall populator.
    slab : :class:`compas_timber.elements.Slab`
        The slab for this populater to fill with beams.

    Attributes
    ----------
    outline_a : :class:`compas.geometry.Polyline`
        The outline A of the slab.
    outline_b : :class:`compas.geometry.Polyline`
        The outline B of the slab.
    openings : list of :class:`compas.geometry.Polyline`
        The openings in the slab.
    frame : :class:`compas.geometry.Polyline`
        The frame of the slab.
    interfaces : list of :class:`compas_timber.connections.SlabToSlabInterface`
        The interfaces of the slab. These are the connections to other slabs.
    edge_count : int
        The number of edges in the slab outline.
    stud_spacing : float
        The spacing between studs in the slab.
    stud_direction : :class:`compas.geometry.Vector`
        The direction of the studs in the slab.
    tolerance : :class:`compas_tolerance.Tolerance`
        The tolerance for the slab populator.
    sheeting_outside : float
        The outside sheeting thickness from the configuration set.
    sheeting_inside : float
        The inside sheeting thickness from the configuration set.
    frame_outline_a : :class:`compas.geometry.Polyline`
        The outline A of the frame.
    frame_outline_b : :class:`compas.geometry.Polyline`
        The outline B of the frame.
    frame_thickness : float
        The thickness of the frame. This is the thickness of the slab minus the sheeting thicknesses.


    """

    def __init__(self, slab, detail_set=None):
        super(SlabPopulator, self).__init__(slab.outline_a, slab.outline_b, slab.openings, slab.interfaces)
        self._slab = slab
        self.detail_set = detail_set or slab.detail_set or None
        if not self.detail_set:
            raise ValueError("SlabPopulator requires a configuration set or slab with a detail set.")

        self._stud_direction = None
        self.frame_outline_a = None
        self.frame_outline_b = None
        self._interior_corner_indices = []
        self._edge_perpendicular_vectors = []
        self.elements = []
        self.joints = []

    def __repr__(self):
        return "SlabPopulator({}, {})".format(self.detail_set, self._slab)

    @property
    def edge_count(self):
        """Returns the number of edges in the slab outline."""
        return len(self._slab.outline_a) - 1

    @property
    def stud_direction(self):
        """Returns the stud direction from the configuration set."""
        if self._stud_direction is None:
            if self.detail_set.stud_direction:
                if is_parallel_vector_vector(self.normal, self.detail_set.stud_direction):
                    self._stud_direction = self._slab.frame.yaxis
                else:
                    proj = Projection.from_plane(Plane.from_frame(self._slab.frame))
                    self._stud_direction = self.detail_set.stud_direction.transformed(proj)
        return self._stud_direction

    @property
    def thickness(self):
        """Returns the thickness of the slab."""
        return self._slab.thickness

    @property
    def frame_thickness(self):
        """Returns the frame thickness, adjusted for sheeting."""
        return self._slab.thickness - self.detail_set.sheeting_inside - self.detail_set.sheeting_outside

    @property
    def beams(self):
        return list(filter(lambda x: x.is_beam, self.elements))

    @property
    def plates(self):
        return list(filter(lambda x: x.is_plate, self.elements))

    @property
    def edge_beams(self):
        """Returns the edge beams of the slab."""
        beams = {}
        for beam in self.beams:
            if beam.attributes.get("edge_index", None) is not None:
                if beams.get(beam.attributes["edge_index"]) is None:
                    beams[beam.attributes["edge_index"]] = []
                beams[beam.attributes["edge_index"]].append(beam)
        return beams

    @property
    def edge_interfaces(self):
        """Get the edge interfaces of the slab."""
        interfaces = {}
        for interface in self.interfaces:
            if interface.edge_index is not None:
                if interfaces.get(interface.edge_index) is None:
                    interfaces[interface.edge_index] = []
                interfaces[interface.edge_index].append(interface)
        return interfaces

    @property
    def face_interfaces(self):
        """Get the face interfaces of the slab."""
        return [i for i in self._slab.interfaces if i.edge_index is None]

    @property
    def edge_perpendicular_vectors(self):
        """Returns the perpendicular vectors for the edges of the slab."""
        if not self._edge_perpendicular_vectors:
            self._edge_perpendicular_vectors = [get_polyline_segment_perpendicular_vector(self._slab.outline_a, i) for i in range(self.edge_count)]
        return self._edge_perpendicular_vectors

    @property
    def interior_corner_indices(self):
        """Get the indices of the interior corners of the slab outline."""
        if not self._interior_corner_indices:
            """Get the indices of the interior corners of the slab outline."""
            points = self._slab.outline_a.points[0:-1]
            cw = is_polyline_clockwise(self._slab.outline_a, self.normal)
            for i in range(len(points)):
                angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], self.normal, deg=True)
                if not (cw ^ (angle < 0)):
                    self._interior_corner_indices.append(i)
        return self._interior_corner_indices

    @property
    def interior_segment_indices(self):
        """Get the indices of the interior segments of the slab outline."""
        if not self._interior_corner_indices:
            for i in range(self.edge_count):
                if i in self.interior_corner_indices and (i + 1) % self.edge_count in self.interior_corner_indices:
                    yield i

    def get_elements_by_category(self, category):
        return list(filter(lambda x: x.attributes.get("category", None) == category, self.elements))

    def process_populator(self):
        """Processes the slab populator and creates the elements and joints."""
        self.prepare_populator()
        self.create_elements()
        self.create_joints()

    def prepare_populator(self):
        """Prepares the slab populator by adjusting outlines, openings, and interfaces."""
        self.detail_set.prepare_populator()
        for opening in self._slab.openings:
            opening.detail_set.prepare_opening(opening, self)
        for interface in self.interfaces:
            interface.detail_set.prepare_interface(interface, self)

    def create_elements(self):
        """Generates the elements for the slab."""
        self.elements.extend(self.detail_set.create_elements(self))
        for i in self.interfaces:
            self.elements.extend(i.create_elements(self))
        for o in self.openings:
            self.elements.extend(o.create_elements(self))

    def create_joints(self):
        """Generates the joints for the slab."""
        self.detail_set.split_and_cull_beams()
        self.joints.extend(self.detail_set.create_joints(self))
        for i in self.interfaces:
            self.joints.extend(i.create_joints(i, self))
        for o in self.openings:
            self.joints.extend(o.create_joints(o, self))

    @classmethod
    def from_model(cls, model, configuration_sets):
        # type: (TimberModel, List[WallPopulatorConfigurationSet]) -> List[WallPopulator]
        """matches configuration sets to walls and returns a list of SlabPopulator instances, each per wall"""
        # TODO: make sure number of walls and configuration sets match
        slabs = list(model.slabs)  # TODO: these are anoying, consider making these lists again
        if len(slabs) != len(configuration_sets):
            raise ValueError("Number of walls and configuration sets do not match")

        slab_populators = []
        for slab in slabs:
            for config_set in configuration_sets:
                if config_set.slab_selector.select(slab):
                    interfaces = [interaction.get_interface_for_slab(slab) for interaction in model.get_interactions_for_element(slab)]
                    slab_populators.append(cls(config_set, slab, interfaces))
                    break
        return slab_populators
