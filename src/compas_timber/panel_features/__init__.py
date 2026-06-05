from .panel_features import PanelFeature
from .panel_features import PanelFeatureType
from .panel_connection_interface import PanelConnectionInterface
from .panel_connection_interface import InterfaceRole
from .opening import Opening
from .opening import OpeningType


# ``Layer`` lives in this package but inherits from ``compas_timber.elements.panel.Panel``,
# which in turn imports symbols from this package at module load time.  Importing
# ``.layer`` at the top of this file would close that cycle.  We use a PEP-562
# module-level ``__getattr__`` to expose ``Layer`` lazily — ``from
# compas_timber.panel_features import Layer`` works without forcing the
# ``Panel`` ↔ ``Layer`` module-load cycle.
def __getattr__(name):
    if name == "Layer":
        from .layer import Layer

        return Layer
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))


__all__ = [
    "PanelFeature",
    "PanelFeatureType",
    "PanelConnectionInterface",
    "InterfaceRole",
    "Opening",
    "OpeningType",
    "Layer",
]
