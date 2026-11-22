"""PenContour: a path drawn on the element, which leaves its volume as it is. The path is drawn for this image."""

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import PenContour
from compas_timber.fabrication import SimpleContour

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
path = Polyline([[150.0, 30.0, 0.0], [650.0, 30.0, 0.0], [650.0, 90.0, 0.0]])
beam.add_feature(PenContour(contour=SimpleContour(path), ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
side = Transformation.from_frame(beam.ref_sides[2])
viewer.scene.add(path.transformed(side), linecolor=Color.red(), linewidth=3)
viewer.show()
