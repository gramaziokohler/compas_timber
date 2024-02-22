from compas.data import Data


class Feature(Data):
    """

    Attirbutes
    ----------
    is_joinery : bool
        Indicates whether this feature is a result of joinery.

    """

    def __init__(self, name=None, is_joinery=False):
        super(Feature, self).__init__(name)
        self._is_joiney = is_joinery

    @property
    def is_joinery(self):
        return self._is_joiney

    @property
    def __data__(self):
        return {"is_joinery": self._is_joiney}


class CutFeature(Feature):
    """Indicates a cut to be made on a beam.

    Parameters
    ----------
    cutting_plane : :class:`compas.geometry.Frame`
        The plane to cut the beam with.

    """

    def __init__(self, cutting_plane, **kwargs):
        super(CutFeature, self).__init__(**kwargs)
        self.cutting_plane = cutting_plane

    @property
    def __data__(self):
        data_dict = {"cutting_plane": self.cutting_plane}
        data_dict.update(super(CutFeature, self).__data__)
        return data_dict


class DrillFeature(Feature):
    """Parametric drill hole to be made on a beam.

    Parameters
    ----------
    plane : :class:`compas.geometry.Plane`
        The plane on which the drill hole is to be made.
    diameter : float
        The diameter of the drill hole.
    length : float
        The length (depth?) of the drill hole.

    """

    def __init__(self, line, diameter, length, **kwargs):
        super(DrillFeature, self).__init__(**kwargs)
        self.line = line
        self.diameter = diameter
        self.length = length

    @property
    def __data__(self):
        data_dict = {"line": self.line, "diameter": self.diameter, "length": self.length}
        data_dict.update(super(DrillFeature, self).__data__)
        return data_dict


class MillVolume(Feature):
    """A volume to be milled out of a beam.

    Parameters
    ----------
    volume : :class:`compas.geometry.Polyhedron` | :class:`compas.datastructures.Mesh`
        The volume to be milled out of the beam.

    """

    def __init__(self, volume, **kwargs):
        super(MillVolume, self).__init__(**kwargs)
        self.volume = volume

    @property
    def __data__(self):
        data_dict = {"volume": self.volume}
        data_dict.update(super(MillVolume, self).__data__)
        return data_dict


class BrepSubtraction(Feature):
    """Generic volume subtraction from a beam.

    Parameters
    ----------
    volume : :class:`compas.geometry.Brep`
        The volume to be subtracted from the beam.

    """

    def __init__(self, volume, **kwargs):
        super(BrepSubtraction, self).__init__(**kwargs)
        self.volume = volume

    @property
    def __data__(self):
        data_dict = {"volume": self.volume}
        data_dict.update(super(BrepSubtraction, self).__data__)
        return data_dict
