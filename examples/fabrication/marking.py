"""Marking: a line on the element, which leaves its volume as it is. The line is drawn for this image."""

from compas.colors import Color
from compas.geometry import Frame
from compas.geometry import Line
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Marking

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
line = Line([200.0, -30.0, 100.0], [600.0, 30.0, 100.0])
beam.add_feature(Marking.from_line_and_element(line, beam, ref_side_index=2))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.scene.add(line, linecolor=Color.red(), linewidth=3)
viewer.show()
