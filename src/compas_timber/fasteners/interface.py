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
        self._logs = []

    @classmethod
    @abstractmethod
    def __from_data__(cls, data) -> Interface:
        raise NotImplementedError

    @abstractmethod
    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        raise NotImplementedError

    @abstractmethod
    def feature(self, element, transformation_to_joint) -> Optional[BTLxProcessing]:
        raise NotImplementedError

    @abstractmethod
    def apply_features_to_elements(self, joint, transformation_to_joint):
        raise NotImplementedError
