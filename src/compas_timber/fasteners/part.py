from abc import ABC
from abc import abstractmethod


class Part(ABC):
    """
    Base class for parts of a fastener.
    A part can be a fastener_plate, a screw, a doweel, etc. It has a geometry and can interact with other parts of the fastener.
    """

    @abstractmethod
    def copy(self):
        raise NotImplementedError("The copy method should be implemented in the child class.")

    @abstractmethod
    def apply_features(self, elements):
        raise NotImplementedError("The apply_features method should be implemented in the child class.")
