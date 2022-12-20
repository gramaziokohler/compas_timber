from compas.geometry import Frame
from compas.geometry import Brep
from compas.geometry import Transformation
from compas_future.datastructures import GeometricFeature
from compas_future.datastructures import ParametricFeature


def trim_brep_with_frame(brep, frame):
    brep.trim(frame)


class BeamTrimmingFeature(GeometricFeature):
    
    OPERATIONS = {Brep: trim_brep_with_frame}
    
    def __init__(self, trimming_plane):
        super(BeamTrimmingFeature, self).__init__()
        self._geometry = trimming_plane

    def apply(self, part):
        part_geometry = part.get_geometry(with_features=True)
        if not isinstance(part_geometry, Brep):
            raise ValueError("Brep feature {} cannot be applied to part with non Brep geometry {}".format(self, part))
        g_copy = part_geometry.copy()
        operation = self.OPERATIONS[Brep]
        operation(g_copy, self._geometry)
        return g_copy

