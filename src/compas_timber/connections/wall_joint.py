from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import angle_vectors
from compas.geometry import intersection_line_line
from compas.geometry import intersection_plane_plane
from compas.itertools import pairwise

from .joint import Joint
from .joint import JointTopology


class InterfaceRole(object):
    """
    Enumeration of the possible interface roles.

    Attributes
    ----------
    MAIN : literal(0)
        The interface is the main interface.
    CROSS : literal(1)
        The interface is the cross interface.
    """

    MAIN = "MAIN"
    CROSS = "CROSS"


class InterfaceLocation(object):
    """
    Enumeration of the possible interface location within the wall.

    Attributes
    ----------
    BACK : literal(0)
        The interface is at the back of the wall.
    FRONT : literal(1)
        The interface is at the front of the wall.
    TOP : literal(2)
        The interface is at the top of the wall.
    BOTTOM : literal(3)
        The interface is at the bottom of the wall.
    OTHER : literal(4)
        The interface is at some other location.
    """

    BACK = "BACK"
    FRONT = "FRONT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    OTHER = "OTHER"


class WallToWallInterface(object):
    """
    interface : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other wall)
        yaxis : up along the interface side
        normal: width direction, perpendicular to the interface

    """

    def __init__(self, interface_polyline, frame, interface_type, interface_role, topology):
        self.interface_polyline = interface_polyline
        self.frame = frame
        self.interface_type = interface_type
        self.interface_role = interface_role
        self.topology = topology  # TODO: don't like this here

    def __repr__(self):
        return "WallToWallInterface({0}, {1}, {2})".format(
            self.interface_type,
            self.interface_role,
            JointTopology.get_name(self.topology),
        )

    def as_plane(self):
        """Returns the interface as a plane.

        Returns
        -------
        :class:`compas.geometry.Plane`
            The plane of the interface.
        """
        return Plane.from_three_points(*self.interface_polyline.points[:3])


class WallJoint(Joint):
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

        self.main_wall_interface = None
        self.cross_wall_interface = None
        if main_wall and cross_wall:
            self._calculate_interfaces()

    def __repr__(self):
        return "WallJoint({0}, {1}, {2})".format(self.main_wall, self.cross_wall, JointTopology.get_name(self.topology))

    @property
    def walls(self):
        return self.elements

    @property
    def elements(self):
        return self.main_wall, self.cross_wall

    @property
    def geometry(self):
        assert self.main_wall_interface
        return self.main_wall_interface.interface_polyline

    @property
    def interfaces(self):
        return self.main_wall_interface, self.cross_wall_interface

    def get_interface_for_wall(self, wall):
        if wall is self.main_wall:
            return self.main_wall_interface
        elif wall is self.cross_wall:
            return self.cross_wall_interface
        else:
            raise ValueError("Wall not part of this joint.")

    def _calculate_interfaces(self):
        # from cross get the face that is closest to main with normal pointing towards main
        # from main we then need the four envelope faces
        assert self.main_wall
        assert self.cross_wall

        self.main_wall.attributes["category"] = "main"
        self.cross_wall.attributes["category"] = "cross"

        cross_face, is_joint_at_main_end, is_joint_at_cross_end = self._find_intersecting_face(self.main_wall, self.cross_wall)

        # collect intersection lines bouding the interface area
        # these cannot be directly used as they are not segmented according to the interface area
        lines = []
        cross_face_plane = Plane.from_frame(cross_face)

        # the order here should be in mirrored dependeing on the side of the wall where the joint is
        # this will result in the interface being oriented consistently on either side
        envelope_faces = self.main_wall.envelope_faces
        if is_joint_at_main_end:
            envelope_faces = [envelope_faces[0], envelope_faces[3], envelope_faces[2], envelope_faces[1]]

        main_interface_type = InterfaceLocation.FRONT if is_joint_at_main_end else InterfaceLocation.BACK
        cross_interface_type = InterfaceLocation.FRONT if is_joint_at_cross_end else InterfaceLocation.BACK

        if self.topology == JointTopology.TOPO_T:
            cross_interface_type = InterfaceLocation.OTHER

        for face in envelope_faces:
            face_plane = Plane.from_frame(face)
            intersection = intersection_plane_plane(face_plane, cross_face_plane)

            assert intersection  # back to the drawing board if this fails

            lines.append(Line(*intersection))

        # find the intersection points of the lines
        points = []
        for line_a, line_b in pairwise(lines + [lines[0]]):
            p1, _ = intersection_line_line(line_a, line_b)
            points.append(p1)

        # connect the points to form the interface
        interface = Polyline(points + [points[0]])
        interface_normal = cross_face.normal
        up_vector = Vector.from_start_end(points[0], points[1])

        self.main_wall_interface = WallToWallInterface(
            interface,
            Frame(interface[0], interface_normal, up_vector),
            main_interface_type,
            InterfaceRole.MAIN,
            self.topology,
        )
        self.cross_wall_interface = WallToWallInterface(
            interface,
            Frame(interface[1], interface_normal.inverted(), up_vector.inverted()),
            cross_interface_type,
            InterfaceRole.CROSS,
            self.topology,
        )

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

        is_joint_at_cross_end = p1.distance_to_point(cross_wall.baseline.start) > p1.distance_to_point(cross_wall.baseline.end)

        face_angles = {}
        for ref_side_index, face in enumerate(cross_wall.faces):
            face_angles[ref_side_index] = angle_vectors(face.normal, baseline_direction)

        cross_face_index = min(face_angles, key=lambda k: face_angles[k])
        return cross_wall.faces[cross_face_index], is_joint_at_main_end, is_joint_at_cross_end

    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_walls_from_keys(*args, **kwargs)

    def restore_walls_from_keys(self, model):
        self.main_wall = model.element_by_guid(self._main_wall_guid)
        self.cross_wall = model.element_by_guid(self._cross_wall_guid)
        self._calculate_interfaces()

    def flip_roles(self):
        self.main_wall, self.cross_wall = self.cross_wall, self.main_wall
        self._main_wall_guid, self._cross_wall_guid = self._cross_wall_guid, self._main_wall_guid
        self._calculate_interfaces()

    def add_features(self):
        pass
