"""SawContour: a contour which is cut with a saw blade."""

from compas.geometry import Frame
from compas.geometry import Polyline
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Contour
from compas_timber.fabrication import SawContour

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
outline = Polyline([[200.0, 20.0, 0.0], [500.0, 20.0, 0.0], [500.0, 100.0, 0.0], [200.0, 100.0, 0.0], [200.0, 20.0, 0.0]])
beam.add_feature(SawContour(Contour(outline, 60.0), tool_position="left", ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
