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



class SlabToSlabInterface(object):
    """
    interface : :class:`compas.geometry.Polyline`
        The outline of the interface area.
    frame : :class:`compas.geometry.Frame`
        The frame of the interface area.
        xaxis : interface normal (towards other slab)
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
        return "SlabToSlabInterface({0}, {1}, {2})".format(
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


class SlabJoint(Joint):
    """Models a slab to slab interaction.

    TODO:First in a very minimal way until we know where this is going.


    Parameters
    ----------
    slab_a : :class:`compas_timber.elements.Slab`
        The first slab.
    slab_b : :class:`compas_timber.elements.Slab`
        The second slab.
    topology : literal(JointTopology)
        The topology in which the slabs are connected.

    Attributes
    ----------
    slabs : tuple of :class:`compas_timber.elements.Slab`
        The slabs that are connected.
    slab_a_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of slab_a where it meets slab_b.
    slab_b_interface : :class:`compas.geometry.PlanarSurface`
        The interface surface of slab_b where it meets slab_a.

    """

    @property
    def __data__(self):
        data = super(SlabJoint, self).__data__
        data["main_slab_guid"] = self._main_slab_guid
        data["cross_slab_guid"] = self._cross_slab_guid
        data["topology"] = self.topology
        return data

    def __init__(self, main_slab=None, cross_slab=None, topology=None, **kwargs):
        super(SlabJoint, self).__init__(**kwargs)
        self.main_slab = main_slab
        self.cross_slab = cross_slab
        self._main_slab_guid = kwargs.get("main_slab_guid", None) or str(main_slab.guid)  # type: ignore
        self._cross_slab_guid = kwargs.get("cross_slab_guid", None) or str(cross_slab.guid)  # type: ignore
        self.topology = topology or JointTopology.TOPO_UNKNOWN

        self.main_slab_interface = None
        self.cross_slab_interface = None
        if main_slab and cross_slab:
            self._calculate_interfaces()

    def __repr__(self):
        return "SlabJoint({0}, {1}, {2})".format(self.main_slab, self.cross_slab, JointTopology.get_name(self.topology))

    @property
    def slabs(self):
        return self.elements

    @property
    def elements(self):
        return self.main_slab, self.cross_slab

    @property
    def geometry(self):
        assert self.main_slab_interface
        return self.main_slab_interface.interface_polyline

    @property
    def interfaces(self):
        return self.main_slab_interface, self.cross_slab_interface

    def get_interface_for_slab(self, slab):
        if slab is self.main_slab:
            return self.main_slab_interface
        elif slab is self.cross_slab:
            return self.cross_slab_interface
        else:
            raise ValueError("Slab not part of this joint.")

    def _calculate_interfaces(self):
        # from cross get the face that is closest to main with normal pointing towards main
        # from main we then need the four envelope faces
        assert self.main_slab
        assert self.cross_slab

        self.main_slab.attributes["category"] = "main"
        self.cross_slab.attributes["category"] = "cross"

        cross_face, is_joint_at_main_end, is_joint_at_cross_end = self._find_intersecting_face(self.main_slab, self.cross_slab)

        # collect intersection lines bouding the interface area
        # these cannot be directly used as they are not segmented according to the interface area
        lines = []
        cross_face_plane = Plane.from_frame(cross_face)

        # the order here should be in mirrored dependeing on the side of the slab where the joint is
        # this will result in the interface being oriented consistently on either side
        envelope_faces = self.main_slab.envelope_faces
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

        self.main_slab_interface = SlabToSlabInterface(
            interface,
            Frame(interface[0], interface_normal, up_vector),
            main_interface_type,
            InterfaceRole.MAIN,
            self.topology,
        )
        self.cross_slab_interface = SlabToSlabInterface(
            interface,
            Frame(interface[1], interface_normal.inverted(), up_vector.inverted()),
            cross_interface_type,
            InterfaceRole.CROSS,
            self.topology,
        )



    def restore_beams_from_keys(self, *args, **kwargs):
        # TODO: this is just to keep the peace. change once we know where this is going.
        self.restore_slabs_from_keys(*args, **kwargs)

    def restore_slabs_from_keys(self, model):
        self.main_slab = model.element_by_guid(self._main_slab_guid)
        self.cross_slab = model.element_by_guid(self._cross_slab_guid)
        self._calculate_interfaces()

    def flip_roles(self):
        self.main_slab, self.cross_slab = self.cross_slab, self.main_slab
        self._main_slab_guid, self._cross_slab_guid = self._cross_slab_guid, self._main_slab_guid
        self._calculate_interfaces()

    def add_features(self):
        pass
