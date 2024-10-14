# flake8: noqa
import math
import random

import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
from compas_rhino.conversions import frame_to_rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error, Warning
from Rhino import Render
from Rhino.Geometry import Interval, Plane


class BakeBeamBoxMap(component):
    def RunScript(self, model_list, map_size, layer_name, clear_layer_content, bake):
        if map_size and len(map_size) != 3:
            self.AddRuntimeMessage(
                Error, "Input parameter MapSize requires exactly three float values (scale factors in x,y,z directions)"
            )
            return

        if map_size:
            dimx, dimy, dimz = map_size
        else:
            # For the pine 251 material bitmap, rotated
            dimx = 0.2
            dimy = 0.2
            dimz = 1.0

        if not model_list:
            self.AddRuntimeMessage(Warning, "Input parameters Model failed to collect any Beam objects.")
            return

        if not bake:
            return

        try:
            # Switch document context to Rhino's active document for baking
            sc.doc = Rhino.RhinoDoc.ActiveDoc

            # Set layer name to active layer if none is defided
            if not layer_name:
                layer_name = sc.doc.Layers.CurrentLayer.FullPath

            # Ensure layer exists and clear it if specified
            self.ensure_layer_exists(layer_name)
            if clear_layer_content:
                self.delete_objects_on_layer(layer_name)

            for model in model_list:
                if hasattr(model, "beams"):
                    frames = [frame_to_rhino(b.frame) for b in model.beams]
                    breps = [beam.geometry.native_brep for beam in model.beams]

                    if frames and breps:
                        rs.EnableRedraw(False)
                        for brep, frame in zip(breps, frames):
                            # Add brep to the document
                            guid = sc.doc.Objects.Add(brep)
                            if layer_name:
                                rs.ObjectLayer(guid, layer_name)

                            # Create box mapping and apply it
                            boxmap = self.create_box_map(frame, dimx, dimy, dimz)
                            sc.doc.Objects.ModifyTextureMapping(guid, 1, boxmap)
        finally:
            # Restore document context back to Grasshopper
            sc.doc = ghdoc
            rs.EnableRedraw(True)

    @staticmethod
    def create_box_map(pln, sx, sy, sz):
        """
        pln: frame of beam box, where x=main axis, y=width, z=height
        sx,sy,sz: box map size in x,y,z direction
        """

        v = pln.YAxis
        w = pln.ZAxis
        pt = pln.Origin

        # Random deviation
        a = math.pi * 0.5
        randangle = (random.random() - 0.5) * a
        v.Rotate(randangle, pln.XAxis)

        b = math.pi * 0.01
        randangle = (random.random() - 0.5) * b
        w.Rotate(randangle, pln.XAxis)

        randpos = sx * random.random()
        pt += pln.XAxis * randpos

        # Create box mapping
        mapping_pln = Plane(pt, w, v)
        dx = Interval(-sx * 0.5, sx * 0.5)
        dy = Interval(-sy * 0.5, sy * 0.5)
        dz = Interval(-sz * 0.5, sz * 0.5)

        box_map = Render.TextureMapping.CreateBoxMapping(mapping_pln, dx, dy, dz, False)

        return box_map

    @staticmethod
    def ensure_layer_exists(layer_name):
        """Ensure that the specified layer exists in the Rhino document, if not create it."""
        if not rs.IsLayer(layer_name):
            rs.AddLayer(layer_name)

    @staticmethod
    def delete_objects_on_layer(layer_name):
        """Delete all objects on the specified layer."""
        object_ids = rs.ObjectsByLayer(layer_name)
        rs.DeleteObjects(object_ids)
