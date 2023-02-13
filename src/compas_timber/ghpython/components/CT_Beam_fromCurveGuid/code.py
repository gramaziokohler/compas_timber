import Rhino
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error

from compas_rhino.conversions import RhinoCurve
from compas_rhino.conversions import vector_to_compas

from compas_timber.parts.beam import Beam
from compas_timber.utils.rhino_object_name_attributes import update_rhobj_attributes_name


class BeamFromCurveGuid(component):
    def RunScript(self, CurveIds, ZVector, Width, Height, Category, Group, UpdateAttrs):
        if not CurveIds:
            self.AddRuntimeMessage(Warning, "Input parameter CurveIds failed to collect data")
        if not Width:
            self.AddRuntimeMessage(Warning, "Input parameter Width failed to collect data")
        if not Height:
            self.AddRuntimeMessage(Warning, "Input parameter Height failed to collect data")

        if not (CurveIds and Width and Height):
            # minimal required input
            return None

        ZVector = ZVector or [None]
        Category = Category or [None]
        Group = Group or [None]

        if CurveIds and Width and Height:
            # check list lengths for consistency
            curve_num = len(CurveIds)
            if len(ZVector) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error,
                    " In 'ZVector' I need either none, one or the same number of inputs as the refCrv parameter.",
                )
            if len(Width) not in (1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'Width' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(Height) not in (1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'Height' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(Category) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error,
                    " In 'Category' I need either none, one or the same number of inputs as the refCrv parameter.",
                )
            if len(Group) not in (0, 1, curve_num):
                self.AddRuntimeMessage(
                    Error, " In 'Group' I need either none, one or the same number of inputs as the refCrv parameter."
                )

        # match number of elemets to number of curves
        if len(ZVector) != curve_num:
            ZVector = [ZVector[0]] * curve_num
        if len(Width) != curve_num:
            Width = [Width[0]] * curve_num
        if len(Height) != curve_num:
            Height = [Height[0]] * curve_num
        if len(Category) != curve_num:
            Category = [Category[0]] * curve_num
        if len(Group) != curve_num:
            Group = [Group[0]] * curve_num

        Beams = []
        for guid, z, w, h, c, g in zip(CurveIds, ZVector, Width, Height, Category, Group):
            curve = RhinoCurve.from_object(Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid))
            line = curve.to_compas_line()
            if z:
                z = vector_to_compas(z)
            beam = Beam.from_centerline(line, w, h, z_vector=z)
            beam.attributes["rhino_guid"] = str(guid)
            beam.attributes["category"] = c
            beam.attributes["group"] = g

            if UpdateAttrs:
                update_rhobj_attributes_name(guid, "width", str(w))
                update_rhobj_attributes_name(guid, "height", str(h))
                update_rhobj_attributes_name(guid, "zaxis", str(list(beam.frame.zaxis)))
                update_rhobj_attributes_name(guid, "category", c)

            Beams.append(beam)
        return Beams
