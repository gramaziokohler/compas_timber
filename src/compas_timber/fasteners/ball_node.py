from __future__ import annotations

from typing import Optional

from compas.data import Data
from compas.geometry import Box
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere
from compas.geometry import Transformation
from compas.geometry import Vector
from compas_brep import Brep

from compas_timber.fabrication import JackRafterCut
from compas_timber.fabrication import Slot

from .anchor import AnchorKind
from .fastener import Fastener
from .fastener import FastenerPart


class BallNodeCore(FastenerPart):
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
        return Brep.from_sphere(sphere)


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
        return Brep.from_cylinder(cylinder)


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
    ball : BallNodeCore, optional
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

    def __init__(self, x_size: float, y_size: float, thickness: float, frame: Optional[Frame] = None, plate_depth: float = 0, rod=None, ball=None, **kwargs):
        # TODO: narrow down the interface, if all we need is rod length and ball radius, we can just pass those instead of the whole objects
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
        box_brep = Brep.from_box(box)

        # slot plate
        slot_plate_frame = local.copy()
        slot_plate_frame.translate(slot_plate_frame.zaxis * (self.thickness + self.plate_depth / 2))
        slot_box = Box(self.thickness, self.y_size, self.plate_depth, frame=slot_plate_frame)
        slot_brep = Brep.from_box(slot_box)

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


class BallNodeFastenerParameters(Data):
    """The parameters that shape a :class:`BallNodeFastener`.

    This is the design intent of the fastener, kept separate from the fastener so it can be authored on the joint (and
    passed through :meth:`~compas_timber.connections.BallNodeJoint.create`) without the joint touching the fastener's
    internals. All values carry meaningful defaults, so an instance with no arguments is a valid, sensible fastener.

    As a :class:`~compas.data.Data`, it serializes and deserializes itself through the standard COMPAS mechanism.

    Parameters
    ----------
    ball_diameter : float, optional
        The diameter of the central ball node. Rods are sized as a third of this. Default is 8.0.
    rods_length : float, optional
        The length of the rods connecting the ball node to the beams. Default is 10.0.
    plate_thickness : float, optional
        The thickness of the plates connecting the rods to the beams. Default is 2.0.
    plate_depth : float, optional
        The depth of the slot connecting the rods to the beams. Default is 10.0.
    """

    @property
    def __data__(self):
        return {
            "ball_diameter": self.ball_diameter,
            "rods_length": self.rods_length,
            "plate_thickness": self.plate_thickness,
            "plate_depth": self.plate_depth,
        }

    def __init__(self, ball_diameter: float = 8.0, rods_length: float = 10.0, plate_thickness: float = 2.0, plate_depth: float = 10.0, **kwargs):
        super().__init__(**kwargs)
        self.ball_diameter = ball_diameter
        self.rods_length = rods_length
        self.plate_thickness = plate_thickness
        self.plate_depth = plate_depth


class BallNodeFastener(Fastener):
    """A fastener that ties the ends of several beams together through a central ball node.

    This is the "what" half of the anchor-based fastener system for the ball node: it is joint-agnostic and binds to a
    single ``POINT`` anchor (the node where the beams meet). When bound, it stages a nested part hierarchy that mirrors
    the physical assembly:

    * the fastener owns a central :class:`BallNodeCore` (the *core*),
    * the core owns one :class:`BallNodeRod` per beam,
    * each rod owns its :class:`BallNodePlate`.

    Every part's placement is expressed relative to its parent, so the core sits at the fastener (the node), each rod is
    oriented relative to the core, and each plate sits at the far end of its rod.

    Parameters
    ----------
    parameters : :class:`BallNodeFastenerParameters`, optional
        The parameters shaping the fastener. Defaults to :class:`BallNodeFastenerParameters` with all default values.

    Attributes
    ----------
    parameters : :class:`BallNodeFastenerParameters`
        The parameters shaping the fastener.
    ACCEPTS : :class:`~compas_timber.fasteners.AnchorKind`
        The kind of anchor this fastener binds to (``POINT``).
    """

    ACCEPTS = AnchorKind.POINT

    @property
    def __data__(self):
        data = super().__data__
        data["parameters"] = self.parameters
        return data

    def __init__(self, parameters: Optional[BallNodeFastenerParameters] = None, **kwargs):
        super().__init__(**kwargs)
        self.parameters = parameters if parameters is not None else BallNodeFastenerParameters()

    def bind(self, anchors: list) -> "BallNodeFastener":
        """Bind the fastener to the joint's node anchor, staging the core/rods/plates hierarchy.

        Parameters
        ----------
        anchors : list of :class:`~compas_timber.fasteners.FastenerAnchor`
            The anchors published by the joint. Exactly one ``POINT`` anchor is expected; its frame locates the node and
            its ``elements`` are the beams to connect.

        Returns
        -------
        :class:`~compas_timber.fasteners.BallNodeFastener`
            The fastener itself, for chaining.

        Raises
        ------
        ValueError
            If the anchors are not a single anchor of the accepted kind.
        """
        anchors = list(anchors)
        if len(anchors) != 1 or anchors[0].kind is not self.ACCEPTS:
            raise ValueError("{} binds to exactly one {} anchor, got {}.".format(type(self).__name__, self.ACCEPTS, [anchor.kind for anchor in anchors]))

        anchor = anchors[0]
        node_point = anchor.frame.point
        beams = anchor.elements
        params = self.parameters

        # the fastener sits at the node; every part below is placed relative to it
        self.transformation = Transformation.from_frame(anchor.frame)

        # the core sits at the fastener origin (identity relative to the fastener)
        core = BallNodeCore(diameter=params.ball_diameter)
        self.add_part(core)

        for beam in beams:
            rod_direction = beam.centerline.direction
            outwards = self._beam_points_outwards(beam, node_point)
            if not outwards:
                rod_direction = rod_direction * -1

            # the rod frame is expressed relative to the core (which sits at the node)
            plane = Plane(Point(0, 0, 0), rod_direction)
            rod_frame = Frame.from_plane(plane)
            rod_frame.xaxis = beam.frame.yaxis
            rod_frame.yaxis = beam.frame.zaxis
            if not outwards:
                rod_frame.yaxis *= -1
            rod_frame.translate(rod_frame.zaxis * params.ball_diameter / 2)

            # TODO: diameter is proportional to ball diameter, but we may want to make it a separate parameter
            rod = BallNodeRod(length=params.rods_length, diameter=params.ball_diameter / 3, beam=beam, frame=rod_frame)
            core.add_part(rod)

            # the plate sits at the far end of the rod, expressed relative to the rod's frame
            plate_frame = Frame(Point(0, 0, params.rods_length))
            plate = BallNodePlate(beam.width, beam.height, params.plate_thickness, plate_frame, plate_depth=params.plate_depth, rod=rod, ball=core)
            rod.add_part(plate)

        return self

    @staticmethod
    def _beam_points_outwards(beam, node_point: Point) -> bool:
        """Whether the beam's centerline direction points away from the node."""
        direction = beam.centerline.direction
        return direction.dot(Vector.from_start_end(node_point, beam.centerline.midpoint)) > 0
