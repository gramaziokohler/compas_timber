from collections import OrderedDict
from importlib import import_module
from compas.data import Data


class BTLxProcess(Data):
    """Base class for BTLx processes.

    Attributes
    ----------
    ref_side_index : int
        The reference side, zero-based, index of the beam to be cut. 0-5 correspond to RS1-RS6.
    priority : int
        The priority of the process.
    process_id : int
        The process ID.
    PROCESS_NAME : str
        The name of the process.

    """

    @property
    def __data__(self):
        return {"ref_side_index": self.ref_side_index, "priority": self.priority, "process_id": self.process_id}

    def __init__(self, ref_side_index, priority=0, process_id=0):
        super(BTLxProcess, self).__init__()
        self.ref_side_index = ref_side_index
        self._priority = priority
        self._process_id = process_id

    @property
    def priority(self):
        return self._priority

    @property
    def process_id(self):
        return self._process_id

    @property
    def PROCESS_NAME(self):
        raise NotImplementedError("PROCESS_NAME must be implemented as class attribute in subclasses!")


class BTLxProcessParams(object):
    """Base class for BTLx process parameters. This creates the dictionary of key-value pairs for the process as expected by the BTLx file format.

    Parameters
    ----------
    instance : :class:`BTLxProcess`
        The instance of the process to create parameters for.

    """

    def __init__(self, instance):
        self._instance = instance

    def as_dict(self):
        """Returns the process parameters as a dictionary.

        Returns
        -------
        dict
            The process parameters as a dictionary.
        """
        result = OrderedDict()
        result["Name"] = self._instance.PROCESS_NAME
        result["Process"] = "yes"
        result["Priority"] = str(self._instance.priority)
        result["ProcessID"] = str(self._instance.process_id)
        result["ReferencePlaneID"] = str(self._instance.ref_side_index + 1)
        return result


class OrientationType(object):
    """Enum for the orientation of the cut.

    Attributes
    ----------
    START : literal("start")
        The start of the beam is cut away.
    END : literal("end")
        The end of the beam is cut away.
    """

    START = "start"
    END = "end"


class StepShapeType(object):
    """Enum for the step shape of the cut.

    Attributes
    ----------
    STEP : literal("step")
        A step shape.
    HEEL : literal("heel")
        A heel shape.
    TAPERED_HEEL : literal("taperedheel")
        A tapered heel shape.
    DOUBLE : literal("double")
        A double shape.
    """

    STEP = "step"
    HEEL = "heel"
    TAPERED_HEEL = "taperedheel"
    DOUBLE = "double"


class TenonShapeType(object):
    """Enum for the tenon shape of the cut.

    Attributes
    ----------
    AUTOMATIC : literal("automatic")
        Automatic tenon shape.
    SQUARE : literal("square")
        Square tenon shape.
    ROUND : literal("round")
        Round tenon shape.
    ROUNDED : literal("rounded")
        Rounded tenon shape.
    RADIUS : literal("radius")
        Radius tenon shape.
    """

    AUTOMATIC = "automatic"
    SQUARE = "square"
    ROUND = "round"
    ROUNDED = "rounded"
    RADIUS = "radius"


class LimitationTopType(object):
    """Enum for the top limitation of the cut.

    Attributes
    ----------
    LIMITED : literal("limited")
        Limitation to the cut.
    UNLIMITED : literal("unlimited")
        No limit to the cut.
    POCKET : literal("pocket")
        Pocket like limitation to the cut.
    """

    LIMITED = "limited"
    UNLIMITED = "unlimited"
    POCKET = "pocket"


class MachiningLimits(object):
    """Configuration class for the machining limits of the cut.

    Attributes
    ----------
    EXPECTED_KEYS : set
        The expected keys for the limits dictionary.
    face_limited_start : bool
        Limit the start face.
    face_limited_end : bool
        Limit the end face.
    face_limited_front : bool
        Limit the front face.
    face_limited_back : bool
        Limit the back face.

    Properties
    ----------
    limits : dict
        The limits dictionary with values as a boolean.
    """

    EXPECTED_KEYS = ["FaceLimitedStart", "FaceLimitedEnd", "FaceLimitedFront", "FaceLimitedBack"]

    def __init__(self):
        self.face_limited_start = True
        self.face_limited_end = True
        self.face_limited_front = True
        self.face_limited_back = True

    @property
    def limits(self):
        """Dynamically generate the limits dictionary with boolean values from instance attributes."""
        return {
            "FaceLimitedStart": self.face_limited_start,
            "FaceLimitedEnd": self.face_limited_end,
            "FaceLimitedFront": self.face_limited_front,
            "FaceLimitedBack": self.face_limited_back,
        }


class EdgePositionType(object):
    """Enum for the edge position of the cut.

    Attributes
    ----------
    REFEDGE : literal("refedge")
        Reference edge.
    OPPEDGE : literal("oppedge")
        Opposite edge.
    """

    REFEDGE = "refedge"
    OPPEDGE = "oppedge"


class BTLxFeatureDefinition(Data):
    """Container linking a BTLx Process Type and generator function to an input geometry.

    This allows delaying the actual applying of features to a downstream component.

    """

    def __init__(self, constructor, geometry, param_dict=None):
        super(BTLxFeatureDefinition, self).__init__()
        self.constructor_module = constructor.__module__
        self.constructor = constructor
        self.geometry = geometry
        self.param_dict = param_dict or {}

    @property
    def __data__(self):
        return {"constructor_module" : self.constructor.__module__, "constructor":  str(self.constructor.__qualname__), "geometry": self.geometry, "param_dict": self.param_dict}

    def __from_data__(cls, data):
        mod = import_module(data["constructor_module"])
        class_name, constructor_name = data["constructor"].split(".")
        constructor = getattr(getattr(mod, class_name), constructor_name)
        geometry = data["geometry"]
        param_dict = data["param_dict"]
        return cls(constructor, geometry, param_dict)

    def __repr__(self):
        return "{}({}, {})".format(BTLxFeatureDefinition.__class__.__name__, self.constructor, self.geometry)

    def ToString(self):
        return repr(self)

    def transformed(self, transformation):
        instance = self.__class__(self.constructor, self.geometry.transformed(transformation), self.param_dict)
        return instance

    def generate_feature(self, element):
        return self.constructor(self.geometry, element, **self.param_dict)
