from __future__ import annotations

from typing import Optional

from compas.geometry import Box, Transformation
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Vector
from compas_model.elements import Element
from compas_model.elements import reset_computed

from compas_timber.elements.plate_geometry import PlateGeometry
from compas_timber.errors import FeatureApplicationError


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

    When no *panel* is supplied at construction time the layer is in a
    *deferred* state: :attr:`plate_geometry` is ``None`` and
    :attr:`transformation` is the identity.  Geometry is created the first
    time :meth:`_attach` is called (triggered by assigning the layer to a
    :class:`~compas_timber.elements.Panel` via ``panel.layers = [...]`` or
    via :meth:`~compas_timber.elements.Panel.define_core_layer`).

    Parameters
    ----------
    panel : :class:`~compas_timber.elements.Panel`, optional
        The parent panel.  When omitted geometry creation is deferred until
        the layer is attached to a panel.
    start_level : float
        Starting offset from ``outline_a``, measured in the panel's thickness direction.
    end_level : float
        Ending offset from ``outline_a``, measured in the panel's thickness direction.
    name : str, optional
        Human-readable identifier (e.g. ``"core"``, ``"exterior"``).
    parent_layer : :class:`Layer`, optional
        The containing layer when this is a sublayer.  ``None`` for root-level layers.
    sublayers : list[:class:`Layer`], optional
        Child layers to attach immediately.  Equivalent to setting :attr:`sublayers`
        after construction.

    Attributes
    ----------
    panel : :class:`~compas_timber.elements.Panel` or None
        The parent panel.  ``None`` when deferred or after deserialization.
    plate_geometry : :class:`~compas_timber.elements.PlateGeometry` or None
        Geometry of this layer slice.  ``None`` while deferred.
    start_level, end_level : float
        Range of this layer through the parent panel's thickness.
    parent_layer : :class:`Layer` or None
        The parent layer, or ``None`` if this is a root-level layer of the panel.
    layer_path : tuple[int, ...] or None
        Hierarchical path key matching the corresponding entry in ``Panel._layer_path_dict``.
        Set automatically when the layer is registered.
    sublayers : list[:class:`Layer`]
        Ordered child layers.  Assign a new list to rewire the subtree; use
        :meth:`define_sublayers` to build sublayers from thickness values.
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

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @property
    def __data__(self):
        data = super().__data__
        data["start_level"] = self.start_level
        data["end_level"] = self.end_level
        data["layer_path"] = self.layer_path
        if self._plate_geometry is not None:
            data["local_outline_a"] = self._plate_geometry.outline_a
            data["local_outline_b"] = self._plate_geometry.outline_b
        else:
            data["local_outline_a"] = None
            data["local_outline_b"] = None
        return data

    @classmethod
    def __from_data__(cls, data):
        layer = cls.__new__(cls)
        layer._sublayers = []  # before Element.__init__ which may read sublayers
        layer._planes = None
        layer._panel = None
        layer._plate_geometry = None
        Element.__init__(layer, transformation=data["transformation"], name=data.get("name"))
        local_outline_a = data.get("local_outline_a")
        local_outline_b = data.get("local_outline_b")
        if local_outline_a is not None and local_outline_b is not None:
            layer._plate_geometry = PlateGeometry(
                local_outline_a=local_outline_a,
                local_outline_b=local_outline_b,
            )
        layer.start_level = data["start_level"]
        layer.end_level = data.get("end_level")
        layer._planes = None
        layer.parent_layer = None
        layer.layer_path = data.get("layer_path")
        return layer

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(
        self,
        panel=None,
        start_level: float = 0.0,
        end_level: Optional[float] = None,
        name: Optional[str] = None,
        parent_layer: Optional["Layer"] = None,
        sublayers: Optional[list] = None,
        layer_path: Optional[tuple] = None,
        **kwargs,
    ):
        self._panel = None
        self._plate_geometry = None
        self._sublayers = []  # before super().__init__() which may read sublayers
        self._planes = None

        self.start_level = start_level
        self.end_level = end_level
        self.parent_layer = parent_layer
        self.layer_path = tuple(layer_path) if layer_path is not None else None

        if panel is not None and end_level is not None:
            outline_a, outline_b = Layer.get_outlines_from_panel_range(panel, start_level, end_level)
            self._plate_geometry = PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=[0, 1, 0])
            transformation = Transformation.from_frame(self._plate_geometry.frame)
        else:
            transformation = Transformation()

        super(Layer, self).__init__(transformation=transformation, name=name, **kwargs)
        self._panel = panel

        if sublayers:
            self.sublayers = sublayers

    def __repr__(self):
        thickness = (self.end_level - self.start_level) if self.end_level is not None else None
        return "Layer(name={}, path={}, thickness={})".format(self.name, self.layer_path, thickness)

    def __str__(self):
        thickness = (self.end_level - self.start_level) if self.end_level is not None else None
        return "Layer(name={}, path={}, thickness={})".format(self.name, self.layer_path, thickness)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def plate_geometry(self):
        return self._plate_geometry

    @plate_geometry.setter
    def plate_geometry(self, value):
        self._plate_geometry = value

    @property
    def panel(self):
        return self._panel

    @panel.setter
    def panel(self, value):
        self._panel = value

    @property
    def sublayers(self):
        return self._sublayers

    @sublayers.setter
    def sublayers(self, layers):
        """Replace child layers, wiring them up if this layer is already attached."""
        for old in self._sublayers:
            old._unregister()
        self._sublayers = list(layers) if layers else []
        for sublayer in self._sublayers:
            sublayer.parent_layer = self
        if self._panel is not None and self.layer_path is not None:
            for i, sublayer in enumerate(self._sublayers):
                sublayer._attach(self._panel, self.layer_path + (i,))

    @property
    def thickness(self):
        return self.end_level - self.start_level

    @property
    def outline_a(self):
        return self._plate_geometry.outline_a.transformed(self.modeltransformation)

    @property
    def outline_b(self):
        return self._plate_geometry.outline_b.transformed(self.modeltransformation)

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
        return {i: plane.transformed(self.modeltransformation) for i, plane in self._plate_geometry.edge_planes.items()}

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

    def regenerate_plate_geometry(self):
        outline_a, outline_b = Layer.get_outlines_from_panel_range(self._panel, self.start_level, self.end_level)
        self._plate_geometry = PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=[0, 1, 0])

    def _attach(self, panel, path):
        """Register this layer with *panel* at *path*, creating geometry if deferred, then recurse.

        This is called automatically when a layer is assigned to a panel or
        to another already-attached layer.  Do not call it directly unless
        manually rebuilding the layer tree.
        """
        if self._plate_geometry is None:
            outline_a, outline_b = Layer.get_outlines_from_panel_range(panel, self.start_level, self.end_level)
            self._plate_geometry = PlateGeometry.from_global_outlines(outline_a, outline_b, orientation=[0, 1, 0])
            self.transformation = Transformation.from_frame(self._plate_geometry.frame)
        self._panel = panel
        self.layer_path = path
        panel._layer_path_dict[path] = self
        for i, sublayer in enumerate(self._sublayers):
            sublayer.parent_layer = self
            sublayer._attach(panel, path + (i,))

    def _unregister(self):
        """Remove this layer and all descendants from the panel's ``_layer_path_dict``."""
        for sublayer in self._sublayers:
            sublayer._unregister()
        if self._panel is not None and self.layer_path is not None:
            self._panel._layer_path_dict.pop(self.layer_path, None)
        self.layer_path = None

    def define_sublayers(self, thicknesses: list, names: Optional[list] = None) -> list:
        """Subdivide this layer into child layers by thickness.

        Parameters
        ----------
        thicknesses : list[float | None]
            Thickness of each sublayer, ordered from ``start_level`` to ``end_level``.
            At most one entry may be ``None``; that slot absorbs whatever thickness
            remains after the other entries are summed.  If no ``None`` is present
            and the sum of entries is less than :attr:`thickness`, an extra layer
            is appended at the end with the remaining thickness.
            The sum of all explicit (non-``None``) values must not exceed
            :attr:`thickness`.
        names : list[str | None], optional
            Names for the sublayers.  When given, length must match *thicknesses*
            (before any auto-appended remainder layer).

        Returns
        -------
        list[:class:`Layer`]
            The newly created sublayers (also stored in :attr:`sublayers`).
        """
        none_count = sum(1 for t in thicknesses if t is None)
        if none_count > 1:
            raise ValueError("At most one None is allowed in thicknesses.")
        if names is not None and len(names) != len(thicknesses):
            raise ValueError("Length of names ({}) must match length of thicknesses ({}).".format(len(names), len(thicknesses)))
        if self.layer_path is None:
            raise RuntimeError("Layer must be registered with a panel (have a layer_path) before calling define_sublayers.")

        sum_defined = sum(t for t in thicknesses if t is not None)
        remaining = self.thickness - sum_defined
        if remaining < -1e-6:
            raise ValueError("Sum of defined thicknesses ({:.6f}) exceeds layer thickness ({:.6f}).".format(sum_defined, self.thickness))

        if none_count == 1:
            thicknesses = [remaining if t is None else t for t in thicknesses]
        elif remaining > 1e-6:
            thicknesses = list(thicknesses) + [remaining]
            if names is not None:
                names = list(names) + [None]

        current_level = self.start_level
        new_sublayers = []
        for i, t in enumerate(thicknesses):
            new_sublayers.append(
                Layer(
                    start_level=current_level,
                    end_level=current_level + t,
                    name=names[i] if names is not None else None,
                    parent_layer=self,
                )
            )
            current_level += t

        self.sublayers = new_sublayers  # use setter to wire up
        return new_sublayers

    def merge_sublayer_tree(self, model):
        for element in self._sublayers:
            if element not in model.elements():
                model.add_element(element, parent=self)
            if isinstance(element, Layer):
                element.merge_sublayer_tree(model)

    @reset_computed
    def reset_computed_properties(self):
        """Clear all cached properties so they recompute against the current model tree."""
        self._plate_geometry.reset()
        self._planes = None

    def clear_model_dependent_cache(self):
        """Clear cached attributes that depend on the element's position in the model hierarchy."""
        self.model = None
        self._modeltransformation = None
        self._modelgeometry = None
        self._aabb = None
        self._obb = None
        self._collision_mesh = None
        self._planes = None

    def transformation_to_local(self):
        """Transformation from model space to this layer's local space."""
        return self.modeltransformation.inverse()

    def set_extension_plane(self, edge_index: int, plane: Plane):
        """Set an extension plane for an edge.  Propagates to all sublayers."""
        self._plate_geometry.set_extension_plane(edge_index, plane.transformed(self.transformation_to_local()))
        for sublayer in self._sublayers:
            sublayer.set_extension_plane(edge_index, plane)

    def apply_edge_extensions(self):
        """Move edge vertices onto the extension planes, then recurse to sublayers."""
        self._plate_geometry.apply_edge_extensions()
        for sublayer in self._sublayers:
            sublayer.apply_edge_extensions()

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
        obb = self._plate_geometry.compute_aabb(inflate)
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
        plate_geo = self.plate_geometry.compute_shape()
        if include_features:
            if self.panel:
                for feature in self.panel._features:
                    try:
                        plate_geo = feature.apply(plate_geo, self)
                    except FeatureApplicationError as error:
                        self.debug_info.append(error)
        return plate_geo

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
        offset_a = range_a / panel.thickness
        if offset_a:
            layer_outline_a = Polyline([pt_a * (1.0 - offset_a) + pt_b * offset_a for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)])
        else:
            layer_outline_a = local_outline_a

        offset_b = range_b / panel.thickness
        layer_outline_b = Polyline([pt_a * (1.0 - offset_b) + pt_b * offset_b for pt_a, pt_b in zip(local_outline_a.points, local_outline_b.points)])
        return layer_outline_a, layer_outline_b


