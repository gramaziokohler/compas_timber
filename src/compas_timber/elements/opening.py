from compas_model.elements import Element
from compas.geometry import Frame, Transformation


class OpeningType(object):
    DOOR = "door"
    WINDOW = "window"
    SERVICE = "service"
    GENERIC = "generic"


class Opening(Element):
    """An opening in a PlateGeometry, defined by one or two polylines.
    Parameters
    ----------
    outline_a : :class:`compas.geometry.Polyline`
        The first polyline defining the opening.
    outline_b : :class:`compas.geometry.Polyline`, optional
        The second polyline defining the opening. If not provided, the opening is defined by a single polyline.
    opening_type : OpeningType, optional
        The type of the opening (e.g., door, window, generic).


    Attributes
    ----------
    outline_a : :class:`compas.geometry.Polyline`
        The first polyline defining the opening.
    outline_b : :class:`compas.geometry.Polyline`, optional
        The second polyline defining the opening. If not provided, the opening is defined by a single polyline.
    opening_type : OpeningType
        The type of the opening (e.g., door, window, generic).
    """
    @property
    def __data__(self):
        return {
            "outline_a": self.outline_a,
            "outline_b": self.outline_b,
            "opening_type": self.opening_type,
        }

    def __init__(self, frame, outline_a, outline_b=None, opening_type=None, **kwargs):
        super(Opening, self).__init__(**kwargs)
        self.transformation = Transformation.from_frame(frame) if frame else Transformation()
        self.outline_a = outline_a
        self.outline_b = outline_b
        self.opening_type = opening_type

    def __repr__(self):
        return "Opening(type={})".format(self.opening_type)

    @property
    # HACK: this is a hack/workaround to allow fasteners to be used without a model
    def frame(self):
        if self.model:
            return super(Opening, self).frame
        else:
            return Frame.from_transformation(self.transformation)

    #===============================================================================
    # class methods
    #===============================================================================
