from __future__ import annotations

from compas_timber.utils import StrEnum
from typing import Optional

from compas.geometry import Polyline
from compas.tolerance import TOL
from compas_timber.elements import Panel

class PanelLayerPosition(StrEnum):
    """Enumeration of the panel layer positions.

    Attributes
    ----------
    INTERIOR : "interior"
        A layer that is not on the exterior of the cross-section.
    CORE : "core"
        A layer that is on the interior of the cross-section, typically containing structural elements.
    EXTERIOR : "exterior"
        A layer that is on the exterior of the cross-section, typically containing insulation, cladding, etc.
    """
    INTERIOR = "interior"
    CORE = "core"
    EXTERIOR = "exterior"


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
