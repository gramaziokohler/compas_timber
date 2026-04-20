from abc import ABC
from abc import abstractmethod
from uuid import uuid4


class Part(ABC):
    """
    Base class for parts of a fastener.
    A part can be a fastener_plate, a screw, a doweel, etc. It has a geometry and can interact with other parts of the fastener.
    """

    def __init__(self):
        self.guid = str(uuid4())

    @property
    def __data__(self):
        data = {}
        data["guid"] = self.guid
        return data

    @classmethod
    def from_data(cls, data):
        part_type = data.get("type")
        if not part_type:
            raise ValueError("Data must contain a 'type' key to determine the part class.")

        for subclass in cls.__subclasses__():
            if subclass.__name__ == part_type:
                return subclass.from_data(data)

    @abstractmethod
    def copy(self):
        raise NotImplementedError("The copy method should be implemented in the child class.")

    @abstractmethod
    def apply_features(self, elements):
        raise NotImplementedError("The apply_features method should be implemented in the child class.")
