"""FreeSurface: removes everything above a NURBS surface."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import FreeSurface
from compas_timber.fabrication import NurbsPatch

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
points = [[x, y, z] for y in (-20.0, 140.0) for x, z in ((-20.0, -20.0), (400.0, -120.0), (820.0, -20.0))]
beam.add_feature(FreeSurface(surface=NurbsPatch(points, [1.0] * 6, [0.0, 0.0, 1.0, 1.0], [0.0, 1.0], 2, 1, 3, 2), ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
