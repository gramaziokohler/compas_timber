import os

from compas.colors import Color
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation

from compas_threejs.materials import Material
from compas_threejs.ui import Button, Slider
from compas_threejs.viewer import Viewer

from compas_timber.elements import Plate
from compas_timber.fabrication import BTLxWriter
from compas_timber.model import TimberModel
from compas_timber.planning import PlateNester, PlateStock


# --- Default parameters ---
default_stock_x = 120
default_stock_y = 60
default_thickness = 1.8
default_spacing = 1.0
default_fast = False
default_per_group = False
default_seed = 0
default_reps = 20

params = {
    "stock_x": default_stock_x,
    "stock_y": default_stock_y,
    "thickness": default_thickness,
    "spacing": default_spacing,
    "fast": default_fast,
    "per_group": default_per_group,
    "seed": default_seed,
    "reps": default_reps,
}

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(HERE), "..", "data")

def export_btlx(model, output_path=None, nesting_result=None):
    """Export the model to BTLx format."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "nesting_test.btlx")
    writer = BTLxWriter()
    writer.write(model, output_path, nesting_result=nesting_result)
    print(f"BTLx exported to {output_path}")


# Base shapes as outlines
base_shapes = [
    Polyline([Point(0, 0, 0), Point(20, 0, 0), Point(20, 10, 0), Point(0, 10, 0), Point(0, 0, 0)]),
    Polyline([Point(0, 0, 0), Point(12, 0, 0), Point(12, 8, 0), Point(0, 8, 0), Point(0, 0, 0)]),
    Polyline([Point(0, 0, 0), Point(15, 0, 0), Point(15, 4, 0), Point(4, 4, 0), Point(4, 12, 0), Point(0, 12, 0), Point(0, 0, 0)]),
]


# --- Geometry objects ---
stock_geometries = []
plate_geometries = []
previous_params = None
last_model = None
last_nesting_result = None


# --- Viewer setup ---
viz = Viewer()
viz.default_lighting = True

# Reuse materials instead of creating a new one per geometry
stock_material = Material(color=Color.grey())
plate_material = Material(color=Color.blue())


def clear_geometries(geometries):
    for geometry in geometries:
        viz.remove_object(geometry)
    geometries.clear()


def update_scene(force=False):
    global previous_params
    global last_model, last_nesting_result

    first_draw = previous_params is None
    if first_draw or force:
        stock_changed = True
        plate_changed = True
    else:
        stock_changed = (
            params["stock_x"] != previous_params["stock_x"]
            or params["stock_y"] != previous_params["stock_y"]
            or params["reps"] != previous_params["reps"]
            or params["per_group"] != previous_params["per_group"]
        )
        plate_changed = (
            params["thickness"] != previous_params["thickness"]
            or params["spacing"] != previous_params["spacing"]
            or params["seed"] != previous_params["seed"]
            or params["fast"] != previous_params["fast"]
        )

    if not (stock_changed or plate_changed):
        return

    if stock_changed:
        clear_geometries(stock_geometries)
    if stock_changed or plate_changed:
        clear_geometries(plate_geometries)

    model = TimberModel()
    for outline in base_shapes * params["reps"]:
        plate = Plate.from_outline_thickness(outline, params["thickness"])
        model.add_element(plate)

    stock = PlateStock((params["stock_x"], params["stock_y"]), params["thickness"])
    nester = PlateNester(
        model,
        stock,
        spacing=params["spacing"],
        per_group=params["per_group"],
        seed=params["seed"],
    )
    nesting_result = nester.nest(fast=params["fast"])
    last_model = model
    last_nesting_result = nesting_result

    print("Nesting Result Data:")
    print("--------------------")
    print("Stock Utilization:")
    for util in getattr(nesting_result, "stock_utilization", []):
        print(util)
    print("Unplaced Elements:", getattr(nesting_result, "unplaced_elements", []))
    print("Unplaced Reasons:", getattr(nesting_result, "unplaced_reasons", {}))

    plates_by_guid = {str(plate.guid): plate for plate in model.plates}
    stock_sep = params["stock_x"] + 10

    for i, stock_item in enumerate(nesting_result.stocks):
        offset_x = i * stock_sep
        sx = getattr(stock_item, "dimensions", [params["stock_x"], params["stock_y"]])[0]
        sy = getattr(stock_item, "dimensions", [params["stock_x"], params["stock_y"]])[1]

        stock_polyline = Polyline(
            [
                [offset_x + 0, 0, 0],
                [offset_x + sx, 0, 0],
                [offset_x + sx, sy, 0],
                [offset_x + 0, sy, 0],
                [offset_x + 0, 0, 0],
            ]
        )
        viz.add_geometry(stock_polyline, stock_material)
        stock_geometries.append(stock_polyline)

        for guid, frame in stock_item.placement_data.items():
            plate = plates_by_guid.get(guid)
            if plate is None:
                print(f"Warning: Plate with guid {guid} not found in model.plates.")
                continue

            transform = Transformation.from_frame(frame)
            outline = plate.plate_geometry.outline_a.transformed(transform)
            outline_flat = Polyline([Point(pt.x + offset_x, pt.y, 0) for pt in outline.points])
            viz.add_geometry(outline_flat, plate_material)
            plate_geometries.append(outline_flat)

    previous_params = params.copy()


# --- UI callbacks ---
def set_stock_x(val):
    params["stock_x"] = val
    update_scene()


def set_stock_y(val):
    params["stock_y"] = val
    update_scene()


def set_spacing(val):
    params["spacing"] = val
    update_scene()


def set_seed(val):
    params["seed"] = int(val)
    update_scene()


def set_reps(val):
    params["reps"] = int(val)
    update_scene()


def toggle_fast():
    params["fast"] = not params["fast"]
    update_scene()


def export_current_btlx():
    if last_model is None or last_nesting_result is None:
        print("Nothing to export yet. Update scene first.")
        return
    export_btlx(last_model, None, last_nesting_result)


# --- UI elements ---
viz.add_ui_element(Slider(min=20, max=200, step=1, default_value=default_stock_x, action=set_stock_x, label="Stock Width (X)"))
viz.add_ui_element(Slider(min=20, max=200, step=1, default_value=default_stock_y, action=set_stock_y, label="Stock Height (Y)"))
viz.add_ui_element(Slider(min=0, max=10, step=0.1, default_value=default_spacing, action=set_spacing, label="Spacing"))
viz.add_ui_element(Slider(min=0, max=20, step=1, default_value=default_seed, action=set_seed, label="Seed"))
viz.add_ui_element(Slider(min=1, max=100, step=1, default_value=default_reps, action=set_reps, label="Repetitions"))
viz.add_ui_element(Button(text="Fast", action=toggle_fast))
viz.add_ui_element(Button(text="Export BTLx", action=export_current_btlx))


# --- Viewer ---
update_scene(force=True)
viz.start()



