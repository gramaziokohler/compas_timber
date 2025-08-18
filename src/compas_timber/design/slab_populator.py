from compas.geometry import Plane
from compas.geometry import Projection
from compas.geometry import Frame
from compas.geometry import Transformation
from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import intersection_line_plane
from compas.geometry import Box
from compas.geometry import bounding_box_xy
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed
from compas.geometry import is_parallel_vector_vector

from compas_timber.utils import get_polyline_segment_perpendicular_vector
from compas_timber.utils import is_polyline_clockwise


class SlabSelector(object): #TODO change to detail selector or similar
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



class OpeningPopulator(object):
    """Populates openings in a slab."""


    def __init__(self, opening, detail_set, slab_populator):
        self.opening = opening
        self.detail_set = detail_set
        self.slab_populator = slab_populator



class SlabPopulator(object):
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

    def __init__(self, slab, detail_set):
        # super(SlabPopulator, self).__init__(slab.outline_a, slab.outline_b, slab.openings, slab.interfaces)
        self._slab = slab
        self.detail_set = detail_set
        self.test = []

        self.frame = self.get_frame(slab, self.detail_set)


        self.outline_a = slab.local_outlines[0].transformed(self.transform_to_local)
        self.outline_b = slab.local_outlines[1].transformed(self.transform_to_local)
        self.test = []
        for opening in slab.openings:
            outline = opening.outline.copy()
            outline.transform(opening.transformation)
            outline.transform(slab.transformation.inverse())
            outline.transform(self.transformation.inverse())
            self.test.append(outline)
        self._frame_outline = None
        self._interior_corner_indices = []
        self._edge_perpendicular_vectors = []
        self.elements = []
        self.direct_rules = []
        detail_set.prepare_populator(self)

    def __repr__(self):
        return "SlabPopulator({}, {})".format(self.detail_set, self._slab)

    @property
    def edge_count(self):
        """Returns the number of edges in the slab outline."""
        return len(self.outline_a) - 1


    def get_frame(self, slab, detail_set):
        """The slab_populator frame in global space."""
        stud_dir = detail_set.stud_direction.transformed(slab.transformation.inverse())
        stud_dir[2]=0.0
        frame = Frame(Point(0, 0, 0), cross_vectors(stud_dir, Vector(0,0,1)), stud_dir)
        transform_to_sp = Transformation.from_frame(frame)
        pts = slab.local_outlines[0].points + slab.local_outlines[1].points
        rebased_pts = [pt.transformed(transform_to_sp.inverse()) for pt in pts]
        min_pt = bounding_box_xy(rebased_pts)[0]
        frame.translate(frame.xaxis * min_pt[0] + frame.yaxis * min_pt[1] + Vector(0, 0, detail_set.sheeting_inside + self.frame_thickness / 2))
        return frame

    @property
    def transform_to_local(self):
        """The transformation from slab.frame ."""
        return Transformation.from_frame_to_frame(self.frame, Frame.worldXY())


    @property
    def transform_to_parent(self):
        """Returns the frame of the slab."""
        return self.transform_to_local.inverse()

    @property
    def transformation(self):
        """Returns the transformation from world coordinates to slab local coordinates."""
        return Transformation.from_frame(self.frame)

    @property
    def frame_outline(self):
        """Returns the frame outline of the slab."""
        if self._frame_outline is None:
            pts = []
            for pt_a, pt_b in zip(self.outline_a.points, self.outline_b.points):
                line = Line(pt_a, pt_b)
                pts.append(Point(*intersection_line_plane(line, Plane.worldXY())))
            print(pts)
            self._frame_outline = Polyline(pts)
        return self._frame_outline

    @property
    def edge_planes(self):
        """Returns the edge planes of the slab."""
        return self._slab.edge_planes

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
            self._edge_perpendicular_vectors = [get_polyline_segment_perpendicular_vector(self.outline_a, i) for i in range(self.edge_count)]
        return self._edge_perpendicular_vectors

    @property
    def interior_corner_indices(self):
        """Get the indices of the interior corners of the slab outline."""
        if not self._interior_corner_indices:
            """Get the indices of the interior corners of the slab outline."""
            points = self.outline_a.points[0:-1]
            cw = is_polyline_clockwise(self.outline_a, self.normal)
            for i in range(len(points)):
                angle = angle_vectors_signed(points[i - 1] - points[i], points[(i + 1) % len(points)] - points[i], Vector.worldZ, deg=True)
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

    @property
    def obb(self):
        """Calculates the oriented bounding box (OBB) for the slab."""
        return Box.from_points(self.outline_a.points + self.outline_b.points)

    def get_elements_by_category(self, category):
        return list(filter(lambda x: x.attributes.get("category", None) == category, self.elements))

    def process_populator(self):
        """Processes the slab populator and creates the elements and joints."""
        self.create_elements()
        self.cull_and_split_studs()
        self.create_joints()


    def create_elements(self):
        """Generates the elements for the slab."""
        self.detail_set.create_elements(self)
        # for i in self.interfaces:
        #     i.detail_set.create_elements(i, self)
        # for o in self.openings:
        #     o.detail_set.create_elements(o, self)

    def cull_and_split_studs(self):
        """Culls the studs that are overlap with details and splits studs that intersect with openings and interfaces."""
        self.detail_set._extend_interior_corner_beams(self)
        for interface in self.interfaces:
            if interface.interface_role == "CROSS":
                interface.detail_set.cull_and_split_studs(interface, self)
        for opening in self.openings:
            opening.detail_set.cull_and_split_studs(opening, self)

    def create_joints(self):
        """Generates the joints for the slab."""
        self.detail_set.create_joints(self)
        for i in self.interfaces:
            i.detail_set.create_joints(i, self)
        for o in self.openings:
            o.detail_set.create_joints(o, self)

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
