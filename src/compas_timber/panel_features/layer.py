from __future__ import annotations

from typing import Optional

from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.elements.plate_geometry import PlateGeometry


class Layer(Element):
    """A resolved cross-section layer of a :class:`~compas_timber.elements.Panel`.

    A ``Layer`` represents a slice of a parent panel between two
    through-thickness levels (``start_level`` and ``end_level``), measured
    from the ``outline_a`` face.  It is a first-class model element that owns
    its own :class:`~compas_timber.elements.PlateGeometry` and lives as a
    child of the parent panel in the model tree.

    The Layer's ``transformation`` is relative to the parent panel frame, so
    once attached to the model its ``modeltransformation`` (and all
    world-space properties) compute correctly through the tree.

    :attr:`is_layer` is ``True`` so
    :class:`~compas_timber.model.TimberModel` keeps layers out of
    :attr:`~compas_timber.model.TimberModel.panels` while exposing them via
    :attr:`~compas_timber.model.TimberModel.layers`.

    Parameters
    ----------
    panel : :class:`~compas_timber.elements.Panel`
        The parent panel this layer is sliced from.
    start_level : float
        Starting offset from ``outline_a``, measured in the panel's thickness direction.
    end_level : float
        Ending offset from ``outline_a``, measured in the panel's thickness direction.
    name : str, optional
        Human-readable identifier (e.g. ``"core"``, ``"exterior"``).

    Attributes
    ----------
    panel : :class:`~compas_timber.elements.Panel` or None
        The parent panel at construction time.  ``None`` after deserialization;
        use ``self.parent`` to navigate the model tree.
    start_level, end_level : float
        Range of this layer through the parent panel's thickness.
    parent_layer : :class:`Layer` or None
        Parent layer in the sublayer tree.
    sublayers : list[:class:`Layer`]
        Ordered child layers.
    thickness : float
        Layer thickness (``end_level - start_level``).
    outline_a, outline_b : :class:`~compas.geometry.Polyline`
        World-space outlines of the two main faces.
    planes : tuple[:class:`~compas.geometry.Plane`, :class:`~compas.geometry.Plane`]
        World-space planes of the two main faces.
    normal : :class:`~compas.geometry.Vector`
        World-space normal of the layer.
    edge_planes : dict[int, :class:`~compas.geometry.Plane`]
        World-space edge planes by edge index.
    """

    is_layer = True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @property
    def __data__(self):
        data = super().__data__
        data["local_outline_a"] = self.plate_geometry.outline_a
        data["local_outline_b"] = self.plate_geometry.outline_b
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["start_level"] = self.start_level
        data["end_level"] = self.end_level
        return data

    @classmethod
    def __from_data__(cls, data):
        layer = cls.__new__(cls)
        Element.__init__(layer, transformation=data["transformation"], name=data.get("name"))
        layer.plate_geometry = PlateGeometry(
            local_outline_a=data["local_outline_a"],
            local_outline_b=data["local_outline_b"],
        )
        layer.length = data["length"]
        layer.width = data["width"]
        layer.height = data["height"]
        layer.start_level = data["start_level"]
        layer.end_level = data["end_level"]
        layer.panel = None
        layer.parent_layer = None
        layer.sublayers = []
        layer._planes = None
        return layer

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(
        self,
        panel,
        start_level: float,
        end_level: float,
        name: Optional[str] = None,
        **kwargs,
    ):
        outline_a, outline_b = Layer.get_outlines_from_panel_range(panel, start_level, end_level)
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, orientation=panel.frame.yaxis)
        super().__init__(transformation=args["frame"].to_transformation(), name=name, **kwargs)

        self.plate_geometry = PlateGeometry(
            local_outline_a=args["local_outline_a"],
            local_outline_b=args["local_outline_b"],
        )
        self.length = args["length"]
        self.width = args["width"]
        self.height = args["thickness"]

        self.panel = panel
        self.start_level = start_level
        self.end_level = end_level
        self.parent_layer = None
        self.sublayers = []
        self._planes = None

    def __repr__(self):
        return "Layer(name={}, thickness={})".format(self.name, self.thickness)

    def __str__(self):
        return "Layer(name={}, position={}, thickness={})".format(self.name, self.frame.point[2], self.thickness)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def thickness(self):
        return self.height

    @property
    def outline_a(self):
        return self.plate_geometry.outline_a.transformed(self.modeltransformation)

    @property
    def outline_b(self):
        return self.plate_geometry.outline_b.transformed(self.modeltransformation)

    @property
    def outlines(self):
        return (self.outline_a, self.outline_b)

    @property
    def planes(self):
        if not self._planes:
            local_planes = (Plane.worldXY(), Plane(Point(0, 0, self.thickness), Vector(0, 0, 1)))
            self._planes = (
                local_planes[0].transformed(self.modeltransformation),
                local_planes[1].transformed(self.modeltransformation),
            )
        return self._planes

    @property
    def normal(self):
        return Vector(0, 0, 1).transformed(self.modeltransformation)

    @property
    def edge_planes(self):
        return {i: plane.transformed(self.modeltransformation) for i, plane in self.plate_geometry.edge_planes.items()}

    @property
    def center_height(self):
        """Z coordinate of the layer's mid-thickness in model space."""
        return self.outline_a[0][2] + self.thickness / 2

    @property
    def geometry(self):
        return self.modelgeometry

    @geometry.setter
    def geometry(self, _):
        raise AttributeError("Geometry is a computed property and cannot be set directly.")

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    @reset_computed
    def reset_computed_properties(self):
        """Clear all cached properties so they recompute against the current model tree."""
        self._planes = None

    def transformation_to_local(self):
        """Transformation from model space to this layer's local space."""
        return self.modeltransformation.inverse()

    def set_extension_plane(self, edge_index: int, plane: Plane):
        """Set an extension plane for an edge.  Propagates to all sublayers."""
        self.plate_geometry.set_extension_plane(edge_index, plane.transformed(self.transformation_to_local()))
        for sublayer in self.sublayers:
            sublayer.set_extension_plane(edge_index, plane)

    def apply_edge_extensions(self):
        """Move edge vertices onto the extension planes, then recurse to sublayers."""
        self.plate_geometry.apply_edge_extensions()
        for sublayer in self.sublayers:
            sublayer.apply_edge_extensions()

    def iter_subtree(self):
        """Yield this layer and all descendants depth-first."""
        yield self
        for child in self.sublayers:
            yield from child.iter_subtree()

    # ------------------------------------------------------------------
    # compas_model.elements.Element abstract method implementations
    # ------------------------------------------------------------------

    def compute_aabb(self, inflate: float = 0.0) -> Box:
        vertices = self.outline_a.points + self.outline_b.points
        box = Box.from_points(vertices)
        box.xsize += inflate
        box.ysize += inflate
        box.zsize += inflate
        return box

    def compute_obb(self, inflate: float = 0.0) -> Box:
        obb = self.plate_geometry.compute_aabb(inflate)
        obb.transform(self.modeltransformation)
        return obb

    def compute_collision_mesh(self):
        return self.obb.to_mesh()

    def compute_modeltransformation(self):
        if not self.model:
            return self.transformation
        return super().compute_modeltransformation()

    def compute_modelgeometry(self):
        if not self.model:
            return self.elementgeometry.transformed(self.transformation)
        return super().compute_modelgeometry()

    def compute_elementgeometry(self, include_features: bool = True):
        return self.plate_geometry.compute_shape()

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_outlines_from_panel_range(panel, range_a: float, range_b: float):
        """Interpolate the parent panel's outlines at *range_a* and *range_b*.

        Returns outlines in panel-local space so the resulting Layer's
        ``transformation`` is relative to the parent panel.  Once attached
        to the model as a child of the panel its ``modeltransformation``
        lands in the correct world location.
        """
        local_outline_a = panel.plate_geometry.outline_a
        local_outline_b = panel.plate_geometry.outline_b
        if range_a:
            offset = range_a / panel.thickness
            frame_outline_a = Polyline(
                [pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)]
            )
        else:
            frame_outline_a = local_outline_a

        offset = range_b / panel.thickness
        frame_outline_b = Polyline(
            [pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)]
        )
        return frame_outline_a, frame_outline_b
