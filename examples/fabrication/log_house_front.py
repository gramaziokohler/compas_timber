"""LogHouseFront: the visible end of a log, narrowed from its edges."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import LogHouseFront

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(LogHouseFront(orientation="end", start_x=700.0, start_depth=40.0, length=120.0, depth_ref_edge=25.0, depth_opp_edge=25.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
