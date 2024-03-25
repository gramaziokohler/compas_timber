from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane

from compas_timber.parts import CutFeature
from compas_timber.parts import DrillFeature
from compas_timber.parts import MillVolume
from compas_timber.parts import BrepSubtraction


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


class FeatureApplicator(object):
    """Base class for feature applicators."""

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
        super(DrillFeatureGeometry, self).__init__()
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
                self.beam_geometry,
                "The drill volume is not contained in the beam geometry.",
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
        super(CutFeatureGeometry, self).__init__()
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
            results = results[0] if isinstance(results, list) else results
            return results
        except IndexError:
            raise FeatureApplicationError(
                self.cutting_plane,
                self.beam_geometry,
                "The cutting plane does not intersect with beam geometry.",
            )


class MillVolumeGeometry(FeatureApplicator):
    """Applies MillVolume to beam geometry.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Brep`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.MillVolume`
        The feature to apply.

    """

    def __init__(self, beam_geometry, feature):
        super(MillVolumeGeometry, self).__init__()
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
                self.beam_geometry,
                "The volume does not intersect with beam geometry.",
            )


class BrepSubtractionGeometry(FeatureApplicator):
    """Applies BrepSubtraction to beam geometry.

    Parameters
    ----------
    beam_geometry : :class:`compas.geometry.Brep`
        The geometry of the beam.
    feature : :class:`compas_timber.parts.BrepSubtraction`
        The feature to apply.

    """

    def __init__(self, beam_geometry, feature):
        super(BrepSubtractionGeometry, self).__init__()
        self.volume = feature.volume
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
                self.beam_geometry,
                "The volume does not intersect with beam geometry.",
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

    FEATURE_MAP = {
        CutFeature: CutFeatureGeometry,
        DrillFeature: DrillFeatureGeometry,
        MillVolume: MillVolumeGeometry,
        BrepSubtraction: BrepSubtractionGeometry,
    }

    def __init__(self, assembly):
        self.assembly = assembly

    @property
    def result(self):
        for beam in self.assembly.beams:
            geometry = Brep.from_box(beam.blank)
            debug_info = None
            resulting_geometry, debug_info = self._apply_features(geometry, beam.features)
            yield BeamGeometry(beam, resulting_geometry, debug_info)

    def _apply_features(self, geometry, features):
        debug_info = []
        for feature in sorted(features, key=lambda f: f.PRIORITY):
            cls = self.FEATURE_MAP.get(type(feature), None)
            if not cls:
                raise ValueError("No applicator found for feature type: {}".format(type(feature)))
            feature_applicator = cls(geometry, feature)

            try:
                geometry = feature_applicator.apply()
            except FeatureApplicationError as error:
                debug_info.append(error)

        return geometry, debug_info
