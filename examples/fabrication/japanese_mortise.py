"""JapaneseMortise: the mortise of a Japanese scarf joint, the counterpart of JapaneseTenon."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import JapaneseMortise

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
beam.add_feature(JapaneseMortise(orientation="end", start_x=650.0, start_y=60.0, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
