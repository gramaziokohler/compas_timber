from __future__ import annotations

from typing import Optional

from compas.geometry import Polyline
from compas.tolerance import TOL
from compas_timber.elements import Panel
from compas_timber.model import TimberModel


class LayerConfig:
    """Declarative description of one cross-section layer within a panel.

    A ``LayerConfig`` is a *blueprint* — it does not carry any geometry.
    Geometry is only created when
    :meth:`~timber_design.populators.PanelPopulatorConfig.create_layers`
    resolves the full layer stack and instantiates :class:`Layer` objects from
    these definitions.

    Parameters
    ----------
    thickness : float, optional
        Thickness of this layer in model units.  Pass ``None`` to use
        fill-remaining logic: the layer receives whatever panel thickness is
        left after all fixed-thickness siblings have been allocated.  At most
        one sibling per parent may have ``thickness=None``.
    name : str, optional
        Human-readable layer identifier (e.g. ``"frame"``, ``"interior"``).
        Used as the layer key in the dict returned by
        :meth:`~timber_design.populators.PanelPopulatorConfig.create_layers`
        and as a prefix for plate categories (e.g. ``"interior_plate"``).
    agent_configs : list[:class:`~timber_design.populators.LayerAgentConfig`], optional
        Configuration objects for the agents that should be instantiated on
        this layer.
    sublayers : list[:class:`LayerConfig`], optional
        Nested child layer definitions for composite layers.

    Examples
    --------
    A structural frame layer with an edge agent and a stud agent::

        from timber_design.populators import LayerConfig
        from timber_design.populators import EdgePopulatorAgentConfig, StudPopulatorAgentConfig

        frame = LayerConfig(
            thickness=None,  # fill remaining
            name="frame",
            agent_configs=[
                EdgePopulatorAgentConfig(),
                StudPopulatorAgentConfig(stud_spacing=625.0),
            ],
        )
    """

    def __init__(
        self,
        thickness: Optional[float] = None,
        name: Optional[str] = None,
        agent_configs: Optional[list] = None,
        sublayers: Optional[list] = None,
    ):
        self.thickness = thickness
        self.sublayers = sublayers or []
        self.name = name
        self.agent_configs = agent_configs or []
        self.position: float = None
        self.resulting_layer = None

    def model_from_panel(self, panel):
        """Build a :class:`~compas_timber.model.TimberModel` of :class:`Layer` objects.

        Resolves all fill-remaining thicknesses and layer positions, then walks
        the definition tree depth-first, creating one :class:`Layer` per node and
        attaching the agents declared in each node's ``agent_configs``.

        Beam widths on those agent configs must already be resolved (the
        :class:`~timber_design.populators.PanelPopulatorConfig` does this via
        :meth:`~timber_design.populators.PanelPopulatorConfig.resolve_beam_widths`
        before calling this method).

        Parameters
        ----------
        panel : :class:`compas_timber.elements.Panel`
            The populator-space panel to slice into layers.

        Returns
        -------
        :class:`~compas_timber.model.TimberModel`
        """
        if not self.thickness:
            self.thickness = panel.thickness
        elif not TOL.is_close(self.thickness, panel.thickness):
            raise ValueError("the layer height was defined at {}, but the panel thickness is {}".format(self.thickness, panel.thickness))
        self.position = 0.0
        self._resolve_thicknesses()
        self._resolve_positions()

        layer_index = [0]  # mutable counter for closure

        def add_layer_from_def_to_model(layer_def, model, parent=None):
            layer = Layer.from_panel_and_range(
                panel,
                layer_def.position,
                layer_def.position + layer_def.thickness,
                name=layer_def.name,
                layer_index=layer_index[0],
                agent_configs=layer_def.agent_configs,
            )

            layer_index[0] += 1
            layer_def.resulting_layer = layer  # store on each specific LayerConfig
            print("resulting_layer = ", layer_def.resulting_layer)
            print(layer_def)
            if parent:
                layer.transform(parent.modeltransformation.inverse())
                parent.sublayer_list.append(layer)
                layer.parent_layer = parent
            model.add_element(layer, parent=parent)
            if layer_def.sublayers:
                for ld in layer_def.sublayers:
                    add_layer_from_def_to_model(ld, model, parent=layer)

        layer_model = TimberModel()
        add_layer_from_def_to_model(self, layer_model, parent=None)
        return layer_model

    def _resolve_thicknesses(self):
        """Resolve all ``thickness=None`` entries in the tree (mutates in place)."""
        self._infer_from_children(self)
        self._distribute_to_children(self)

    def _resolve_positions(self, start=0.0):
        current = start
        for sl in self.sublayers:
            sl.position = current
            if sl.sublayers:
                sl._resolve_positions(start=current)
            current += sl.thickness

    def _infer_from_children(self, layer_def):
        for sl in layer_def.sublayers:
            self._infer_from_children(sl)
        if layer_def.thickness is None and layer_def.sublayers:
            if all(sl.thickness is not None for sl in layer_def.sublayers):
                layer_def.thickness = sum(sl.thickness for sl in layer_def.sublayers)

    def _distribute_to_children(self, layer_def):
        if not layer_def.sublayers:
            return
        fill = [sl for sl in layer_def.sublayers if sl.thickness is None]
        known_sum = sum(sl.thickness for sl in layer_def.sublayers if sl.thickness is not None)
        if layer_def.thickness is None:
            raise ValueError("Cannot resolve fill-remaining sublayer(s) of layer {!r}: own thickness unknown.".format(layer_def.name))
        if not fill:
            if not TOL.is_close(known_sum, layer_def.thickness):
                breakdown = ", ".join("{!r}={}".format(sl.name, sl.thickness) for sl in layer_def.sublayers)
                raise ValueError("Sublayers of {!r} sum to {} but layer thickness is {}. [{}]".format(layer_def.name, known_sum, layer_def.thickness, breakdown))
        else:
            if len(fill) > 1:
                raise ValueError("At most one sublayer of {!r} may have thickness=None; got {}.".format(layer_def.name, len(fill)))
            remaining = layer_def.thickness - known_sum
            if remaining < 0 and not TOL.is_zero(remaining):
                raise ValueError("Fixed sublayers of {!r} exceed its thickness {}.".format(layer_def.name, layer_def.thickness))
            fill[0].thickness = remaining
        for sl in layer_def.sublayers:
            self._distribute_to_children(sl)


