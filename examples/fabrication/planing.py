"""Planing: removes a layer from the sides of the element."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Planing

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(Planing(start_x=200.0, start_limited=True, end_limited=True, length=400.0, depth=15.0))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
