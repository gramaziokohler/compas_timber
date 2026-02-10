from abc import ABC
from abc import abstractmethod

from compas.geometry import Frame

from compas_timber.fasteners.fastener import Fastener


class JointFastener(ABC):
    def __init__(self, base_fastener: Fastener, **kwargs):
        super().__init__(**kwargs)
        self.base_fastener = base_fastener
        self._fasteners = []

        self.place_fasteners_instances()

    @property
    def generated_elements(self):
        return self.fasteners

    @property
    def fasteners(self) -> list[Fastener]:
        """
        Returns all fasteners of the joint.

        Returns
        -------
        list[:class:`compas_timber.fasteners.Fastener`]
            A list of all fasteners in the joint.
        """
        fasteners = []
        for fastener in self._fasteners:
            fasteners.extend(fastener.find_all_nested_sub_fasteners())
        return fasteners

    def compute_fasteners_interactions(self) -> list[tuple]:
        """
        Computes the interactions between fasteners and beams and fastener and sub-fastnert participating to the joint.
        """
        interactions = []
        if not hasattr(self, "beams"):
            raise AttributeError("The attribute 'beams' does not exist on this object.")

        # beam ---- fastener ---- beam
        for fastener in self._fasteners:
            for beam in self.beams:  # type: ignore
                interactions.append((beam, fastener))
            # fastener ---- sub_fastener ---- sub-fastener
            interactions.extend(fastener.compute_sub_fasteners_interactions())
        return interactions

    @abstractmethod
    def place_fasteners_instances(self):
        raise NotImplementedError("Subclasses of JointFastener must implement the place_fasteners_instances method.")

    @abstractmethod
    def compute_fastener_target_frames(self) -> list[Frame]:
        raise NotImplementedError("Subclasses of JointFastener must implement the compute_fastener_target_frames method.")
