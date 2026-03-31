import os

from compas.colors import Color
from compas.geometry import Polyline, Point, Transformation

from compas_timber.model import TimberModel
from compas_timber.fabrication import BTLxWriter
from compas_timber.elements import Plate
from compas_timber.planning import PlateStock, PlateNester

from compas_threejs.viewer import Viewer
from compas_threejs.materials import Material


# Default parameters
stock_x = 120
stock_y = 60
thickness = 1.8
spacing = 1.0
fast = False
per_group = False
seed = 0

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(os.path.dirname(HERE), "..", "data")

def export_btlx(model, output_path=None, nesting_result=None):
    """Export the model to BTLx format."""
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "nesting_test.btlx")
    writer = BTLxWriter()
    writer.write(model, output_path, nesting_result=nesting_result)
    print(f"BTLx exported to {output_path}")

# Base_shapes as outlines
base_shapes = [
    Polyline([Point(0,0,0), Point(20,0,0), Point(20,10,0), Point(0,10,0), Point(0,0,0)]),
    Polyline([Point(0,0,0), Point(12,0,0), Point(12,8,0), Point(0,8,0), Point(0,0,0)]),
    Polyline([Point(0,0,0), Point(15,0,0), Point(15,4,0), Point(4,4,0), Point(4,12,0), Point(0,12,0), Point(0,0,0)])
]

# Build model from outlines
model = TimberModel()
for i, outline in enumerate(base_shapes * 20):  # Repeat the base shapes 20 times
    plate = Plate.from_outline_thickness(outline, thickness)
    model.add_element(plate)

# Nest
stock = PlateStock((stock_x, stock_y), thickness)
nester = PlateNester(model, stock, spacing=spacing, per_group=per_group, seed=seed)
nesting_result = nester.nest(fast=fast)

# Viewer setup
viz = Viewer()
viz.default_lighting = True
viz.background_color = Color(0.1, 0.1, 0.1)

# Print nesting result data
print("Nesting Result Data:")
print("--------------------")
print("Stock Utilization:")
for util in getattr(nesting_result, "stock_utilization", []):
    print(util)
print("Unplaced Elements:", getattr(nesting_result, "unplaced_elements", []))
print("Unplaced Reasons:", getattr(nesting_result, "unplaced_reasons", {}))

# Draw all stocks
stock_sep = stock_x + 10
for i, s in enumerate(nesting_result.stocks):
    offset_x = i * stock_sep

    # Draw stock rectangle for each stock
    sx = getattr(s, "dimensions", [stock_x, stock_y])[0]
    sy = getattr(s, "dimensions", [stock_x, stock_y])[1]
    stock_polyline = Polyline([
        [offset_x + 0, 0, 0],
        [offset_x + sx, 0, 0],
        [offset_x + sx, sy, 0],
        [offset_x + 0, sy, 0],
        [offset_x + 0, 0, 0]
    ])
    viz.add_geometry(stock_polyline, Material(color=Color.white()))

    # Draw placed plates for this stock
    for guid, frame in s.placement_data.items():
        plate = next(p for p in model.plates if str(p.guid) == guid)
        T = Transformation.from_frame(frame)
        outline = plate.plate_geometry.outline_a.transformed(T)
        outline_flat = Polyline([Point(p.x + offset_x, p.y, 0) for p in outline.points])
        viz.add_geometry(outline_flat, Material(color=Color.cyan()))

# Export BTLx
export_btlx(model, None, nesting_result)

# Visualize with ThreeJS
viz.start()



