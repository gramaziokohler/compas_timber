from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane
from compas.itertools import pairwise
from compas_model.interactions import Interaction

from .joint import JointTopology


class WallJoint(Interaction):
    """Models a wall to wall interaction.

    TODO:First in a very minimal way until we know where this is going.

    Parameters
    ----------
    wall_a : :class:`compas_timber.elements.Wall`
        The first wall.
    wall_b : :class:`compas_timber.elements.Wall`
        The second wall.
    topology : literal(JointTopology)
        The topology in which the walls are connected.

    Attributes
    ----------
    walls : tuple of :class:`compas_timber.elements.Wall`
        The walls that are connected.
    wall_a_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of wall_a where it meets wall_b.
    wall_b_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of wall_b where it meets wall_a.

    """

    @property
    def __data__(self):
        data = super(WallJoint, self).__data__
        data["main_wall_guid"] = self._main_wall_guid
        data["cross_wall_guid"] = self._cross_wall_guid
        data["topology"] = self.topology
        return data

    def __init__(self, main_wall=None, cross_wall=None, topology=None, **kwargs):
        super(WallJoint, self).__init__(**kwargs)
        self.main_wall = main_wall
        self.cross_wall = cross_wall
        self._main_wall_guid = kwargs.get("main_wall_guid", None) or str(main_wall.guid)  # type: ignore
        self._cross_wall_guid = kwargs.get("cross_wall_guid", None) or str(cross_wall.guid)  # type: ignore
        self.topology = topology or JointTopology.TOPO_UNKNOWN

        self.main_wall_interface = None, None
        self.cross_wall_interface = None, None
        if main_wall and cross_wall:
            self._calculate_interfaces()

    def __repr__(self):
        return "WallJoint({0}, {1}, {2})".format(self.main_wall, self.cross_wall, JointTopology.get_name(self.topology))

    @property
    def walls(self):
        return self.main_wall, self.cross_wall

    @property
    def geometry(self):
        interface_polyline, _ = self.main_wall_interface
        return interface_polyline

    def _calculate_interfaces(self):
        # from cross get the face that is closest to main with normal pointing towards main
        # from main we then need the four envelope faces
        # TODO: find the cross face using something like find side_incidence_...
        assert self.main_wall
        assert self.cross_wall

        cross_face, dir_cross_to_main = self._find_intersecting_face(self.main_wall, self.cross_wall)

        # collect intersection lines bouding the interface area
        # these cannot be directly used as they are not segmented according to the interface area
        lines = []
        cross_face_plane = Plane.from_frame(cross_face)
        for face in self.main_wall.envelope_faces:
            face_plane = Plane.from_frame(face)
            intersection = intersection_plane_plane(face_plane, cross_face_plane)
            if not intersection:
                raise ValueError("mmhh..")
            lines.append(Line(*intersection))

        # find the intersection points of the lines
        points = []
        for line_a, line_b in pairwise(lines + [lines[0]]):
            p1, _ = intersection_line_line(line_a, line_b)
            points.append(p1)

        # connect the points to form the interface
        interface = Polyline(points + [points[0]])
        self.main_wall_interface = interface, dir_cross_to_main.inverted()
        self.cross_wall_interface = interface, dir_cross_to_main

    @staticmethod
    def _find_intersecting_face(main_wall, cross_wall):
        # find the face of the cross wall where the main wall meets it, return the face and the direction towards the main wall
        main_baseline = main_wall.baseline
        p1, _ = intersection_line_line(main_baseline, cross_wall.baseline)
        if p1 is None:
            raise ValueError("No intersection found between walls.")

        baseline_direction = main_baseline.direction

        p1 = Point(*p1)
        is_joint_at_main_end = p1.distance_to_point(main_baseline.start) > p1.distance_to_point(main_baseline.end)
        if is_joint_at_main_end:
            # we always want the baseline direction the points away from the joint
            baseline_direction = baseline_direction.inverted()

        face_angles = {}
        for ref_side_index, face in enumerate(cross_wall.faces):
            face_angles[ref_side_index] = angle_vectors(face.normal, baseline_direction)

        cross_face_index = min(face_angles, key=lambda k: face_angles[k])
        return cross_wall.faces[cross_face_index], baseline_direction.inverted()

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_walls_from_keys(*args, **kwargs)

    def restore_walls_from_keys(self, model):
        self.main_wall = model.element_by_guid(self._main_wall_guid)
        self.cross_wall = model.element_by_guid(self._cross_wall_guid)
        self._calculate_interfaces()
