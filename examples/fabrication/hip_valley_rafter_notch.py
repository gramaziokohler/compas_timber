"""HipValleyRafterNotch: the notch of a rafter on a hip or a valley rafter."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import HipValleyRafterNotch

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(HipValleyRafterNotch(start_x=300.0, start_y=60.0, start_depth=40.0, angle_ref_edge=50.0, angle_opp_edge=50.0, inclination=20.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
