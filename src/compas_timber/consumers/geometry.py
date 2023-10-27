from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame

from compas_timber.parts import CutFeature
from compas_timber.parts import DrillFeature
from compas_timber.parts import MillVolume


def apply_drill_feature(beam_geometry, feature):
    frame = Frame.from_plane(feature.plane)
    drill_volume = Cylinder(frame, radius=feature.diameter / 2.0, height=feature.length)
    return beam_geometry - Brep.from_cylinder(drill_volume)


def apply_cut_feature(beam_geometry, feature):
    # TODO: replace with Brep.trimmed once available
    brep_copy = beam_geometry.copy()
    brep_copy.trim(feature.cutting_plane)
    return brep_copy


def appliy_mill_volume(beam_geometry, feature):
    brep = Brep.from_mesh(feature.volume)
    return beam_geometry - brep


class BeamGeometry(object):
    def __init__(self, beam, geometry):
        self.beam = beam
        self.geometry = geometry


class BrepGeometryConsumer(object):
    FEATURE_MAP = {CutFeature: apply_cut_feature, DrillFeature: apply_drill_feature, MillVolume: appliy_mill_volume}

    def __init__(self, assembly):
        self.assembly = assembly

    @property
    def result(self):
        for beam in self.assembly.beams:
            geometry = Brep.from_box(beam.blank)
            features_geo = self._apply_features(geometry, beam.features)
            yield BeamGeometry(beam, features_geo)

    def _apply_features(self, geometry, features):
        for feature in features:
            geo_op = self.FEATURE_MAP.get(type(feature), None)
            if not geo_op:
                continue
            geometry = geo_op(geometry, feature)
        return geometry
