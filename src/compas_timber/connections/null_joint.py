from compas.geometry import Frame
from .joint import Joint
from .solver import JointTopology


class NullJoint(Joint):
    """A null joint is a joint that does not have any features.

    Can be used to join to beams which shouldn't join.

    Please use `NullJoint.create()` to properly create an instance of this class and associate it with an assembly.

    Parameters
    ----------
    beam_a : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    beam_b : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.

    Attributes
    ----------
    beams : list(:class:`~compas_timber.parts.Beam`)
        The beams joined by this joint.
    joint_type : str
        A string representation of this joint's type.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_L  # TODO: this really supports all..

    def __init__(self, beam_a=None, beam_b=None, **kwargs):
        super(NullJoint, self).__init__(**kwargs)

        self.beam_a = beam_a
        self.beam_b = beam_b
        self.beam_a_key = beam_a.key if beam_a else None
        self.beam_b_key = beam_b.key if beam_b else None
        self.features = []

    @property
    def __data__(self):
        data_dict = {
            "beam_a_key": self.beam_a_key,
            "beam_b_key": self.beam_b_key,
        }
        data_dict.update(super(NullJoint, self).__data__)
        return data_dict

    @classmethod
    def __from_data__(cls, value):
        instance = cls(
            frame=Frame.__from_data__(value["frame"]),
            key=value["key"],
            small_beam_butts=value["small_beam_butts"],
            modify_cross=value["modify_cross"],
            reject_i=value["reject_i"],
        )
        instance.beam_a_key = value["main_beam_key"]
        instance.beam_b_key = value["cross_beam_key"]
        return instance

    @property
    def beams(self):
        return [self.beam_a, self.beam_b]

    @property
    def joint_type(self):
        return "L-Butt"


    def restore_beams_from_keys(self, assemly):
        """After de-serialization, resotres references to the main and cross beams saved in the assembly."""
        self.beam_a = assemly.find_by_key(self.beam_a_key)
        self.beam_b = assemly.find_by_key(self.beam_b_key)

    def add_features(self):
        """Adds the required extension and trimming features to both beams.

        This method is automatically called when joint is created by the call to `Joint.create()`.

        """
        pass
