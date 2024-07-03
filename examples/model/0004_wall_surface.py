from compas.scene import Scene
from compas.geometry import Brep
from compas.geometry import Surface
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Plane
from compas.geometry import Vector
from compas_timber.design import SurfaceModel
from compas_timber.design import DebugInfomation

from compas_viewer.viewer import Viewer

from compas_occ.geometry import OCCSurface


def create_viewer():
    viewer = Viewer()
    viewer.renderer.camera.far = 1000000.0
    viewer.renderer.camera.position = [10000.0, 10000.0, 10000.0]
    viewer.renderer.camera.pan_delta = 5.0
    viewer.renderer.rendermode = "ghosted"
    return viewer


frame = Frame(
    point=Point(x=0.0, y=-6000.0, z=-7000.0), xaxis=Vector(x=0.0, y=1.0, z=0.0), yaxis=Vector(x=-0.0, y=0.0, z=1.0)
)
surface = OCCSurface.from_plane(Plane.from_frame(frame))

viewer = create_viewer()
viewer.scene.add(surface.to_brep())
viewer.show()
# minimum inputs required

# if not surface:
#     return
# if not isinstance(surface, RhinoBrep):
#     raise TypeError("Expected a compas.geometry.Surface, got: {}".format(type(surface)))
# if not stud_spacing:
#     self.AddRuntimeMessage(Warning, "Input parameter 'spacing' failed to collect data")
# if not isinstance(stud_spacing, float):
#     raise TypeError("stud_spacing expected a float, got: {}".format(type(stud_spacing)))
# if z_axis is not None and not isinstance(z_axis, RhinoVector):
#     raise TypeError("Expected a compas.geometry.Vector, got: {}".format(type(z_axis)))

# # reformat unset parameters for consistency
# if not z_axis:
#     z_axis = None
# if not options:
#     options = {}

# assembly = SurfaceAssembly(Brep.from_native(surface), stud_spacing, beam_width, frame_depth, z_axis, **options)

# debug_info = DebugInfomation()
# Geometry = None
# scene = Scene()
# if CreateGeometry:
#     vis_consumer = BrepGeometryConsumer(assembly.assembly)
#     for result in vis_consumer.result:
#         scene.add(result.geometry)
#         if result.debug_info:
#             debug_info.add_feature_error(result.debug_info)
# else:
#     for beam in assembly.beams:
#         scene.add(beam.blank)

# if debug_info.has_errors:
#     self.AddRuntimeMessage(Warning, "Error found during joint creation. See DebugInfo output for details.")

# Geometry = scene.draw()
