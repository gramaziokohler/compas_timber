"""ProcessingGroup: several processings which belong together."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import ProcessingGroup

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
holes = [Drilling(start_x=x, start_y=60.0, diameter=30.0, ref_side_index=2) for x in (250.0, 400.0, 550.0)]
beam.add_feature(ProcessingGroup(subprocessings=holes))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
