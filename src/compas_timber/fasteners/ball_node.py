from __future__ import annotations

from typing import Optional

from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Sphere

from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Slot

from .fastener import FastenerPart


class BallNode(FastenerPart):
    """
    This part is used by the `BallNodeJoint`.
    It describes the ball node itself, a sphere that connects multiple beams together through rods and plates.

    Parameters
    ----------
    diameter : float
        The diameter of the ball node.
    frame : Frame, optional
        The placement frame of the ball node. Defaults to the world XY frame.

    Attributes
    ----------
    diameter : float
        The diameter of the ball node.
    radius : float
        The radius of the ball node, which is half of the diameter.
    geometry : Brep
        The geometry of the ball node in model coordinates.

    """

    @property
    def __data__(self):
        return {"diameter": self.diameter, "frame": self.placement_frame}

    def __init__(self, diameter: float, frame: Optional[Frame] = None, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.diameter = diameter

    @property
    def radius(self):
        return self.diameter / 2

    def compute_elementgeometry(self, include_features: bool = False):
        sphere = Sphere(self.radius, Frame.worldXY())
        return sphere.to_brep()


class BallNodeRod(FastenerPart):
    """
    Describes the rod that connects the ball node to the beam. It is used by the `BallNodeJoint`.

    Parameters
    ----------
    length : float
        The length of the rod.
    diameter : float
        The diameter of the rod.
    beam : Beam, optional
        The beam that the rod is connected to, used as reference for the directionality.
    frame : Frame, optional
        The placement frame of the rod. Defaults to the world XY frame.

    Attributes
    ----------
    length : float
        The length of the rod.
    diameter : float
        The diameter of the rod.
    referenced_beam : Beam
        The beam that the rod is connected to, used as reference for the directionality.
    geometry : Brep
        The geometry of the rod in model coordinates.

    """

    @property
    def __data__(self):
        return {"length": self.length, "diameter": self.diameter, "frame": self.placement_frame}

    def __init__(self, length: float, diameter: float, beam=None, frame: Optional[Frame] = None, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.length = length
        self.diameter = diameter
        self.referenced_beam = beam

    def compute_elementgeometry(self, include_features: bool = False):
        local = Frame.worldXY()
        cylinder = Cylinder(radius=self.diameter / 2, height=self.length, frame=local)
        cylinder.frame.point += local.zaxis * self.length / 2
        return cylinder.to_brep()


class BallNodePlate(FastenerPart):
    """
    Describes the plate that connects the ball node to the beam. It is used by the `BallNodeJoint`.

    Parameters
    ----------
    x_size : float
        The size of the plate in the x direction.
    y_size : float
        The size of the plate in the y direction.
    thickness : float
        The thickness of the plate.
    frame : Frame, optional
        The placement frame of the plate. Defaults to the world XY frame.
    plate_depth : float
        The depth of the slot that will be cut in the plate to fit the rod.
    rod : BallNodeRod, optional
        The rod that the plate is connected to, used as reference for the directionality.
    ball : BallNode, optional
        The ball node that the plate is connected to, used as reference for the directionality.

    Attributes
    ----------
    x_size : float
        The size of the plate in the x direction.
    y_size : float
        The size of the plate in the y direction.
    thickness : float
        The thickness of the plate.
    plate_depth : float
        The depth of the slot that will be cut in the plate to fit the rod.
    geometry : list[Brep]
        The geometry of the plate in model coordinates, as a cap box and a slot box.

    """

    @property
    def __data__(self):
        return {"x_size": self.x_size, "y_size": self.y_size, "thickness": self.thickness, "frame": self.placement_frame, "plate_depth": self.plate_depth}

    def __init__(self, x_size, y_size, thickness, frame: Optional[Frame] = None, plate_depth=0, rod=None, ball=None, **kwargs):
        super().__init__(frame=frame, **kwargs)
        self.x_size = x_size
        self.y_size = y_size
        self.thickness = thickness
        self.plate_depth = plate_depth
        self.rod = rod
        self.ball = ball

    def _local_breps(self):
        local = Frame.worldXY()

        # cap plate
        box = Box(self.x_size, self.y_size, self.thickness, frame=local.copy())
        box.frame.point += local.zaxis * self.thickness / 2
        box_brep = box.to_brep()

        # slot plate
        slot_plate_frame = local.copy()
        slot_plate_frame.translate(slot_plate_frame.zaxis * (self.thickness + self.plate_depth / 2))
        slot_box = Box(self.thickness, self.y_size, self.plate_depth, frame=slot_plate_frame)
        slot_brep = slot_box.to_brep()

        return [box_brep, slot_brep]

    def compute_elementgeometry(self, include_features: bool = False):
        return self._local_breps()

    @property
    def geometry(self):
        xform = self.modeltransformation
        return [brep.transformed(xform) for brep in self._local_breps()]

    def apply_fastening_features(self, elements):
        features = []
        for ele in elements:
            if self.rod is not None and ele is self.rod.referenced_beam:
                frame = self.frame  # placement frame in model coordinates

                # jack rafter cut
                cutting_plane = Plane(frame.point, frame.zaxis)
                cutting_plane.translate(frame.zaxis * self.thickness)
                cutting_plane.normal *= -1
                jrc = JackRafterCut.from_plane_and_beam(cutting_plane, ele)
                ele.add_feature(jrc)
                features.append(jrc)

                # slot
                plane = Plane(frame.point, frame.xaxis)
                slot_depth = self.plate_depth + self.thickness + self.rod.length + self.ball.radius
                slot = Slot.from_plane_and_beam(plane, ele, slot_depth, self.thickness)
                ele.add_feature(slot)
                features.append(slot)

        return features
