"""SawCut: a straight cut of a saw blade, limited in length and depth."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import SawCut

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(SawCut(start_x=300.0, start_y=20.0, angle=90.0, length=80.0, depth=60.0, tool_position="center", ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
