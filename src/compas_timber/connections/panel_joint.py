from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import dot_vectors

from compas_timber.panel_features import PanelConnectionInterface

from .joint import JointTopology
from .plate_joint import PlateJoint


class PanelJoint(PlateJoint):
    """Models a plate to plate interaction.

    Parameters
    ----------
    panel_a : :class:`compas_timber.elements.Panel`
        The first plate.
    panel_b : :class:`compas_timber.elements.Panel`
        The second plate.
    topology : literal(JointTopology)
        The topology in which the plates are connected.
    a_segment_index : int
        The index of the segment in panel_a's outline where the plates are connected.
    b_segment_index : int
        The index of the segment in panel_b's outline where the plates are connected.
    **kwargs : dict, optional
        Additional keyword arguments to pass to the parent class.

    Attributes
    ----------
    panel_a : :class:`compas_timber.elements.Panel`
        The first plate.
    panel_b : :class:`compas_timber.elements.Panel`
        The second plate.
    panels : tuple of :class:`compas_timber.elements.Panel`
        The panels that are connected.
    interface_a : :class:`compas.geometry.PlanarSurface`
        The interface surface of panel_a where it meets panel_b.
    interface_b : :class:`compas.geometry.PlanarSurface`
        The interface surface of panel_b where it meets panel_a.

    """

    @property
    def __data__(self):
        data = super(PanelJoint, self).__data__
        data["interfaces"] = self.interfaces
        return data

    def __init__(self, panel_a=None, panel_b=None, topology=None, a_segment_index=None, b_segment_index=None, **kwargs):
        super(PanelJoint, self).__init__(panel_a, panel_b, topology, a_segment_index, b_segment_index, **kwargs)
        self.interface_a = None
        self.interface_b = None

    def __repr__(self):
        return "PanelJoint({0}, {1}, {2})".format(self.panel_a, self.panel_b, JointTopology.get_name(self.topology))

    @property
    def panels(self):
        return self.elements

    @property
    def panel_a(self):
        return self.plate_a

    @property
    def panel_b(self):
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
        interface_a = PanelConnectionInterface(
            a_interface_polyline.transformed(Transformation.from_frame(frame_a).inverse()),
            frame_a.transformed(self.panel_a.modeltransformation.inverse()),
            self.a_segment_index,
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
        interface_b = PanelConnectionInterface(
            b_interface_polyline.transformed(Transformation.from_frame(frame_b).inverse()),
            frame_b.transformed(self.panel_b.modeltransformation.inverse()),
            self.b_segment_index,
        )
        return interface_a, interface_b

    def add_features(self):
        # NOTE: I called this add_features to fit with joint workflow, as interface is the panel equivalent of a joint-generated feature.
        """Add features to the plates based on the joint."""
        if self.interface_a and self.interface_b:
            self.panel_a.remove_features(self.interface_a)
            self.panel_b.remove_features(self.interface_b)
        self.interface_a, self.interface_b = self.create_interfaces()
        self.panel_a.add_feature(self.interface_a)
        self.panel_b.add_feature(self.interface_b)

    def get_interface_for_plate(self, plate):
        if plate is self.panel_a:
            return self.interface_a
        elif plate is self.panel_b:
            return self.interface_b
        else:
            raise ValueError("Plate not part of this joint.")
