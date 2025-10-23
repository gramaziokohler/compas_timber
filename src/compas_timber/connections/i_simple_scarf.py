from compas.tolerance import TOL

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import SimpleScarf

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence
from .utilities import beam_ref_side_incidence_with_vector


class ISimpleScarf(Joint):

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_I

    @property
    def __data__(self):
        data = super(ISimpleScarf, self).__data__
        data["main_beam_guid"] = self.main_beam_guid
        data["other_beam_guid"] = self.other_beam_guid
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        other_beam=None,
        **kwargs
    ):
        super(ISimpleScarf, self).__init__(main_beam, other_beam, **kwargs)
        self.main_beam = main_beam
        self.other_beam = other_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.other_beam_guid = kwargs.get("other_beam_guid", None) or str(other_beam.guid)

        self.features = []

    @property
    def elements(self):
        return [self.main_beam, self.other_beam]

    @property
    def add_extensions(self):
        assert self.main_beam and self.other_beam
        start_a = None
        
