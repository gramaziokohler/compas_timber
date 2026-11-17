"""Variant: a set of parameters whose meaning is up to the receiver of the file. It has no geometry, a line at its start point is drawn for this image."""

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Transformation
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Variant
from compas_timber.fabrication import VariantParameter

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(Variant(start_x=400.0, start_y=60.0, parameters=[VariantParameter("Type", "custom")], ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
side = Transformation.from_frame(beam.ref_sides[2])
viewer.scene.add(Line([400.0, 60.0, 0.0], [400.0, 60.0, 100.0]).transformed(side), linecolor=Color.red(), linewidth=3)
viewer.show()
