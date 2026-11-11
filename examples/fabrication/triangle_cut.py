"""TriangleCut: removes the wedge between two planes through a point."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import TriangleCut

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(TriangleCut(start_x=400.0, start_y=60.0, start_depth=80.0, normal_1_x=-1.0, normal_1_z=1.0, normal_2_x=1.0, normal_2_z=1.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
