from abc import ABC
from abc import abstractmethod
from uuid import uuid4


class Part(ABC):
    """
    Base class for a part of a fastener.
    A part can be a plate, a rod, a node, or any other component that can be used to create a fastener.

    This is an abstract class and should be inherited by specific part classes.
    It contains a unique identifier (guid) that can be used to track the part across different fasteners and interactions.


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
