from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane

from compas_timber.parts import CutFeature
from compas_timber.parts import DrillFeature
from compas_timber.parts import MillVolume


class FeatureApplicationError(Exception):
    """Raised when a feature cannot be applied to a beam geometry.

    Attributes
    ----------
    feature_geometry : :class:`compas.geometry.Geometry`
        The geometry of the feature that could not be applied.
    message : str
        The error message.

    """
    def __init__(self, feature_geometry, message):
        self.feature_geometry = feature_geometry
        self.message = message


class FeatureApplicator(object):
    """Base class for feature applicators.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Geometry`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.Feature`
        The feature to apply.

    """
    def __init__(self, beam_geometry, feature):
        self.beam_geometry = beam_geometry
        self.feature = feature

    def apply(self):
        """Apply the feature to the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Geometry`
            The resulting geometry after processing.

        """
        raise NotImplementedError


class DrillFeatureGeometry(FeatureApplicator):
    """Applies DrillFeature to beam geometry.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Brep`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.DrillFeature`
        The feature to apply.

    """
    def __init__(self, beam_geometry, feature):
        self.line = feature.line
        self.diameter = feature.diameter
        self.length = feature.length
        self.beam_geometry = beam_geometry

    def apply(self):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.consumers.FeatureApplicationError`
            If the drill volume is not contained in the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        plane = Plane(point=self.line.start, normal=self.line.vector)
        plane.point += plane.normal * 0.5 * self.length
        drill_volume = Cylinder(frame=Frame.from_plane(plane), radius=self.diameter / 2.0, height=self.length)

        try:
            return self.beam_geometry - Brep.from_cylinder(drill_volume)
        except IndexError:
            raise FeatureApplicationError(
                drill_volume,
                "Drill feature could not be applied. The drill volume is not contained in the beam geometry.",
            )


class CutFeatureGeometry(FeatureApplicator):
    """Applies CutFeature to beam geometry.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Brep`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.CutFeature`
        The feature to apply.

    """
    def __init__(self, beam_geometry, feature):
        self.cutting_plane = feature.cutting_plane
        self.beam_geometry = beam_geometry

    def apply(self):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.consumers.FeatureApplicationError`
            If the cutting plane does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        try:
            results = self.beam_geometry.trimmed(self.cutting_plane)
            return results[0]
        except IndexError:
            raise FeatureApplicationError(
                self.cutting_plane,
                "Cut feature could not be applied. The cutting plane does not intersect with beam geometry.",
            )


class MillVolumeGeometry(object):
    """Applies MillVolume to beam geometry.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Brep`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.MillVolume`
        The feature to apply.

    """
    def __init__(self, beam_geometry, feature):
        self.volume = Brep.from_mesh(feature.volume)
        self.beam_geometry = beam_geometry

    def apply(self):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.consumers.FeatureApplicationError`
            If the volume does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        try:
            return self.beam_geometry - self.volume
        except IndexError:
            raise FeatureApplicationError(
                self.volume,
                "Mill volume could not be applied. The volume does not intersect with beam geometry.",
            )


class BeamGeometry(object):
    """A data class containing the result of applying features to a beam.

    Parameters
    ----------
    beam : :class:`~compas_timber.beam.Beam`
        The beam.
    geometry : :class:`~compas.geometry.Geometry`
        The resulting geometry after processing.
    debug_info : :class:`~compas_timber.consumers.FeatureApplicationError`, optional
        Debug information if an error occurred during processing.

    """
    def __init__(self, beam, geometry, debug_info=None):
        self.beam = beam
        self.geometry = geometry
        self.debug_info = debug_info


class BrepGeometryConsumer(object):
    """A consumer that applies features to beams and yields the resulting geometry.

    Parameters
    ----------
    assembly : :class:`~compas_timber.assembly.Assembly`
        The assembly to consume.

    Attributes
    ----------
    FEATURE_MAP : dict(:class:`~compas_timber.parts.Feature`, :class:`~compas_timber.consumers.FeatureApplicator`.)
        A mapping of feature types to feature applicators.
    result : generator(:class:`~compas_timber.consumers.BeamGeometry`)
        The resulting geometry after processing.

    """
    FEATURE_MAP = {CutFeature: CutFeatureGeometry, DrillFeature: DrillFeatureGeometry, MillVolume: MillVolumeGeometry}

    def __init__(self, assembly):
        self.assembly = assembly

    @property
    def result(self):
        for beam in self.assembly.beams:
            geometry = Brep.from_box(beam.blank)
            debug_info = None
            try:
                resulting_geometry = self._apply_features(geometry, beam.features)
            except FeatureApplicationError as error:
                resulting_geometry = geometry
                debug_info = error
            yield BeamGeometry(beam, resulting_geometry, debug_info)

    def _apply_features(self, geometry, features):
        for feature in features:
            cls = self.FEATURE_MAP.get(type(feature), None)
            feature_applicator = cls(geometry, feature)
            if not feature_applicator:
                continue
            geometry = feature_applicator.apply()
        return geometry