class Layer(Panel):
    """A resolved cross-section layer that *is* a :class:`~compas_timber.elements.Panel`.

    Each ``Layer`` is created by
    :meth:`~timber_design.populators.PanelPopulatorConfig.create_layers` from a
    :class:`LayerConfig`.  It extends :class:`~compas_timber.elements.Panel`
    with agent tracking and tree-structure bookkeeping.

    Since ``Layer`` inherits from ``Panel``, all panel geometry is accessed
    directly: ``layer.outline_a``, ``layer.outline_b``, ``layer.thickness``,
    ``layer.planes``, etc.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
    length, width, thickness : float
    local_outline_a, local_outline_b : :class:`~compas.geometry.Polyline`, optional
    name : str, optional
    agents : list, optional
    layer_index : int, optional

    Attributes
    ----------
    agents : list
        Agent instances registered on this layer.
    layer_index : int or None
        Zero-based ordinal position in the flat layer list.
    parent_layer : :class:`Layer` or None
        Parent layer in the cross-section tree.
    sublayer_list : list[:class:`Layer`]
        Ordered child layers.
    """

    def __init__(
        self,
        frame,
        length,
        width,
        thickness,
        local_outline_a=None,
        local_outline_b=None,
        type=None,
        name=None,
        agents=None,
        layer_index=None,
        **kwargs,
    ):
        super().__init__(
            frame,
            length,
            width,
            thickness,
            local_outline_a=local_outline_a,
            local_outline_b=local_outline_b,
            type=type,
            **kwargs,
        )
        self.name = name  # Panel.name setter → self._name
        self.agents = agents if agents is not None else []
        self.layer_index = layer_index
        self.parent_layer = None
        self.sublayer_list = []

    def __repr__(self):
        return "Layer with layer_index({})".format(self.layer_index)

    def __str__(self):
        return "Layer(name={}, layer_index={}, position={}, thickness={})".format(self.name, self.layer_index, self.frame.point[2], self.thickness)

    @property
    def elements(self):
        """All elements placed on this layer by every registered agent."""
        result = []
        for agent in self.agents:
            result.extend(agent.elements_for_layer(self))
        return result

    @property
    def center_height(self):
        """Z coordinate of the layer's mid-thickness in populator space."""
        return self.outline_a[0][2] + self.thickness / 2

    @classmethod
    def from_panel_and_range(
        cls,
        panel,
        range_a: float,
        range_b: float,
        name: Optional[str] = None,
        layer_index: Optional[int] = None,
        agent_configs: Optional[list] = None,
    ) -> "Layer":
        """Create a layer by slicing *panel* to a Z range and attaching agents.

        Parameters
        ----------
        panel : :class:`compas_timber.elements.Panel`
            Source panel to slice.
        range_a : float
            Layer start, measured from the ``outline_a`` face.
        range_b : float
            Layer end, measured from the ``outline_a`` face.
        name : str, optional
        layer_index : int, optional
        agent_configs : list[:class:`~timber_design.populators.LayerAgentConfig`], optional
            Configs whose agents are instantiated on the new layer.  Their beam
            widths are expected to be resolved already; this method calls
            :meth:`~LayerAgentConfig.get_agent_from_layer` without a
            ``standard_beam_width``.

        Returns
        -------
        :class:`Layer`
        """
        if range_a:
            offset = range_a / panel.thickness
            frame_outline_a = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(panel.outline_a.points, panel.outline_b.points)])
        else:
            frame_outline_a = panel.outline_a

        offset = range_b / panel.thickness
        frame_outline_b = Polyline([pt_a * (1.0 - offset) + pt_b * offset for pt_a, pt_b in zip(panel.outline_a.points, panel.outline_b.points)])

        layer = cls.from_outlines(frame_outline_a, frame_outline_b)
        layer.name = name
        layer.layer_index = layer_index
        for agent_config in agent_configs or []:
            layer.agents.append(agent_config.get_agent_from_layer(layer))
        return layer

    def iter_subtree(self):
        """Yield this layer and all descendants depth-first."""
        yield self
        for child in self.sublayer_list:
            yield from child.iter_subtree()
