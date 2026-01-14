from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Optional

from compas.data import Data

if TYPE_CHECKING:
    from compas.geometry import Brep

    from compas_timber.fabrication import BTLxProcessing


class Interface(Data, ABC):
    """Base class for interfaces (abstract)."""

    def __init__(self, frame, **kwargs):
        self.frame = frame
        self.kwargs = kwargs

    @classmethod
    def __from_data__(cls, data):
        type_tag = data.get("type")
        if not type_tag:
            return
        sub = cls._registry.get(type_tag.lower())
        if not sub:
            raise ValueError(f"Unknown Interface type '{type_tag}' in data: {data}")
        ctor = getattr(sub, "__from_data__", getattr(sub, "from_data", None))
        if not ctor:
            raise TypeError(f"Registered Interface class {sub} has no from-data constructor")
        return ctor(data)

    @abstractmethod
    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        raise NotImplementedError

    @abstractmethod
    def feature(self, element, transformation_to_joint) -> Optional[BTLxProcessing]:
        raise NotImplementedError

    @abstractmethod
    def apply_features_to_elements(self, joint, transformation_to_joint):
        raise NotImplementedError
