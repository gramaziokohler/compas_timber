"""House: a tenon which holds a second, nested tenon or dovetail tenon on its face."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import House
from compas_timber.fabrication import Tenon

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
tenon = Tenon(orientation="end", start_x=680.0, start_y=60.0, start_depth=60.0, length=80.0, width=40.0, height=70.0, shape="square", ref_side_index=2)
beam.add_feature(
    House(orientation="end", start_x=650.0, start_y=60.0, start_depth=20.0, length=160.0, width=90.0, height=30.0, shape="square", subprocessings=[tenon], ref_side_index=2)
)

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
