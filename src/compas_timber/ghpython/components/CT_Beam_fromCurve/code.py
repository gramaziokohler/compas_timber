"""Creates a Beam from a LineCurve."""
import Rhino.Geometry as rg
from compas_rhino.conversions import line_to_compas
from compas_rhino.conversions import vector_to_compas
from ghpythonlib.componentbase import executingcomponent as component
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Error
from Grasshopper.Kernel.GH_RuntimeMessageLevel import Warning

from compas_timber.parts.beam import Beam as ctBeam
from compas.scene import Scene


class Beam_fromCurve(component):
    def RunScript(self, Centerline, ZVector, Width, Height, Category):
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

            for crv, z, w, h, c in zip(Centerline, ZVector, Width, Height, Category):
                if crv is None or w is None or h is None:
                    self.AddRuntimeMessage(Warning, "Some of the input values are Null")
                else:
                    line = rg.Line(crv.PointAtStart, crv.PointAtEnd)

                    line = line_to_compas(line)
                    if z:
                        z = vector_to_compas(z)
                    else:
                        None

                    beam = ctBeam.from_centerline(centerline=line, width=w, height=h, z_vector=z)

                    beam.attributes["rhino_guid"] = None
                    beam.attributes["category"] = c

                    Beam.append(beam)
                    scene.add(beam.blank)
        Blank = scene.redraw()

        return Beam, Blank