def build_layers_from_defs(panel, layer_defs, panel_thickness=None):
    """Create bound Layer instances from panel-free layer definitions.

    Creates one Layer per def bound to *panel*, resolving ``end_level=None``
    to *panel_thickness* (or ``panel.thickness``).  Sublayer relationships are
    wired via ``Layer._sublayers`` so the returned roots can be passed directly
    to ``panel.layers``.

    Parameters
    ----------
    panel : Panel
        The panel to bind layers to.
    layer_defs : list[Layer]
        Layer definitions with ``layer_path`` set and ``panel=None``.
    panel_thickness : float, optional
        Override for the panel thickness; defaults to ``panel.thickness``.

    Returns
    -------
    list[Layer]
        Root layers (path depth 1) with sublayers already wired.
    """
    thickness = panel_thickness if panel_thickness is not None else panel.thickness
    sorted_defs = sorted(
        (d for d in layer_defs if d.layer_path is not None),
        key=lambda d: (len(d.layer_path), d.layer_path),
    )
    bound_by_path = {}
    for layer_def in sorted_defs:
        path = layer_def.layer_path
        end = layer_def.end_level if layer_def.end_level is not None else thickness
        bound = Layer(panel, layer_def.start_level, end, name=layer_def.name, layer_path=path)
        bound_by_path[path] = bound
        if len(path) > 1:
            parent = bound_by_path.get(path[:-1])
            if parent is not None:
                parent._sublayers.append(bound)
                bound.parent_layer = parent
    return [bound_by_path[p] for p in sorted(p for p in bound_by_path if len(p) == 1)]
