from __future__ import annotations

from typing import TYPE_CHECKING

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line

from compas_timber.elements import TimberElement
from compas_timber.fabrication import Drilling
from compas_timber.fasteners.interface import Interface

if TYPE_CHECKING:
    from compas_timber.fabrication import BTLxProcessing


class HoleInterface(Interface):
    """
    Represents a hole interface for a timber element and a Fastener.

    Parameters
    ----------
    frame : :class:`compas.geometry.Frame`
        Frame of reference the define the position of the hole. Its zaxis defines the direction of the hole.
    depth : float
        The depth of the hole interface.
    diameter : float
        The diameter of the hole interface.

    Attributes:
        frame (Frame): The frame of the hole interface.
        depth (float): The depth of the hole interface.
        diameter (float): The diameter of the hole interface.
        element (:class:`compas_timber.elements.TimberElement`): The timber element to which the interface is applied.
    """

    def __init__(self, frame: Frame, depth: float, diameter: float, **kwargs):
        super().__init__(frame, **kwargs)
        self.frame = frame
        self.depth = depth
        self.diameter = diameter

    @property
    def __data__(self):
        return {"type": "HoleInterface", "frame": self.frame.__data__, "depth": self.depth, "diameter": self.diameter}

    @classmethod
    def __from_data__(cls, data):
        interface = cls(frame=Frame(data["frame"]["point"], data["frame"]["xaxis"], data["frame"]["yaxis"]), depth=data["depth"], diameter=data["diameter"])
        return interface

    @property
    def shape(self):
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder.frame.point += self.depth / 2 * self.frame.zaxis
        cylinder = Brep.from_cylinder(cylinder)
        return cylinder

    def apply_to_fastener_geometry(self, fastener_geometry) -> Brep:
        """
        Adds a hole to the geometry of the fastener.

        This method is called by `Fastener.compute_elementgeometry()`

        Parameters
        ----------
        fastener_geometry : :class:`compas.geometry.Brep`
            The geometry of the Fastener
        """
        cylinder = Cylinder(radius=self.diameter * 0.5, height=self.depth, frame=self.frame)
        cylinder = Brep.from_cylinder(cylinder)
        fastener_geometry -= cylinder
        return fastener_geometry

    def feature(self, element, transformation_to_joint) -> list[BTLxProcessing]:
        """
        Creates a feature for the specified element.

        Parameters
        ----------
        element : :class:`compas_timber.elements.TimberElement'
            The element to which the feature is applied.
        transformation_to_joint : Transformation
            The transformation from the global coordinate system to the joint's local coordinate system.

        Returns
        -------
        Optional[BTLxProcessing]
            The feature created for the element.
        """
        start_point = self.frame.point + self.frame.zaxis * 0.01
        end_point = self.frame.point + self.depth * -self.frame.zaxis
        line = Line(start_point, end_point)
        line.transform(transformation_to_joint)

        try:
            drilling = Drilling.from_line_and_element(line=line, element=element, diameter=self.diameter)
            return [drilling]
            self._logs.append(f"Drilling feature in HoleInterface succeded: {drilling}")
        except Exception as e:
            self._logs.append(f"Drilling feature in HoleInterface not succeded: {e}")
            return []

    def apply_features_to_elements(self, joint, transformation_to_joint):
        """
        Creates and applies the features of this interface to the elements of the specified joint.

        Parameters
        ----------
        joint : :class:`compas_timber.connections.Joint`
            The joint to which the interface is applied.
        transformation_to_joint : :class:`compas.geomtry.Transformation'
            The transformation from the global coordinate system to the joint's local coordinate system.

        """
        for element in joint.elements:
            if not isinstance(element, TimberElement):
                continue
            processings = self.feature(element, transformation_to_joint)
            if processings:
                element.features.extend(processings)
            else:
                continue
