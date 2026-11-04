"""Renders the examples in `examples/fabrication` to the images of the BTLx processings page of the docs.

An example is a plain script ending in `viewer.show()`. It is run as it is and its scene is then styled: the element is ghosted so that all
its edges show, and the material which the processing removes is added in a colour. `Viewer` is a singleton, which means one process per example.

Needs `compas_viewer`, `compas_brep[occ]` and a display: a window opens for each example. Qt's offscreen platform has no OpenGL.

    python scripts/screenshot_processing_examples.py [example ...]

"""

import os
import pathlib
import runpy
import subprocess
import sys
import traceback

import numpy as np
from compas.colors import Color
from compas_brep import Brep
from compas_viewer import Viewer
from compas_viewer.gl import GL
from PySide6.QtCore import QRect
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLFramebufferObject
from PySide6.QtOpenGL import QOpenGLFramebufferObjectFormat

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLES = ROOT / "examples" / "fabrication"
IMAGES = ROOT / "docs" / "_images" / "processings"

TARGET = [400.0, 0.0, 0.0]
DIRECTION = [650.0, -1000.0, 1000.0]  # from the target to the camera
VIEWS = {"connector": [200.0, -350.0, 1300.0]}  # the examples which need another direction, by name
LENS = 2.6  # how much further the camera is than the direction, with a field of view narrowed to match: less perspective
FIELD_OF_VIEW = 18.0

TIMBER = Color(1.0, 0.72, 0.28, 0.34)
TIMBER_EDGES = Color(0.3, 0.15, 0.03)
REMOVED = Color(0.05, 0.5, 1.0, 0.42)
REMOVED_EDGES = Color(0.0, 0.3, 0.75)
LINE_WIDTH = 5.0  # in pixels of the buffer

BUFFER_SIZE = (4800, 3200)  # rendered larger than the image, as the edges of a window grab are jagged
IMAGE_WIDTH = 1800
MARGIN = 72  # in pixels of the buffer
RENDER_DELAY = 1500  # ms, for the first frames to be drawn


def crop_and_save(image, path):
    """Crop the white space around the element, as the shape of the elements differs from the one of the buffer."""
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    pixels = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, : image.width(), :3]
    rows, columns = np.where(pixels.min(axis=2) < 250)
    if not len(rows):
        raise SystemExit("Nothing was rendered for {}".format(path.stem))
    left, top = max(columns.min() - MARGIN, 0), max(rows.min() - MARGIN, 0)
    width, height = min(columns.max() + MARGIN, image.width()) - left, min(rows.max() + MARGIN, image.height()) - top
    image.copy(QRect(int(left), int(top), int(width), int(height))).scaledToWidth(IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation).save(str(path))


def style(viewer, beam):
    """Ghost the element, draw what the example marks in a colour and add the material the processing removes."""
    for obj in viewer.scene.objects:
        if isinstance(obj.item, Brep):
            obj.facecolor, obj.linecolor, obj.linewidth = TIMBER, TIMBER_EDGES, LINE_WIDTH
        else:
            obj.linecolor, obj.linewidth = REMOVED_EDGES, 2 * LINE_WIDTH

    blank = beam.compute_elementgeometry(include_features=False)
    result = beam.compute_elementgeometry(include_features=True)
    if result.volume < blank.volume - 1.0:
        for piece in Brep.from_boolean_difference(blank, result):
            viewer.scene.add(piece, facecolor=REMOVED, linecolor=REMOVED_EDGES, linewidth=LINE_WIDTH)


def grab(renderer):
    """Paint one frame to a multisampled buffer of `BUFFER_SIZE`, independent of the size of the window."""
    renderer.makeCurrent()
    buffer_format = QOpenGLFramebufferObjectFormat()
    buffer_format.setSamples(8)
    buffer_format.setAttachment(QOpenGLFramebufferObject.Attachment.Depth)
    framebuffer = QOpenGLFramebufferObject(*BUFFER_SIZE, buffer_format)
    framebuffer.bind()
    renderer.width, renderer.height = lambda: BUFFER_SIZE[0], lambda: BUFFER_SIZE[1]
    GL.glViewport(0, 0, *BUFFER_SIZE)
    GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA, GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)  # the alpha of the image stays 1
    renderer.clear()

    # the faces are drawn after the edges they share a plane with, which would otherwise show as a dotted edge
    draw_transparent_faces = renderer.buffer_manager._draw_transparent_faces

    def draw_behind_edges(*args):
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        draw_transparent_faces(*args)
        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    renderer.buffer_manager._draw_transparent_faces = draw_behind_edges
    renderer.paint()
    return framebuffer.toImage()


def render(example):
    path = IMAGES / "{}.png".format(example.stem)
    show = Viewer.show
    Viewer.show = lambda viewer: None
    namespace = runpy.run_path(str(example))
    Viewer.show = show

    viewer, beam = namespace["viewer"], namespace["beam"]
    if beam.debug_info:  # a processing which failed leaves the beam as it is, which would look like a valid image
        raise SystemExit("{}: {}".format(example.stem, beam.debug_info))
    style(viewer, beam)

    viewer.config.renderer.show_grid = False
    viewer.renderer.rendermode = "lighted"
    camera = viewer.renderer.camera
    camera.far, camera.fov, camera.target = 100000.0, FIELD_OF_VIEW, TARGET
    direction = VIEWS.get(example.stem, DIRECTION)
    camera.position = [target + LENS * offset for target, offset in zip(TARGET, direction)]

    def save():
        try:
            crop_and_save(grab(viewer.renderer), path)
        except Exception:  # raised in a Qt callback it would be printed and leave the window open
            traceback.print_exc()
            os._exit(1)
        viewer.app.quit()

    QTimer.singleShot(RENDER_DELAY, save)
    viewer.show()


def main(names):
    IMAGES.mkdir(parents=True, exist_ok=True)
    examples = [EXAMPLES / "{}.py".format(name) for name in names] or sorted(EXAMPLES.glob("*.py"))
    failed = [example.stem for example in examples if subprocess.run([sys.executable, __file__, "--render", str(example)]).returncode]
    if failed:
        raise SystemExit("Failed: {}".format(", ".join(failed)))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--render"]:
        render(pathlib.Path(sys.argv[2]))
    else:
        main(sys.argv[1:])
