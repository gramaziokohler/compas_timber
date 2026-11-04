# BTLx Processings

The processings of [BTLx 2.3](https://www.design2machine.com/btlx/BTLx_2_3_0.pdf) which were added with [`ParametricProcessing`](api/compas_timber.fabrication.md#compas_timber.fabrication.ParametricProcessing), each with a minimal example.

The examples are in [`examples/fabrication`](https://github.com/gramaziokohler/compas_timber/tree/main/examples/fabrication). They need `compas_viewer` and `compas_brep[occ]`.
The images are rendered from these examples with `python scripts/screenshot_processing_examples.py`.

!!! note
    Most examples use `ref_side_index=2`, the reference side which faces up in a beam on `Frame.worldXY()`, to be visible in the image.

## Cuts

### RidgeValleyCut

Two inclined planes which meet in a ridge along the element.

![RidgeValleyCut](_images/processings/ridge_valley_cut.png)

```python
--8<-- "examples/fabrication/ridge_valley_cut.py"
```

### SawCut

A straight cut of a saw blade, limited in length and depth.

![SawCut](_images/processings/saw_cut.png)

!!! note
    The width of the kerf is not part of BTLx, so it is an assumption here.

```python
--8<-- "examples/fabrication/saw_cut.py"
```

### TriangleCut

Removes the wedge between two planes through a point.

![TriangleCut](_images/processings/triangle_cut.png)

```python
--8<-- "examples/fabrication/triangle_cut.py"
```

### Chamfer

Bevels the edges along the element.

![Chamfer](_images/processings/chamfer.png)

!!! note
    A `round` exit is made of 16 straight segments.

```python
--8<-- "examples/fabrication/chamfer.py"
```

### Planing

Removes a layer from the sides of the element.

![Planing](_images/processings/planing.png)

```python
--8<-- "examples/fabrication/planing.py"
```

### Sphere

Mills a section of a sphere out of the element.

![Sphere](_images/processings/sphere.png)

!!! note
    The opening angles of the cones are machine settings which are not part of BTLx, so they are 90 degrees as in the specification. A `start_offset` of 0 splits the element, of which the largest piece remains.

```python
--8<-- "examples/fabrication/sphere.py"
```

## Notches and log house joints

### HipValleyRafterNotch

The notch of a rafter on a hip or a valley rafter.

![HipValleyRafterNotch](_images/processings/hip_valley_rafter_notch.png)

!!! note
    `RafterNailHole` has no geometry, as the specification gives no position or size for it.

```python
--8<-- "examples/fabrication/hip_valley_rafter_notch.py"
```

### LogHouseHalfLap

The end of a log, reduced in height from both sides.

![LogHouseHalfLap](_images/processings/log_house_half_lap.png)

```python
--8<-- "examples/fabrication/log_house_half_lap.py"
```

### LogHouseJoint

Laps on the four sides of a log, where it crosses another one.

![LogHouseJoint](_images/processings/log_house_joint.png)

!!! note
    `Drillhole` has no geometry, as the specification gives no position or size for it.

```python
--8<-- "examples/fabrication/log_house_joint.py"
```

### LogHouseFront

The visible end of a log, narrowed from its edges.

![LogHouseFront](_images/processings/log_house_front.png)

```python
--8<-- "examples/fabrication/log_house_front.py"
```

## Joinery

### House

A tenon which holds a second, nested tenon or dovetail tenon on its face.

![House](_images/processings/house.png)

```python
--8<-- "examples/fabrication/house.py"
```

### HouseMortise

A mortise which holds a second, nested mortise or dovetail mortise.

![HouseMortise](_images/processings/house_mortise.png)

!!! note
    As in `Mortise`, `Slope` and `Inclination` are ignored.

```python
--8<-- "examples/fabrication/house_mortise.py"
```

### JapaneseTenon

The tenon of a Japanese scarf joint.

![JapaneseTenon](_images/processings/japanese_tenon.png)

!!! note
    Arcs are made of straight segments.

```python
--8<-- "examples/fabrication/japanese_tenon.py"
```

### JapaneseMortise

The mortise of a Japanese scarf joint, the counterpart of JapaneseTenon.

![JapaneseMortise](_images/processings/japanese_mortise.png)

!!! note
    Arcs are made of straight segments.

```python
--8<-- "examples/fabrication/japanese_mortise.py"
```

### ScarfJoint

A lengthwise joint with a sloped lap and optional drill holes.

![ScarfJoint](_images/processings/scarf_joint.png)

```python
--8<-- "examples/fabrication/scarf_joint.py"
```

### Dovetail

The corner lock of a log, with a sloped tail.

![Dovetail](_images/processings/dovetail.png)

```python
--8<-- "examples/fabrication/dovetail.py"
```

### TyroleanDovetail

The Tyrolean corner lock of a log, here with a Frosch.

![TyroleanDovetail](_images/processings/tyrolean_dovetail.png)

!!! note
    A `Frosch` is made of straight segments and the faces of a `Klingschrot` stay planar.

```python
--8<-- "examples/fabrication/tyrolean_dovetail.py"
```

## Profiles

### ProfileFront

A profile of two arcs at the end of the element.

![ProfileFront](_images/processings/profile_front.png)

!!! note
    The specification has no figure for `concave`, its shape here is a best guess.

```python
--8<-- "examples/fabrication/profile_front.py"
```

### ProfileCambered

A curved profile along the element.

![ProfileCambered](_images/processings/profile_cambered.png)

!!! note
    A `round` premill is a straight wall, as the radius of the tool is not a parameter.

```python
--8<-- "examples/fabrication/profile_cambered.py"
```

### RoundArch

An arc milled along the element.

![RoundArch](_images/processings/round_arch.png)

!!! note
    A `round` premill is a straight wall, as the radius of the tool is not a parameter.

```python
--8<-- "examples/fabrication/round_arch.py"
```

### ProfileHead

Stairs and arcs at the head of the element.

![ProfileHead](_images/processings/profile_head.png)

```python
--8<-- "examples/fabrication/profile_head.py"
```

## Contours and surfaces

### SawContour

A contour which is cut with a saw blade.

![SawContour](_images/processings/saw_contour.png)

!!! note
    Straight segments only, an open contour does not cut, and `Recess` and `MachiningLimits` are not supported.

```python
--8<-- "examples/fabrication/saw_contour.py"
```

### MillContour

A contour which is milled, here as a pocket.

![MillContour](_images/processings/mill_contour.png)

!!! note
    Straight segments only, an open contour does not cut, and `Recess` and `MachiningLimits` are not supported.

```python
--8<-- "examples/fabrication/mill_contour.py"
```

### PlaningArea

Planes an area, here around an aperture.

![PlaningArea](_images/processings/planing_area.png)

```python
--8<-- "examples/fabrication/planing_area.py"
```

### FreeSurface

Removes everything above a NURBS surface.

![FreeSurface](_images/processings/free_surface.png)

```python
--8<-- "examples/fabrication/free_surface.py"
```

## Processings without geometry

These are written to the BTLx file, but they do not change the volume of the element. The red lines are not part of the geometry of the element, the examples draw them to show where the processing is.

### Marking

A line on the element, which leaves its volume as it is.

![Marking](_images/processings/marking.png)

```python
--8<-- "examples/fabrication/marking.py"
```

### NailContour

Nails along a path, which leave the volume as it is.

![NailContour](_images/processings/nail_contour.png)

```python
--8<-- "examples/fabrication/nail_contour.py"
```

### CrampContour

Cramps along a path, which leave the volume as it is.

![CrampContour](_images/processings/cramp_contour.png)

```python
--8<-- "examples/fabrication/cramp_contour.py"
```

### ScrewContour

Screws along a path, which leave the volume as it is.

![ScrewContour](_images/processings/screw_contour.png)

```python
--8<-- "examples/fabrication/screw_contour.py"
```

### PenContour

A path drawn on the element, which leaves its volume as it is.

![PenContour](_images/processings/pen_contour.png)

```python
--8<-- "examples/fabrication/pen_contour.py"
```

### GlueArea

An area of glue, which leaves the volume as it is.

![GlueArea](_images/processings/glue_area.png)

```python
--8<-- "examples/fabrication/glue_area.py"
```

### PlasterArea

An area of plaster, which leaves the volume as it is.

![PlasterArea](_images/processings/plaster_area.png)

```python
--8<-- "examples/fabrication/plaster_area.py"
```

### InsulationArea

An area of insulation, which leaves the volume as it is.

![InsulationArea](_images/processings/insulation_area.png)

```python
--8<-- "examples/fabrication/insulation_area.py"
```

### LockoutArea

An area where processes are not allowed, which leaves the volume as it is.

![LockoutArea](_images/processings/lockout_area.png)

```python
--8<-- "examples/fabrication/lockout_area.py"
```

### Variant

A set of parameters whose meaning is up to the receiver of the file. It has no geometry, the example draws a line at its start point.

![Variant](_images/processings/variant.png)

```python
--8<-- "examples/fabrication/variant.py"
```

## Containers

### ProcessingGroup

Several processings which belong together.

![ProcessingGroup](_images/processings/processing_group.png)

```python
--8<-- "examples/fabrication/processing_group.py"
```

### Connector

A connector with the processings which make room for it, here a lap and a drilling.

![Connector](_images/processings/connector.png)

```python
--8<-- "examples/fabrication/connector.py"
```

### PatternContour

Repeats processings at the nodes of a contour, here a drilling.

![PatternContour](_images/processings/pattern_contour.png)

!!! note
    Straight segments only. A processing which depends on the dimensions of the element sees it at its original position.

```python
--8<-- "examples/fabrication/pattern_contour.py"
```
