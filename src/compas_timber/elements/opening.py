from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Transformation

from compas_timber.elements import TimberElement
from compas_timber.utils import intersection_segment_segment


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
        self.outline = outline
        self.beams = []
        self.joints = []
        self.detail_set = detail_set
        self.frame = frame
        self.frame_polyline = None

    def __repr__(self):
        return "Opening(type={})".format(self.__class__.__name__, self.outline)

    @classmethod
    def from_outline_and_slab(cls, outline, slab, detail_set=None):
        """Create an Opening from an outline and a slab."""

        def does_opening_intersect_polyline(opening_polyline, polyline):
            for segment_a in opening_polyline.lines:
                for segment_b in polyline.lines:
                    if intersection_segment_segment(segment_a, segment_b)[0]:
                        return True
            return False

        if does_opening_intersect_polyline(outline, slab.outline_a) or does_opening_intersect_polyline(outline, slab.outline_b):
            op = Door(outline, detail_set=detail_set)
        else:
            op = Window(outline, detail_set=detail_set)
        return op



    @property
    def obb(self):
        """Oriented bounding box of the window. used for creating framing elements around non-standard window shapes."""
        rebase = Transformation.from_frame_to_frame(self.frame, Frame.worldXY())
        box = Box.from_points(self.outline.transformed(rebase))
        rebase.invert()
        box.transform(rebase)
        return box

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

    def generate_elements(self, slab_populator):
        """Create the elements for the window."""
        return self.detail_set.generate_elements(self, slab_populator)

    def generate_joints(self, slab_populator):
        """Generate the joints for the window."""
        return self.detail_set.generate_joints(self, slab_populator)


