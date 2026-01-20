from compas_timber.connections.joint import Joint


class YSpatialLapJoint(Joint):
    def __init__(self):
        raise NotImplementedError

    @property
    def __data__(self):
        raise NotImplementedError

    @property
    def beams(self):
        raise NotImplementedError

    @property
    def elements(self):
        raise NotImplementedError

    def cross_beam_ref_side_inde(self, beam):
        raise NotImplementedError

    def main_beam_ref_side_index(self, beam):
        raise NotImplementedError

    def add_extensions(self):
        raise NotImplementedError

    def add_features(self):
        raise NotImplementedError

    def restore_beams_from_keys(self, model):
        raise NotImplementedError

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        raise NotImplementedError
