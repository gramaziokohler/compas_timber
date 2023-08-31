import uuid
#from compas_timber.assembly import TimberAssembly
import xml.dom.minidom
class BTLx:


    def add_process(self, processings, process):
        if process == 0:
            jack_cut = ET.Element(
                "JackRafterCut", Name="Jack cut", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2"
            )
            orientation = ET.SubElement(jack_cut, "Orientation")
            orientation.text = "end"
            start_x = ET.SubElement(jack_cut, "StartX")
            start_x.text = "1402.659"
            start_y = ET.SubElement(jack_cut, "StartY")
            start_y.text = "0"
            start_depth = ET.SubElement(jack_cut, "StartDepth")
            start_depth.text = "0"
            angle = ET.SubElement(jack_cut, "Angle")
            angle.text = "55"
            inclination = ET.SubElement(jack_cut, "Inclination")
            inclination.text = "90"
            processings.insert(1, jack_cut)

        elif process == 1:
            mortise = ET.Element(
                "Mortise", Name="Mortise", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2"
            )
            processings.insert(1, mortise)
        else:
            tenon = ET.Element("Tenon", Name="Tenon", Process="yes", Priority="0", ProcessID="4", ReferencePlaneID="2")
            processings.insert(1, tenon)

    class XmlElement:
        name = ""
        text = ""
        attributes = []
        subelements = []

        def __init__(self, name, text = "", attributes = [], subelements = []):
            self.name = name
            self.text = text
            self.attributes = attributes
            self.subelements = subelements


        def __str__(self) -> str:
            string = "<{} {}> {} {} </{}> "

            attribute_text = ""
            for att in self.attributes:
                attribute_text += att.__str__()

            subelement_text = ""
            for subelement in self.subelements:
                subelement_text += subelement.__str__()


            string = string.format(self.name, attribute_text, subelement_text, self.text, self.name)
            return string

        class Attribute:
            name = ""
            value = ""

            def __init__(self, name, value = ""):
                self.name = name
                self.value = value
                pass

            def __str__(self) -> str:
                string = self.name
                string += "=\""+self.value+ "\" "
                return string




    def __init__(self, assembly):







        print("NOW OK")

        root = ET.Element("BTLx")
        print("NOW DO EVEN BETTER!")

        project = ET.SubElement(root, "Project")
        parts = ET.SubElement(project, "Parts")

        beams = assembly.beams

        for beam in beams:
            a = 0
            BTLx_corner_reference_point = (
                beam.frame.point
                - (beam.frame.yaxis * beam.width)
                - np.cross(beam.frame.xaxis, beam.frame.yaxis) * beam.height
            )
            part = ET.SubElement(
                parts,
                "Part",
                SingleMemberNumber="",
                AssemblyNumber="",
                OrderNumber="",
                Designation="",
                Annotation="",
                Storey="",
                Group="",
                Package="",
                Material="",
                TimberGrade="",
                QualityGrade="",
                Count="1",
                Length="",
                Height="",
                Width="",
                PlaningLength="0",
                Weight="0",
                ProcessingQuality="automatic",
                StoreyType="",
                ElementNumber="00",
                Layer="0",
                ModuleNumber="",
            )
            part.set("SingleMemberNumber", str(a))
            part.set("Length", str(beam.length))
            part.set("Width", str(beam.width))
            part.set("Height", str(beam.height))

            transformations = ET.SubElement(part, "Transformations")
            guid = str(uuid.uuid4())
            transformation = ET.SubElement(transformations, "Transformation", GUID=guid)
            position = ET.SubElement(transformation, "Position")

            reference_point = ET.SubElement(position, "ReferencePoint", X="", Y="", Z="")
            reference_point.set("X", str(BTLx_corner_reference_point.x))
            reference_point.set("Y", str(BTLx_corner_reference_point.y))
            reference_point.set("Z", str(BTLx_corner_reference_point.z))

            x_vector = ET.SubElement(position, "XVector", X="", Y="", Z="")
            x_vector.set("X", str(beam.frame.xaxis.x))
            x_vector.set("Y", str(beam.frame.xaxis.y))
            x_vector.set("Z", str(beam.frame.xaxis.z))

            y_vector = ET.SubElement(position, "YVector", X="", Y="", Z="")
            y_vector.set("X", str(beam.frame.yaxis.x))
            y_vector.set("Y", str(beam.frame.yaxis.y))
            y_vector.set("Z", str(beam.frame.yaxis.z))

            grain_direction = ET.SubElement(part, "GrainDirection", X="1", Y="0", Z="0", Align="no")
            reference_side = ET.SubElement(part, "ReferenceSide", Side="3", Align="no")

            processings = ET.SubElement(part, "Processings")
            i=0
            for feature in beam.features:
                self.add_process(processings, i)
                i = i+1

            shape = ET.SubElement(part, "Shape")
            indexed_face_set = ET.SubElement(shape, "IndexedFaceSet", convex="", coorIndex="")
            coordinate = ET.SubElement(indexed_face_set, "Coordinate", point="")

            a = a + 1
        return root

    def writeBTLx(self, path):
        self.write(open(path + ".btlx", "wb", encoding="utf-8"))

attributes = [BTLx.XmlElement.Attribute("A", "1.0"), BTLx.XmlElement.Attribute("B", "2.0") ]
subelements = [BTLx.XmlElement("subelement1", "subText1"),BTLx.XmlElement("subelement2", "subText2")]



btlx = BTLx.XmlElement("newBTLX", "sampleText", attributes, subelements)

print(btlx.__str__())
print(xml.dom.minidom.parseString(btlx.__str__()).toprettyxml())
# pretty print generated XML
