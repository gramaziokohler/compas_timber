"""HouseMortise: a mortise which holds a second, nested mortise or dovetail mortise."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import HouseMortise
from compas_timber.fabrication import Mortise

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
mortise = Mortise(start_x=350.0, start_y=60.0, start_depth=30.0, length=60.0, width=30.0, depth=60.0, shape="square", ref_side_index=2)
beam.add_feature(HouseMortise(start_x=320.0, start_y=60.0, start_depth=0.0, length=120.0, width=70.0, depth=30.0, shape="square", subprocessings=[mortise], ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
