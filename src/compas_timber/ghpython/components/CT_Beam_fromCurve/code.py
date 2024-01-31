"""Creates a Beam from a LineCurve."""

from compas.geometry import Line
from compas.scene import Scene
from compas_rhino.conversions import curve_to_compas
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning
from Rhino.RhinoDoc import ActiveDoc

from compas_timber.ghpython.rhino_object_name_attributes import update_rhobj_attributes_name
from compas_timber.parts import Beam as CTBeam


class Beam_fromCurve(component):
    def RunScript(self, Centerline, ZVector, Width, Height, Category, updateRefObj):
        # minimum inputs required
        if not Centerline:
            self.AddRuntimeMessage(Warning, "Input parameter 'Centerline' failed to collect data")
        if not Width:
            self.AddRuntimeMessage(Warning, "Input parameter 'Width' failed to collect data")
        if not Height:
            self.AddRuntimeMessage(Warning, "Input parameter 'Height' failed to collect data")

        # reformat unset parameters for consistency
        if not ZVector:
            ZVector = [None]
        if not Category:
            Category = [None]

        Beam = []
        Blank = []
        scene = Scene()

        if Centerline and Height and Width:
            # check list lengths for consistency
            N = len(Centerline)
            if len(ZVector) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error, " In 'ZVector' I need either none, one or the same number of inputs as the Crv parameter."
                )
            if len(Width) not in (1, N):
                self.AddRuntimeMessage(
                    Error, " In 'W' I need either one or the same number of inputs as the Crv parameter."
                )
            if len(Height) not in (1, N):
                self.AddRuntimeMessage(
                    Error, " In 'H' I need either one or the same number of inputs as the Crv parameter."
                )
            if len(Category) not in (0, 1, N):
                self.AddRuntimeMessage(
                    Error, " In 'Category' I need either none, one or the same number of inputs as the Crv parameter."
                )

            # duplicate data if None or single value
            if len(ZVector) != N:
                ZVector = [ZVector[0] for _ in range(N)]
            if len(Width) != N:
                Width = [Width[0] for _ in range(N)]
            if len(Height) != N:
                Height = [Height[0] for _ in range(N)]
            if len(Category) != N:
                Category = [Category[0] for _ in range(N)]

            for guid, z, w, h, c in zip(Centerline, ZVector, Width, Height, Category):
                curve = curve_to_compas(ActiveDoc.Objects.FindId(guid))
                line = Line(curve.start, curve.end)
                z = vector_to_compas(z) if z else None
                beam = CTBeam.from_centerline(centerline=line, width=w, height=h, z_vector=z)
                beam.attributes["rhino_guid"] = str(guid)
                beam.attributes["category"] = c

                if updateRefObj:
                    update_rhobj_attributes_name(guid, "width", str(w))
                    update_rhobj_attributes_name(guid, "height", str(h))
                    update_rhobj_attributes_name(guid, "zvector", str(list(beam.frame.zaxis)))
                    update_rhobj_attributes_name(guid, "category", c)

                Beam.append(beam)
                scene.add(beam.blank)

        Blank = scene.draw()

        return Beam, Blank
