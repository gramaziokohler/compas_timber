from .joint import Joint
from .solver import JointTopology


class NullJoint(Joint):
    """A null joint is a joint that does not have any features.

    Can be used to join to beams which shouldn't join.

    Please use `NullJoint.create()` to properly create an instance of this class and associate it with an model.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    Attributes
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L  # TODO: this really supports all..

    @property
    def __data__(self):
        data_dict = {
            "beam_a_key": self.beam_a_guid,
            "beam_b_key": self.beam_b_guid,
        }
        data_dict.update(super(NullJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(**value)
        instance.beam_a_guid = value["main_beam_key"]
        instance.beam_b_guid = value["cross_beam_key"]
        return instance

    def __init__(self, beam_a=None, beam_b=None, **kwargs):
        super(NullJoint, self).__init__(**kwargs)
        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_guid = str(beam_a.guid) if beam_a else None
        self.beam_b_guid = str(beam_b.guid) if beam_b else None

    @property
    def elements(self):
        return [self.beam_a, self.beam_b]

    def restore_beams_from_keys(self, model):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.beam_a = model.beam_by_guid(self.beam_a_guid)
        self.beam_b = model.beam_by_guid(self.beam_b_guid)

    def add_features(self):
        """This joint does not add any features to the beams."""
        pass
