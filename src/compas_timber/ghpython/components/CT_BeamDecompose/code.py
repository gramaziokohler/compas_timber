# flake8: noqa
from compas.geometry import Line
from compas_rhino.conversions import frame_to_rhino_plane
from compas_rhino.conversions import line_to_rhino
from compas_rhino.conversions import point_to_rhino
from compas_rhino.conversions import box_to_rhino
from ghpythonlib.componentbase import executingcomponent as component
from System.Drawing import Color


class BeamDecompose(component):
    RED = Color.FromArgb(255, 255, 100, 100)
    GREEN = Color.FromArgb(200, 50, 220, 100)
    BLUE = Color.FromArgb(200, 50, 150, 255)
    WHITE = Color.FromArgb(255, 255, 255, 255)
    YELLOW = Color.FromArgb(255, 255, 255, 0)
    SCREEN_SIZE = 10
    RELATIVE_SIZE = 0

    def RunScript(self, beam, show_frame, show_faces):
        self.show_faces = show_faces if show_faces is not None else False
        self.show_frame = show_frame if show_frame is not None else False
        self.frames = []
        self.rhino_frames = []
        self.scales = []
        self.faces = []
        self.width = []
        self.height = []
        self.centerline = []
        self.shapes = []

        for b in beam:
            self.frames.append(b.frame)
            self.rhino_frames.append(frame_to_rhino_plane(b.frame))
            self.scales.append(b.width + b.height)
            self.centerline.append(line_to_rhino(b.centerline))
            self.shapes.append(box_to_rhino(b.shape))
            self.width.append(b.width)
            self.height.append(b.height)
            self.faces.append(b.faces)

        return self.rhino_frames, self.centerline, self.shapes, self.width, self.height

    def DrawViewportWires(self, arg):
        if self.Locked:
            return

        for f, s, faces in zip(self.frames, self.scales, self.faces):
            if self.show_frame:
                self._draw_frame(arg.Display, f, s)
            if self.show_faces:
                self._draw_faces(arg.Display, faces, s)

    def _draw_frame(self, display, frame, scale):
        x = Line.from_point_and_vector(frame.point, frame.xaxis * scale)
        y = Line.from_point_and_vector(frame.point, frame.yaxis * scale)
        z = Line.from_point_and_vector(frame.point, frame.zaxis * scale)
        display.DrawArrow(line_to_rhino(x), self.RED, self.SCREEN_SIZE, self.RELATIVE_SIZE)
        display.DrawArrow(line_to_rhino(y), self.GREEN, self.SCREEN_SIZE, self.RELATIVE_SIZE)
        display.DrawArrow(line_to_rhino(z), self.BLUE, self.SCREEN_SIZE, self.RELATIVE_SIZE)

        x_loc = x.end + x.vector * scale * 1.1
        y_loc = y.end + y.vector * scale * 1.1
        z_loc = z.end + z.vector * scale * 1.1
        display.Draw2dText("X", self.RED, point_to_rhino(x_loc), True, 16, "Verdana")
        display.Draw2dText("Y", self.GREEN, point_to_rhino(y_loc), True, 16, "Verdana")
        display.Draw2dText("Z", self.BLUE, point_to_rhino(z_loc), True, 16, "Verdana")

    def _draw_faces(self, display, faces, scale):
        for index, face in enumerate(faces):
            normal = Line.from_point_and_vector(face.point, face.normal * scale)
            text = str(index)
            display.Draw2dText(text, self.WHITE, point_to_rhino(face.point), True, 16, "Verdana")
            display.DrawArrow(line_to_rhino(normal), self.YELLOW, self.SCREEN_SIZE, self.RELATIVE_SIZE)
