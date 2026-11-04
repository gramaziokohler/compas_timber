"""LockoutArea: an area where processes are not allowed, which leaves the volume as it is. Its outline is drawn for this image."""

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import LockoutArea
from compas_timber.fabrication import SimpleContour

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
outline = Polyline([[200.0, 20.0, 0.0], [500.0, 20.0, 0.0], [500.0, 100.0, 0.0], [200.0, 100.0, 0.0], [200.0, 20.0, 0.0]])
beam.add_feature(LockoutArea(contour=SimpleContour(outline), for_sawing=False, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
side = Transformation.from_frame(beam.ref_sides[2])
viewer.scene.add(outline.transformed(side), linecolor=Color.red(), linewidth=3)
viewer.show()
