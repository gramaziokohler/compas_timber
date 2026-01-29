from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Optional
from typing import Union

from compas.geometry import Frame
from compas.geometry import Transformation
from compas_model.elements import Element

if TYPE_CHECKING:
    from compas.datstructure import Mesh
    from compas.geometry import Brep
    from compas.geometry import Transformation

    from compas_timber.connections.joint import Joint


class Fastener(Element, ABC):
    """
    A class to represent timber fasteners (screws, dowels, brackets).

    This is an abstract class.

    Parameters
    ----------
    shape : :class:`~compas.geometry.Geometry`, optional
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`, optional
        The frame of the fastener in parent space.
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    shape : :class:`~compas.geometry.Geometry`
        The geometry of the fastener.
    frame : :class:`~compas.geometry.Frame`
        The frame of the fastener in parent space.
    interfaces : list
        A list of interfaces associated with this fastener.
    attributes : dict
        Dictionary of attributes for this fastener.
    debug_info : list
        A list of debug information.
    is_fastener : bool
        Always True for fasteners.
    key : int or None
        The graph node key of this fastener.

    """

    def __init__(self, frame: Frame, **kwargs):
        # super(Fastener, self).__init__(transformation=Transformation.from_frame(frame) if frame else Transformation(), **kwargs)
        super(Fastener, self).__init__(transformation=Transformation.from_frame_to_frame(frame, frame) if frame else Transformation(), **kwargs)
        self._frame = frame
        self.target_frame = frame
        self._sub_fasteners = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    @property
    def __data__(self) -> dict:
        return {
            "transformation": self.transformation,
            "attributes": self.attributes,
            "frame": self.frame.__data__,
            "target_frame": self.target_frame.__data__,
            "sub_fasteners": [sub_fastener.__data__ for sub_fastener in self._sub_fasteners],
        }

    @classmethod
    def __from_data__(cls, data: dict) -> Fastener:
        frame_data = data["frame"]
        frame = Frame(frame_data["point"], frame_data["xaxis"], frame_data["yaxis"])
        target_frame_data = data["target_frame"]
        target_frame = Frame(target_frame_data["point"], target_frame_data["xaxis"], target_frame_data["yaxis"])
        sub_fasteners = [Fastener.__from_data__(data) for data in data["sub_fasteners"]]
        fastener = cls(frame=frame)
        fastener.transformation = data["transformation"]
        fastener.target_frame = target_frame
        fastener.attributes = data["attributes"]
        for sub_fastener in sub_fasteners:
            fastener.add_sub_fastener(sub_fastener)
        return fastener

    def __repr__(self) -> str:
        return "Fastener(frame={!r}, name={})".format(Frame.from_transformation(self.transformation), self.name)

    def __str__(self) -> str:
        return "<Fastener {}>".format(self.name)

    @property
    def is_fastener(self) -> bool:
        return True

    @property
    def key(self) -> Optional[int]:
        return self.graphnode

    @property
    def frame(self) -> Frame:
        return self._frame

    @frame.setter
    def frame(self, frame) -> None:
        self._frame = frame

    @property
    def sub_fasteners(self) -> list[Fastener]:
        """
        Returns the direct sub-fasteners of this fastener.

        Returns
        -------
        list[:class:`compas_timber.fasteners.Fastener`]
            A list of direct sub_fasteners.
        """
        return self._sub_fasteners

    @property
    def geometry(self) -> Brep:
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

    @property
    def to_joint_transformation(self) -> Transformation:
        """
        Computes the transformation from the fastener's local frame to the target frame in the joint.
        """
        return Transformation.from_frame_to_frame(self.frame, self.target_frame)

    def compute_joint_instance(self, target_frame: Frame) -> Fastener:
        """
        Computes an instance of this fastener for a specific target frame in a joint.

        Parameters
        ----------
        target_frame : :class:`compas.geometry.Frame`
            The target frame in the joint where the fastener instance is to be computed.

        Returns
        -------
        :class:`compas_timber.fasteners.Fastener`
            The computed fastener instance for the specified target frame.
        """
        joint_fastener = self.copy()
        joint_fastener.target_frame = target_frame.copy()

        for sub_fastener in self.sub_fasteners:
            sub_target_frame = sub_fastener.frame.transformed(joint_fastener.to_joint_transformation)
            sub_instance = sub_fastener.compute_joint_instance(sub_target_frame)
            joint_fastener.sub_fasteners.append(sub_instance)

        return joint_fastener

    @abstractmethod
    def apply_processings(self, joint: Joint) -> None:
        """
        Applies BTLx processings to the elements of the joint base on this fastener.

        Parameters
        ----------
        joint: :class:`compas_timber.connections.Joint`
            The joint to wiche the fastener is to be applied.

        """
        raise NotImplementedError

    # ---- SUB FASTENERS -----

    def add_sub_fastener(self, sub_fastener: Fastener) -> None:
        """
        Adds a sub-fastener to this fastener.

        Parameters
        ----------
        sub_fastener : :class:`compas_timber.fasteners.Fastener`
            The sub-fastener to be added.
        """
        self._sub_fasteners.append(sub_fastener)

    def find_all_nested_sub_fasteners(self) -> list[Fastener]:
        """
        Returna a list of all sub_fastener and nested sub_fasteners of this fastener.\

        Returns
        -------
        list[:class:`compas_timber.fasteners.Fastener`]
            A list of all sub_fasteners and nested sub_fasteners.
        """
        sub_fasteners = []
        for sub_fastener in self.sub_fasteners:
            sub_fasteners.extend(sub_fastener.find_all_nested_sub_fasteners())
        else:
            sub_fasteners.append(self)
        return sub_fasteners

    def compute_sub_fasteners_interactions(self) -> list[tuple[Fastener, Fastener]]:
        """
        Computes the interactions between this fastener and its sub-fasteners recursively.
        This method returns a list of tuples, each containing a pair of fasteners that interact, needed to build the interaction graph of the `TimberModel`.

        Returns
        -------
        list[tuple(:class:`compas_timber.fasteners.Fastener`, :class:`compas_timber.fasteners.Fastener`)]
            A list of tuples representing the interactions between fasteners.
        """

        interactions = []
        for sub_fastener in self.sub_fasteners:
            interaction = (self, sub_fastener)
            interactions.append(interaction)
            interactions.extend(sub_fastener.compute_sub_fasteners_interactions())
        return interactions

    # ---- GEOMETRY -----

    @abstractmethod
    def compute_elementgeometry(self, include_interfaces=True) -> Brep:
        """
        Compute the geoemtry of the element in local coordinates.

        Parameters
        ----------
        include_interfaces: bool, optional
            If True, the geometry of the interfaces are applied to the creation of the geometry. Default is True.
        """
        raise NotImplementedError

    def compute_modeltransformation(self) -> Optional[Transformation]:
        """Same as parent but handles standalone elements."""
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self) -> Union[Brep, Mesh]:
        """Computes the geometry of the element in model coordinates and taking into account the effect of interations with connected elements.

        Returns:
        -------
        :class:`~compas.geometry.Geometry.Brep`
        """
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()

    def transformation_to_local(self) -> Transformation:
        """Compute the transformation to local coordinates of this element
        based on its position in the spatial hierarchy of the model.

        Returns
        -------
        :class:`compas.geometry.Transformation`

        """
        return self.modeltransformation.inverted()
