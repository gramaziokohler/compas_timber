"""Renders the examples in `examples/fabrication` to the images of the BTLx processings page of the docs.

An example is a plain script ending in `viewer.show()`. It is run as it is, with `Viewer.show` replaced by
rendering one frame to an image, so an image is what the example shows. `Viewer` is a singleton, which means one process per example.

Needs `compas_viewer`, `compas_brep[occ]` and a display: a window opens for each example. Qt's offscreen platform has no OpenGL.

    python scripts/screenshot_processing_examples.py [example ...]

"""

import pathlib
import runpy
import subprocess
import sys

import numpy as np
from compas_viewer import Viewer
from PySide6.QtCore import QRect
from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLES = ROOT / "examples" / "fabrication"
IMAGES = ROOT / "docs" / "_images" / "processings"

TARGET = [400.0, 0.0, 0.0]
POSITION = [1050.0, -1000.0, 1000.0]
VIEWS = {"connector": [600.0, -350.0, 1300.0]}  # the examples which need another position of the camera, by name

IMAGE_WIDTH = 900
MARGIN = 24
RENDER_DELAY = 1500  # ms, for the first frames to be drawn


def crop_and_save(image, path):
    """Crop the white space around the element, as the shape of the elements differs from the one of the window."""
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    pixels = np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, : image.width(), :3]
    rows, columns = np.where(pixels.min(axis=2) < 250)
    if not len(rows):
        raise SystemExit("Nothing was rendered for {}".format(path.stem))
    left, top = max(columns.min() - MARGIN, 0), max(rows.min() - MARGIN, 0)
    width, height = min(columns.max() + MARGIN, image.width()) - left, min(rows.max() + MARGIN, image.height()) - top
    image.copy(QRect(int(left), int(top), int(width), int(height))).scaledToWidth(IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation).save(str(path))


def render(example):
    path = IMAGES / "{}.png".format(example.stem)
    show = Viewer.show

    def show_one_frame(viewer):
        viewer.renderer.rendermode = "lighted"
        viewer.renderer.camera.far = 100000.0
        viewer.renderer.camera.target = TARGET
        viewer.renderer.camera.position = VIEWS.get(example.stem, POSITION)

        def grab():
            crop_and_save(viewer.renderer.grabFramebuffer(), path)
            viewer.app.quit()

        QTimer.singleShot(RENDER_DELAY, grab)
        show(viewer)

    Viewer.show = show_one_frame
    errors = runpy.run_path(str(example))["beam"].debug_info
    if errors:  # a processing which failed leaves the beam as it is, which would look like a valid image
        path.unlink()
        raise SystemExit("{}: {}".format(example.stem, errors))


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
