"""Connector: a connector with the processings which make room for it, here a lap and a drilling."""

from compas.geometry import Frame
from compas_viewer import Viewer

from compas_timber.elements import Beam
from compas_timber.fabrication import Connector
from compas_timber.fabrication import ConnectorInfo
from compas_timber.fabrication import ConnectorParameter
from compas_timber.fabrication import Drilling
from compas_timber.fabrication import Lap

beam = Beam(Frame.worldXY(), length=800.0, width=120.0, height=200.0)
lap = Lap(start_x=300.0, start_y=30.0, length=200.0, width=60.0, depth=40.0, ref_side_index=2)
hole = Drilling(start_x=400.0, start_y=60.0, diameter=20.0, ref_side_index=2)
info = ConnectorInfo("plate", Frame.worldXY(), [ConnectorParameter("Depth", 40.0)])
beam.add_feature(Connector(connector_info=info, subprocessings=[lap, hole]))

viewer = Viewer()
viewer.scene.add(beam.compute_elementgeometry(include_features=True))
viewer.show()
