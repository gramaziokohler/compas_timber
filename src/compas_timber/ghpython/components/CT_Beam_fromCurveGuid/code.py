import Rhino
from compas_rhino.conversions import RhinoCurve
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.parts.beam import Beam as ctBeam


class Beam_fromCurveGuid(component):
    def RunScript(self, RefCenterline, ZVector, Width, Height, Category, updateRefObj):
        if not RefCenterline:
            self.AddRuntimeMessage(Warning, "Input parameter RefCenterline failed to collect data")
        if not Width:
            self.AddRuntimeMessage(Warning, "Input parameter Width failed to collect data")
        if not Height:
            self.AddRuntimeMessage(Warning, "Input parameter Height failed to collect data")

        if not (RefCenterline and Width and Height):
            # minimal required input
            return None

        ZVector = ZVector or [None]
        Category = Category or [None]

        if RefCenterline and Height and Height:
            # check list lengths for consistency
            N = len(RefCenterline)
            if len(ZVector) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error,
                    " In 'ZVector' I need either none, one or the same number of inputs as the refCrv parameter.",
                )
            if len(Width) not in (1, N):
                self.AddRuntimeMessage(
                    Error, " In 'Width' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(Height) not in (1, N):
                self.AddRuntimeMessage(
                    Error, " In 'Height' I need either one or the same number of inputs as the refCrv parameter."
                )
            if len(Category) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error,
                    " In 'Category' I need either none, one or the same number of inputs as the refCrv parameter.",
                )

        # match number of elemets to number of curves
        if len(ZVector) != N:
            ZVector = [ZVector[0]] * N
        if len(Width) != N:
            Width = [Width[0]] * N
        if len(Height) != N:
            Height = [Height[0]] * N
        if len(Category) != N:
            Category = [Category[0]] * N

        beams = []
        for guid, z, w, h, c in zip(RefCenterline, ZVector, Width, Height, Category):
            curve = RhinoCurve.from_object(Rhino.RhinoDoc.ActiveDoc.Objects.FindId(guid))
            line = curve.to_compas_line()
            if z:
                z = vector_to_compas(z)
            beam = ctBeam.from_centerline(line, w, h, z_vector=z)
            beam.attributes["rhino_guid"] = str(guid)
            beam.attributes["category"] = c

            if updateRefObj:
                update_rhobj_attributes_name(guid, "width", str(w))
                update_rhobj_attributes_name(guid, "height", str(h))
                update_rhobj_attributes_name(guid, "zvector", str(list(beam.frame.zaxis)))
                update_rhobj_attributes_name(guid, "category", c)

            beams.append(beam)
        Beam = beams
        return Beam
