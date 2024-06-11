from compas.data import Data
from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Polyhedron


class FeatureApplicationError(Exception):
    """Raised when a feature cannot be applied to a beam geometry.

    Attributes
    ----------
    feature_geometry : :class:`~compas.geometry.Geometry`
        The geometry of the feature that could not be applied.
    beam_geometry : :class:`~compas.geometry.Geometry`
        The geometry of the beam that could not be modified.
    message : str
        The error message.

    """

    def __init__(self, feature_geometry, beam_geometry, message):
        self.feature_geometry = feature_geometry
        self.beam_geometry = beam_geometry
        self.message = message


class Feature(Data):
    """

    Attributes
    ----------
    is_joinery : bool
        Indicates whether this feature is a result of joinery. This is used when (de)serializing elements with features.
        Joinery related features should not be serialized with the element as they are re-applied by the joints.

    """

    def __init__(self, name=None, is_joinery=False):
        super(Feature, self).__init__(name)
        self._is_joiney = is_joinery

    @property
    def __data__(self):
        return {"is_joinery": self._is_joiney}

    @property
    def is_joinery(self):
        return self._is_joiney


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
        data_dict = super(CutFeature, self).__data__
        data_dict["cutting_plane"] = self.cutting_plane
        return data_dict

    def apply(self, beam_geometry):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.elements.FeatureApplicationError`
            If the cutting plane does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        try:
            return beam_geometry.trimmed(self.cutting_plane)
        except BrepTrimmingError:
            raise FeatureApplicationError(
                self.cutting_plane,
                beam_geometry,
                "The cutting plane does not intersect with beam geometry.",
            )


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
        data_dict = super(DrillFeature, self).__data__
        data_dict["line"] = self.line
        data_dict["diameter"] = self.diameter
        data_dict["length"] = self.length
        return data_dict

    def apply(self, beam_geometry):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.elements.FeatureApplicationError`
            If the drill volume is not contained in the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        print("applying drill hole feature to beam")
        plane = Plane(point=self.line.start, normal=self.line.vector)
        plane.point += plane.normal * 0.5 * self.length
        drill_volume = Cylinder(frame=Frame.from_plane(plane), radius=self.diameter / 2.0, height=self.length)

        try:
            return beam_geometry - Brep.from_cylinder(drill_volume)
        except IndexError:
            raise FeatureApplicationError(
                drill_volume,
                beam_geometry,
                "The drill volume is not contained in the beam geometry.",
            )


class MillVolume(Feature):
    """A volume to be milled out of a beam.

    Parameters
    ----------
    volume : :class:`compas.geometry.Polyhedron` | :class:`compas.datastructures.Mesh`
        The volume to be milled out of the beam.

    """

    @property
    def __data__(self):
        data_dict = super(MillVolume, self).__data__
        data_dict["volume"] = self.mesh_volume
        return data_dict

    def __init__(self, volume, **kwargs):
        super(MillVolume, self).__init__(**kwargs)
        self.mesh_volume = volume

    def apply(self, beam_geometry):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.elements.FeatureApplicationError`
            If the volume does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        # NOTE: while very similar, Polyhedron and Mesh have slightly different interface where this below is concerned
        mesh = self.mesh_volume
        if isinstance(self.mesh_volume, Polyhedron):
            mesh = self.mesh_volume.to_mesh()
        volume = Brep.from_mesh(mesh)
        try:
            return beam_geometry - volume
        except IndexError:
            raise FeatureApplicationError(
                volume,
                beam_geometry,
                "The volume does not intersect with beam geometry.",
            )


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
        data_dict = super(BrepSubtraction, self).__data__
        data_dict["volume"] = self.volume
        return data_dict

    def apply(self, beam_geometry):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.elements.FeatureApplicationError`
            If the volume does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        try:
            return beam_geometry - self.volume
        except IndexError:
            raise FeatureApplicationError(
                self.volume,
                beam_geometry,
                "The volume does not intersect with beam geometry.",
            )
