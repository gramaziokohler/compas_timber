from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Transformation

from compas_timber.elements import TimberElement
from compas_timber.utils import intersection_segment_segment


class Opening(TimberElement):
    """Represents an opening in a slab, such as a window or door.

    Parameters
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The outline of the opening.
    opening_type : str
        The type of the opening (e.g., "window", "door").

    Attributes
    ----------
    polyline : :class:`compas.geometry.Polyline`
        The outline of the opening.
    opening_type : str
        The type of the opening.
    """

    @property
    def __data__(self):
        return {
            "outline": self.outline,
        }

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


class Window(object):
    """

    # TODO: is this an Element maybe?

    A window object for the SurfaceAssembly.

    Parameters
    ----------
    outline : :class:`compas.geometry.Polyline` TODO: define with 2 polylines(inside and outside)
        The outline of the window.
    parent : :class:`compas_timber.model.SurfaceAssembly`
        The parent of the window.

    Attributes
    ----------
    outline : :class:`compas.geometry.Polyline`
        The outline of the window.
    parent : :class:`compas_timber.model.SurfaceAssembly`
        The parent of the window.
    stud_direction : :class:`compas.geometry.Vector`
        The z axis of the parent.
    normal : :class:`compas.geometry.Vector`
        The normal of the parent.
    beam_dimensions : dict
        The beam dimensions of the parent.
    beam_definions : list of :class:`compas_timber.model.SurfaceAssembly.BeamDefinition`
        The beam_definions of the window.
    length : float
        The length of the window.
    height : float
        The height of the window.
    frame : :class:`compas.geometry.Frame`
        The frame of the window.
    """

    # TODO: consider make opening generate an interface. it shares a lot of characteristics, e.g. it adds beams, joints, etc.

    def __init__(self, outline, detail_set=None, frame=None):
        self.outline = outline
        self.beams = []
        self.joints = []
        self.detail_set = detail_set
        self.frame = frame
        self.frame_polyline = None

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


class Door(Window):
    """TODO: revise when we know where this is going, maybe no need for classes here beyond Opening"""

    def __init__(self, outline, detail_set=None):
        super(Door, self).__init__(outline, detail_set=detail_set)
