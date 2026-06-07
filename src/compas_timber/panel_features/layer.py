from __future__ import annotations

from typing import Optional

from compas.geometry import Polyline, Transformation

from compas_timber.elements.panel import Panel
from compas_timber.elements.plate_geometry import PlateGeometry


class Layer(Panel):
    """A resolved cross-section layer that *is* a :class:`~compas_timber.elements.Panel`.

    A ``Layer`` represents a slice of a parent :class:`~compas_timber.elements.Panel`
    between two through-thickness levels (``start_level`` and ``end_level``).  It
    is a full :class:`Panel` in its own right — it owns its ``plate_geometry``
    (built from the slice) and inherits every panel operation (``outline_a`` /
    ``outline_b``, ``planes``, ``edge_planes``, ``set_extension_plane`` /
    ``apply_edge_extensions``, joints, …).  Because the slice is built from the
    parent panel's *local* outlines, the Layer's ``transformation`` is relative
    to the parent panel; once the Layer is attached to the model as a child of
    the panel, its ``modeltransformation`` (and therefore its outlines, planes,
    and edge extensions) is correct without any per-method patching.

    ``Layer`` is distinguished from a regular ``Panel`` by the class attribute
    :attr:`is_layer` (``True``).  :class:`~compas_timber.model.TimberModel` uses
    it to keep layers out of :attr:`~compas_timber.model.TimberModel.panels`
    (so layers are not auto-connected at the top level) while still exposing
    them via :attr:`~compas_timber.model.TimberModel.layers`.

    Parameters
    ----------
    panel : :class:`~compas_timber.elements.Panel`
        The parent panel this layer is sliced from.
    start_level : float
        The starting level of the layer, measured from the ``outline_a`` face.
    end_level : float
        The ending level of the layer, measured from the ``outline_a`` face.
    name : str, optional
        Human-readable layer identifier (e.g. ``"core"``, ``"exterior"``).

    Attributes
    ----------
    panel : :class:`~compas_timber.elements.Panel`
        The parent panel.
    start_level, end_level : float
        Range of the layer through the parent panel's thickness.
    parent_layer : :class:`Layer` or None
        Parent layer in the cross-section tree.
    sublayers : list[:class:`Layer`]
        Ordered child layers.
    """

    is_layer = True

    def __init__(
        self,
        panel: Panel,
        start_level: float,
        end_level: float,
        name: Optional[str] = None,
        **kwargs,
    ):
        outline_a, outline_b = Layer.get_outlines_from_panel_range(panel, start_level, end_level)
        args = PlateGeometry.get_args_from_outlines(outline_a, outline_b, orientation = panel.frame.yaxis)
        # Build the Layer as a real Panel from the slice geometry.  ``args`` carries
        # frame / length / width / thickness / local_outline_a / local_outline_b
        # (in the parent panel's local space), so the Layer's transformation is
        # the slice frame relative to the parent panel.
        super().__init__(name=name, **args, **kwargs)

        self.panel = panel
        self.start_level = start_level
        self.end_level = end_level
        self.parent_layer = None
        self.sublayers = []

    def __repr__(self):
        return "Layer(name={}, thickness={})".format(self.name, self.thickness)

    def __str__(self):
        return "Layer(name={}, position={}, thickness={})".format(self.name, self.frame.point[2], self.thickness)

    @property
    def center_height(self):
        """Z coordinate of the layer's mid-thickness in model space."""
        return self.outline_a[0][2] + self.thickness / 2

    @staticmethod
    def get_outlines_from_panel_range(panel: Panel, range_a: float, range_b: float):
        """Interpolate the parent panel's two outlines at *range_a* and *range_b*.

        The outlines are returned in **panel-local** space (sliced from
        ``panel.plate_geometry.outline_a`` / ``outline_b``, not from
        ``panel.outline_a`` / ``outline_b`` which apply ``modeltransformation``).
        Building the Layer from local-space slices keeps the Layer's
        transformation relative to the parent panel, so once it is attached to
        the model as a child of the panel its ``modelgeometry`` lands in the
        right world location instead of being double-transformed.
        """
        local_outline_a = panel.plate_geometry.outline_a
        local_outline_b = panel.plate_geometry.outline_b
        if range_a:
            offset = range_a / panel.thickness
            frame_outline_a = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)])
        else:
            frame_outline_a = local_outline_a

        offset = range_b / panel.thickness
        frame_outline_b = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)])
        return frame_outline_a, frame_outline_b

    def apply_edge_extensions(self):
        super().apply_edge_extensions()
        self.update_sublayer_geometry(self)

    @staticmethod
    def update_sublayer_geometry(layer):
        """Rebuild this layer's ``plate_geometry`` from the parent panel range.

        Call after the parent panel's outlines change so the slice tracks it.
        """
        for sublayer in layer.sublayers:
            outline_a, outline_b = Layer.get_outlines_from_panel_range(layer, sublayer.start_level, sublayer.end_level)
            args = PlateGeometry.get_args_from_outlines(outline_a, outline_b)
            sublayer.plate_geometry = PlateGeometry(local_outline_a=args["local_outline_a"], local_outline_b=args["local_outline_b"])
            sublayer.transformation = Transformation.from_frame(args["frame"])
            Layer.update_sublayer_geometry(sublayer)



    def iter_subtree(self):
        """Yield this layer and all descendants depth-first."""
        yield self
        for child in self.sublayers:
            yield from child.iter_subtree()
