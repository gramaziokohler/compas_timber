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
    from compas_timber.fasteners.interface import Interface


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

    def __init__(self, frame: Frame, interfaces: Optional[list["Interface"]] = None, **kwargs):
        # super(Fastener, self).__init__(transformation=Transformation.from_frame(frame) if frame else Transformation(), **kwargs)
        super(Fastener, self).__init__(transformation=Transformation.from_frame_to_frame(frame, frame) if frame else Transformation(), **kwargs)
        self.frame = frame
        self.target_frame = frame
        self._sub_fasteners = []
        self.attributes = {}
        self.attributes.update(kwargs)
        self.debug_info = []

    @property
    def __data__(self) -> dict:
        return {"transformation": self.transformation, "interfaces": self.interfaces, "attributes": self.attributes}

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

    @property
    def sub_fasteners(self):
        return self._sub_fasteners

    @frame.setter
    def frame(self, frame) -> None:
        self._frame = frame

    def find_all_nested_sub_fasteners(self):
        sub_fasteners = []
        for sub_fastener in self.sub_fasteners:
            sub_fasteners.extend(sub_fastener.find_all_nested_sub_fasteners())
        else:
            sub_fasteners.append(self)
        return sub_fasteners

    # def place_instances(self, joint: Joint) -> None:
    #     """Adds the fasteners to the joint.

    #     This method is automatically called when joint is created by the call to `Joint.create()`.

    #     This methoud shoudl be called bz Joint.apply() and not Joint.create()
    #     Joint.apply() adds the features to the Tis
    #     """
    #     frames = joint.fastener_target_frames

    #     # add the fasteners to the joint
    #     for frame in frames:
    #         joint_fastener = self.copy()
    #         joint_fastener.target_frame = Frame(frame.point, frame.xaxis, frame.yaxis)
    #         joint.fasteners.append(joint_fastener)

    #     # add the subfastener to the joint
    #     for sub_fastener in self.sub_fasteners:
    #         sub_fastener.place_instances(joint)

    def compute_instance(self, target_frame):
        joint_fastener = self.copy()
        joint_fastener.target_frame = target_frame.copy()

        for sub_fastener in self.sub_fasteners:
            sub_target_frame = sub_fastener.frame.transformed(joint_fastener.to_joint_transformation)
            sub_instance = sub_fastener.compute_instance(sub_target_frame)
            joint_fastener.sub_fasteners.append(sub_instance)

        return joint_fastener

    def compute_sub_fasteners_interactions(self):
        interactions = []
        for sub_fastener in self.sub_fasteners:
            interaction = (self, sub_fastener)
            interactions.append(interaction)
            interactions.extend(sub_fastener.compute_sub_fasteners_interactions())
        return interactions

    @abstractmethod
    def apply_processings(self, joint: Joint) -> None:
        """
        If the fastener contains intefaces, the interfaces are applied to the elements of the joint.

        Parameters
        ----------
        joint: :class:`compas_timber.connections.Joint`
            The joint to wiche the fastener is to be applied.

        """
        raise NotImplementedError

    def add_interface(self, interface: Interface) -> None:
        """
        Adds an interface to the fastener

        Parameters
        ----------
        interface : :class:`compas_timber.fasteners.Interface`
            The interface to add to the fastener.
        """
        self.interfaces.append(interface)

    @property
    def to_joint_transformation(self) -> Transformation:
        return Transformation.from_frame_to_frame(self.frame, self.target_frame)

    # ---- GEOMETRY -----
    @property
    def geometry(self) -> Brep:
        """The geometry of the element in the model's global coordinates."""
        if self._geometry is None:
            self._geometry = self.compute_modelgeometry()
        return self._geometry

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
