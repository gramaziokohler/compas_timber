from compas.geometry import Frame
from compas.geometry import Brep
from compas_future.datastructures import GeometricFeature
from compas_future.datastructures import ParametricFeature


def _trim_brep_with_frame(brep, frame):
    """Trim the given Brep using the provided trimming frame."""
    brep.trim(frame)


def _boolean_subtract_breps(brep_a, brep_b):
    """Returns the result of the boolean subtraction of two Breps."""
    return brep_a - brep_b


class BeamTrimmingFeature(GeometricFeature):
    
    OPERATIONS = {Brep: _trim_brep_with_frame}
    
    def __init__(self, trimming_plane):
        super(BeamTrimmingFeature, self).__init__()
        self._geometry = trimming_plane

    @property
    def data(self):
        return {
            "trimming_frame": self._geometry.data    
        }

    @data.setter
    def data(self, value):
        self._geometry = Frame.from_data(value["trimming_frame"])

    def apply(self, part):
        part_geometry = part.get_geometry(with_features=True)
        if not isinstance(part_geometry, Brep):
            raise ValueError("Brep feature {} cannot be applied to part with non Brep geometry {}".format(self, part))
        g_copy = part_geometry.copy()
        operation = self.OPERATIONS[Brep]
        operation(g_copy, self._geometry)
        return g_copy

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self._geometry))


class BeamBooleanSubtraction(GeometricFeature):

    OPERATIONS = {Brep: _boolean_subtract_breps}
    
    def __init__(self, brep):
        super(BeamBooleanSubtraction, self).__init__()
        self._geometry = brep

    def __deepcopy__(self, memo=None):
        return self.copy()
        
    @property
    def data(self):
        raise NotImplementedError

    @data.setter
    def data(self, value):
        raise NotImplementedError
    
    def copy(self, cls=None):
        return BeamBooleanSubtraction(self._geometry.copy())

    def apply(self, part):
        part_geometry = part.get_geometry(with_features=True)
        if not isinstance(part_geometry, Brep):
            raise ValueError("Brep feature {} cannot be applied to part with non Brep geometry {}".format(self, part))
        operation = self.OPERATIONS[Brep]
        return operation(part_geometry, self._geometry)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, repr(self._geometry))


class BeamExtensionFeature(ParametricFeature):
    def __init__(self, extend_start_by, extend_end_by):
        super(BeamExtensionFeature, self).__init__()
        self._extend_start = extend_start_by
        self._extend_end = extend_end_by
    
    @property
    def data(self):
        return {
            "start": self._extend_start,
            "end": self._extend_end
        }

    @data.setter
    def data(self, value):
        self._extend_start = value["start"]
        self._extend_end = value["end"]

    def apply(self, part):
        part.extend_ends(self._extend_start, self._extend_end)

    def restore(self, part):
        part.extend_ends(-self._extend_start, -self._extend_end)

    def accumulate(self, feature):
        if not isinstance(feature, self.__class__):
            return False
        self._extend_start = max(feature._extend_start)
        self._extend_end = max(feature._extend_end)
        return True

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self._extend_start, self._extend_end)