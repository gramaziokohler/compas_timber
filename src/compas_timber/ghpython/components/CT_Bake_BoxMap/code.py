# flake8: noqa
import math
import random

import scriptcontext as sc
import Rhino
import rhinoscriptsyntax as rs
from compas_rhino.conversions import frame_to_rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino import Render
from Rhino.Geometry import Interval
from Rhino.Geometry import Plane
from Rhino.RhinoDoc import ActiveDoc


class BakeBoxMap(component):
    def RunScript(self, model, beam_map_size, plate_map_size, beam_layer_name, plate_layer_name, swap_uv, bake):
        def get_dimensions(map_size, default):
            return map_size if map_size else default

        # Check if model exists and baking is enabled
        if not model:
            self.AddRuntimeMessage(Warning, "Input parameters Model failed to collect any Beam objects.")
            return

        if not bake:  # Exit early if bake is False
            return

        # Save current Grasshopper document context
        ghdoc = sc.doc

        try:
            # Switch document context to Rhino's active document for baking
            sc.doc = Rhino.RhinoDoc.ActiveDoc

            # Define dimensions
            b_dimx, b_dimy, b_dimz = get_dimensions(beam_map_size, [0.2, 0.2, 1.0])
            p_dimx, p_dimy, p_dimz = get_dimensions(plate_map_size, [1.0, 1.0, 1.0])

            # Bake beams
            beam_frames = [frame_to_rhino(b.frame) for b in model.beams]
            beam_breps = [beam.geometry.native_brep for beam in model.beams]
            self.add_brep_to_document(beam_breps, beam_frames, beam_layer_name, b_dimx, b_dimy, b_dimz, False)

            # Bake plates
            plate_frames = [frame_to_rhino(p.frame) for p in model.plates]
            plate_breps = [plate.geometry.native_brep for plate in model.plates]
            self.add_brep_to_document(plate_breps, plate_frames, plate_layer_name, p_dimx, p_dimy, p_dimz, swap_uv)

        finally:
            # Restore document context back to Grasshopper
            sc.doc = ghdoc

            rs.EnableRedraw(True)


    @staticmethod
    def create_box_map(pln, sx, sy, sz, swap_uv):
        """
        pln: frame of beam box, where x=main axis, y=width, z=height
        sx,sy,sz: box map size in x,y,z direction
        """

        v = pln.YAxis
        w = pln.ZAxis
        pt = pln.Origin

        # Apply random deviation
        v.Rotate(BakeBoxMap.random_rotation_angle(math.pi * 0.5), pln.XAxis)
        w.Rotate(BakeBoxMap.random_rotation_angle(math.pi * 0.01), pln.XAxis)

        randpos = sx * random.random()
        pt += pln.XAxis * randpos

        # create box mapping
        mappingPln = Plane(pt, w, v)
        dx = Interval(-sx * 0.5, sx * 0.5)
        dy = Interval(-sy * 0.5, sy * 0.5)
        dz = Interval(-sz * 0.5, sz * 0.5)
        if swap_uv:
            mappingPln.Rotate(math.radians(90), mappingPln.XAxis)

        BoxMap = Render.TextureMapping.CreateBoxMapping(mappingPln, dx, dy, dz, False)

        return BoxMap

    @staticmethod
    def add_brep_to_document(breps, frames, layer_name, b_dimx, b_dimy, b_dimz, swap_uv):
        if frames and breps:
            rs.EnableRedraw(False)

            for brep, frame in zip(breps, frames):
                guid = sc.doc.Objects.Add(brep)
                if layer_name:
                    BakeBoxMap.ensure_layer_exists(layer_name)
                    rs.ObjectLayer(guid, layer_name)
                boxmap = BakeBoxMap.create_box_map(frame, b_dimx, b_dimy, b_dimz, swap_uv)
                sc.doc.Objects.ModifyTextureMapping(guid, 1, boxmap)

    @staticmethod
    def ensure_layer_exists(layer_name):
        if not rs.IsLayer(layer_name):
            rs.AddLayer(layer_name)

    @staticmethod
    def random_rotation_angle(max_angle):
        return (random.random() - 0.5) * max_angle
