from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Transformation

from compas_timber.elements import TimberElement


class Opening(TimberElement):
    """Represents an opening in a slab, such as a window or door.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the opening.
    detail_set : :class:`compas_timber.design.OpeningDetailBase`
        The detail set associated with the opening.

    Attributes
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the opening.
    detail_set : :class:`compas_timber.design.OpeningDetailBase`
        The detail set associated with the opening.
    frame : :class:`compas.geometry.Frame`
        The frame of the opening, used for positioning and orientation.
    beams : list[:class:`compas_timber.elements.Beam`]
        The beams associated with the opening.
    joints : list[:class:`compas_timber.elements.Joint`]
        The joints associated with the opening.
    frame_polyline : :class:`compas.geometry.Polyline`
        The polyline representation of the opening's frame, used for beam generation.
    obb : :class:`compas.geometry.Box`
        The oriented bounding box of the opening, used for framing elements around non-standard shapes.
    jack_studs : list[:class:`compas_timber.elements.Beam`]
        The jack studs associated with the opening.
    king_studs : list[:class:`compas_timber.elements.Beam`]
        The king studs associated with the opening.
    sill : :class:`compas_timber.elements.Beam`
        The sill beam associated with the opening.
    header : :class:`compas_timber.elements.Beam`
        The header beam associated with the opening.
    """

    @property
    def __data__(self):
        return {
            "outline": self.outline,
            "detail_set": self.detail_set,
        }

    def __init__(self, outline, detail_set=None, frame=None):
        self.frame = frame or Frame.from_points(outline[0], outline[1], outline[-2])
        self.local_outline = outline.transformed(Transformation.from_frame_to_frame(self.frame, Frame.worldXY()))
        self.beams = []
        self.joints = []
        self.detail_set = detail_set
        self.frame_polyline = None
        self.joint_tuples = []
        self.name = "opening with outline {}".format(self.outline)
    def __repr__(self):
        return "Opening(type={})".format(
            self.__class__.__name__,
        )

    @property
    def is_opening(self):
        return True

    @property
    def is_group_element(self):
        return True

    @property
    def obb(self):
        """Oriented bounding box of the window. used for creating framing elements around non-standard window shapes."""
        box = Box.from_points(self.local_outline)
        return box.transformed(self.transformation)

    @property
    def jack_studs(self):
        return [beam for beam in self.beams if beam.attributes["category"] == "jack_stud"]

    @property
    def king_studs(self):
        return [beam for beam in self.beams if beam.attributes["category"] == "king_stud"]

    @property
    def sill(self):
        for beam in self.beams:
            if beam.attributes["category"] == "sill":
                return beam
        return None

    @property
    def header(self):
        for beam in self.beams:
            if beam.attributes["category"] == "header":
                return beam
        return None

    @property
    def transformation(self):
        return Transformation.from_frame(self.frame)

    @property
    def outline(self):
        return self.local_outline.transformed(self.transformation)
