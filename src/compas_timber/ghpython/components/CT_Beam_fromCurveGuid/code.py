import Rhino
from compas_rhino.conversions import RhinoCurve
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.parts.beam import Beam
from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name


class BeamFromCurveGuid(component):
    def RunScript(self, curve_ids, width, height, z_vector, category, group, update_attrs):

        if not curve_ids:
            self.AddRuntimeMessage(Warning, "Input parameter curve_ids failed to collect data")
        if not width:
            self.AddRuntimeMessage(Warning, "Input parameter width failed to collect data")
        if not height:
            self.AddRuntimeMessage(Warning, "Input parameter height failed to collect data")

        if not (curve_ids and width and height):
            # minimal required input
            return

        z_vector = z_vector or [None]
        category = category or [None]
        group = group or [None]

        if curve_ids and height and height:
            # check list lengths for consistency
            curve_num = len(curve_ids)
            if len(z_vector) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error,
                    " In 'z_vector' I need either none, one or the same number of inputs as the refCrv parameter.",
                )
            if len(width) not in (1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'width' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(height) not in (1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'height' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(category) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error,
                    " In 'category' I need either none, one or the same number of inputs as the refCrv parameter.",
                )
            if len(group) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'group' I need either none, one or the same number of inputs as the refCrv parameter."
                )

        # match number of elemets to number of curves
        if len(z_vector) != curve_num:
            z_vector = [z_vector[0]] * curve_num
        if len(width) != curve_num:
            width = [width[0]] * curve_num
        if len(height) != curve_num:
            height = [height[0]] * curve_num
        if len(category) != curve_num:
            category = [category[0]] * curve_num
        if len(group) != curve_num:
            group = [group[0]] * curve_num

        beams = []
        for guid, z, w, h, c, g in zip(curve_ids, z_vector, width, height, category, group):
            curve = RhinoCurve.from_object(Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid))
            line = curve.to_compas_line()
            if z:
                z = vector_to_compas(z)
            beam = Beam.from_centerline(line, w, h, z_vector=z)
            beam.attributes["rhino_guid"] = str(guid)
            beam.attributes["category"] = c
            beam.attributes["group"] = g

            if update_attrs:
                update_rhobj_attributes_name(guid, "width", str(w))
                update_rhobj_attributes_name(guid, "height", str(h))
                update_rhobj_attributes_name(guid, "zaxis", str(list(beam.frame.zaxis)))
                update_rhobj_attributes_name(guid, "category", c)

            beams.append(beam)
        return beams
