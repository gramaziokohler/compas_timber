import copy
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Vector
from compas.geometry import dot_vectors
from compas.geometry import Transformation

from .joint import JointTopology
from .plate_joint import PlateJoint
from compas_timber.elements import SlabConnectionInterface


class SlabJoint(PlateJoint):
    """Models a plate to plate interaction.

    Parameters
    ----------
    plate_a : :class:`compas_timber.elements.Plate`
        The first plate.
    plate_b : :class:`compas_timber.elements.Plate`
        The second plate.
    topology : literal(JointTopology)
        The topology in which the plates are connected.
    a_segment_index : int
        The index of the segment in plate_a's outline where the plates are connected.
    b_segment_index : int
        The index of the segment in plate_b's outline where the plates are connected.
    **kwargs : dict, optional
        Additional keyword arguments to pass to the parent class.

    Attributes
    ----------
    plate_a : :class:`compas_timber.elements.Plate`
        The first plate.
    plate_b : :class:`compas_timber.elements.Plate`
        The second plate.
    plates : tuple of :class:`compas_timber.elements.Plate`
        The plates that are connected.
    interface_a : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_a where it meets plate_b.
    interface_b : :class:`compas.geometry.PlanarSurface`
        The interface surface of plate_b where it meets plate_a.

    """

    @property
    def __data__(self):
        data = super(SlabJoint, self).__data__
        data["interfaces"] = self.interfaces
        return data

    def __init__(self, slab_a=None, slab_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(SlabJoint, self).__init__(slab_a, slab_b, topology, a_segment_index, b_segment_index, **kwargs)
        self.interface_a = None
        self.interface_b = None

    def __repr__(self):
        return "SlabJoint({0}, {1}, {2})".format(self.slab_a, self.slab_b, JointTopology.get_name(self.topology))

    @property
    def slabs(self):
        return self.elements

    @property
    def slab_a(self):
        return self.plate_a

    @property
    def slab_b(self):
        return self.plate_b

    @property
    def geometry(self):
        return self.interface_a.polyline

    @property
    def interfaces(self):
        return [self.interface_a, self.interface_b] if self.interface_a and self.interface_b else None

    def create_interfaces(self):
        a_interface_polyline = Polyline(
            [
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[0][self.a_segment_index],
            ]
        )
        frame_a = Frame.from_points(a_interface_polyline.points[0], a_interface_polyline.points[1], a_interface_polyline.points[-2])
        if dot_vectors(frame_a.normal, Vector.from_start_end(self.b_planes[1].point, self.b_planes[0].point)) < 0:
            frame_a = Frame.from_points(a_interface_polyline.points[1], a_interface_polyline.points[0], a_interface_polyline.points[2])
        a_interface_polyline.transform(Transformation.from_frame(frame_a).inverse())    #set polyline to local frame
        frame_a.transform(self.slab_a.transformation_to_local()) #set frame to slab space
        interface_a = SlabConnectionInterface(
            a_interface_polyline,
            frame_a,
            self.a_segment_index,
            self.topology,
        )


        b_interface_polyline = Polyline(
            [
                self.a_outlines[1][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index + 1],
                self.a_outlines[0][self.a_segment_index],
                self.a_outlines[1][self.a_segment_index],
            ]
        )
        frame_b = Frame.from_points(b_interface_polyline.points[0], b_interface_polyline.points[1], b_interface_polyline.points[-2])
        if dot_vectors(frame_b.normal, Vector.from_start_end(self.b_planes[0].point, self.b_planes[1].point)) < 0:
            frame_b = Frame.from_points(b_interface_polyline.points[1], b_interface_polyline.points[0], b_interface_polyline.points[2])
        b_interface_polyline.transform(Transformation.from_frame(frame_b).inverse())    #set polyline to local frame
        frame_b.transform(self.slab_b.transformation_to_local()) #set frame to slab space
        interface_b = SlabConnectionInterface(
            b_interface_polyline,
            frame_b,
            self.b_segment_index,
            self.topology,
        )
        return interface_a, interface_b

    def add_features(self):
        # NOTE: I called this add_features to fit with joint workflow, as interface is the slab equivalent of feature.
        """Add features to the plates based on the joint."""
        if self.interface_a and self.interface_b:
            self.slab_a._features.remove(self.interface_a)
            self.slab_b._features.remove(self.interface_b)
        self.interface_a, self.interface_b = self.create_interfaces()
        self.slab_a._features.append(self.interface_a)
        self.slab_b._features.append(self.interface_b)

    def get_interface_for_plate(self, plate):
        if plate is self.slab_a:
            return self.interface_a
        elif plate is self.slab_b:
            return self.interface_b
        else:
            raise ValueError("Plate not part of this joint.")
