# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

* Added new base class for timber elements `TimberElement`.
* Added property `is_beam` to `Beam` class.
* Added property `is_plate` to `Plate` class.
* Added property `is_wall` to `Wall` class.
* Added `side_as_surface` to `compas_timber.elements.Beam`.
* Added `opposing_side_index` to `compas_timber.elements.Beam`.
* Added `Plate` element.
* Added attribute `plates` to `TimberModel`.
* Added new temporary package `_fabrication`.
* Added new `compas_timber._fabrication.JackRafterCut`.
* Added new `compas_timber._fabrication.JackRafterCutParams`.
* Added new `compas_timber._fabrication.Drilling`.
* Added new `compas_timber._fabrication.DrillingParams`.
* Added new `compas_timber._fabrication.StepJoint`.
* Added new `compas_timber._fabrication.StepJointNotch`.
* Added new `compas_timber._fabrication.DovetailTenon`.
* Added new `compas_timber._fabrication.DovetailMortise`.
* Added new `compas_timber.connections.TStepJoint`.
* Added new `compas_timber.connections.TDovetailJoint`.
* Added new `utilities` module in `connections` package.
* Added new `compas_timber._fabrication.DoubleCut`.
* Added new `compas_timber.connections.TBirdsmouthJoint`.

### Changed

* Changed incorrect import of `compas.geometry.intersection_line_plane()` to `compas_timber.utils.intersection_line_plane()`
* Renamed `intersection_line_plane` to `intersection_line_plane_param`.
* Renamed `intersection_line_line_3D` to `intersection_line_line_param`.

### Removed

* Removed module `compas_timber.utils.compas_extra`.

## [0.11.0] 2024-09-17

### Added

* Added bake component for `Plate` elements.
* Added default paramteters for `Surface Model` in the GH Component

### Changed

* Fixed wrong image file paths in the Documentation.
* Changed `TimberModel.beams` to return generator of `Beam` elements.
* Changed `TimberModel.walls` to return generator of `Wall` elements.
* Changed `TimberModel.plates` to return generator of `Plate` elements.
* Changed `TimberModel.joints` to return generator of `Joint` elements.
* Fixed polyline analysis for generating `SurfaceModel`
* Fixed errors in debug info components.

### Removed


## [0.10.1] 2024-09-11

### Added

### Changed

* Implemented a workaround for https://github.com/gramaziokohler/compas_timber/issues/280.

### Removed


## [0.10.0] 2024-09-11

### Added

* Added `SurfaceModelJointOverride` GH Component.
* Added `Plate` element.
* Added attribute `plates` to `TimberModel`.
* Added `SurfaceModelJointOverride` GH Component
* Added `ShowSurfaceModelBeamType` GH Component
* Re-introduced attribute `key` in `Beam`.
* Added attribute `key` to `Plate`.
* Added generation of `plate` elements to the `SurfaceModel`

### Changed

* Updated documentation for Grasshopper components.
* Fixed missing input parameter in `SurfaceModelOptions` GH Component.
* Fixed error with tolerances for `SurfaceModel`s modeled in meters.
* Renamed `beam` to `element` in different locations to make it more generic.
* Fixed `AttributeError` in `SurfaceModel`.
* Updated example scripts.
* Calling `process_joinery` in `SurfaceModel`.
* Changed how `BeamDefinition` and `Plate` types are handled in `SurfaceModel`
* Changed the `get_interior_segment_indices` function to work when there are multiple openings.
* Renamed `ShowSurfaceModelBeamType` to `ShowBeamsByCategory`.
* Changed `SurfaceModel` component input handling to give warnings instead of errors.

### Removed

* Removed `add_beam` from `TimberModel`, use `add_element` instead.
* Removed `add_plate` from `TimberModel`, use `add_element` instead.
* Removed `add_wall` from `TimberModel`, use `add_element` instead.

## [0.9.1] 2024-07-05

### Added

* Added `ref_frame` attribute to `Beam`.
* Added `ref_sides` attribute to `Beam`.
* Added `ref_edges` attribute to `Beam`.

### Changed

* Fixed error in BakeWithBoxMap component.
* Added `add_extensions` to `Joint` interface.
* Added `process_joinery` to `TimberModel`.
* Features are not automatically added when creating a joint using `Joint.create()`.
* Features are not automatically added when de-serializing.

### Removed


## [0.9.0] 2024-06-14

### Added

* Added `birdsmouth` parameter to `butt_joint` which applies a `btlx_double_cut` process to the part. 
* Added `BTLxDoubleCut` BTLx Processing class.
* Added BTLx support for `TButtJoint` and `LButtJoint`
* Added `BTLxLap` process class.

### Changed

* Moved module `workflow` from package `ghpython` to new package `design`.
* Moved `compas_timber.ghpython.CategoryRule` to `compas_timber.design`.
* Moved `compas_timber.ghpython.DirectRule` to `compas_timber.design`.
* Moved `compas_timber.ghpython.JointRule` to `compas_timber.design`.
* Moved `compas_timber.ghpython.TopologyRule` to `compas_timber.design`.
* Moved `compas_timber.ghpython.JointDefinition` to `compas_timber.design`.
* Moved `compas_timber.ghpython.FeatureDefinition` to `compas_timber.design`.
* Moved `compas_timber.ghpython.DebugInfomation` to `compas_timber.design`.

### Removed


## [0.8.1] 2024-06-13

### Added

### Changed

* Fixed import errors in GH components.
* Updated GH example file.

### Removed


## [0.8.0] 2024-06-12

### Added

* Added attribute `geometry` to `Beam`.
* Added `center_of_mass` property to Assembly class.
* Added `volume` property to Assembly class.
* Added new element type `Wall`.

### Changed

* Reduced some boilerplate code in `Joint` subclasses.
* Added argument `beams` to `Joint.__init__()` which expects tuple containing beams from implementing class instance.
* Renamed `TimberAssembly` to `TimberModel`.
* Renamed `compas_timber.assembly` to `compas_timber.model`.
* Renamed `compas_timber.parts` to `compas_timber.elements`.
* Based `Beam` on new `compas_model.elements.Element`.
* Based `TimberModel` on new `compas_model.model.Model`.
* Based `Joint` on new `compas_model.interactions.Interaction`.
* Removed support for Python `3.8`.

### Removed

* Removed `joint_type` attributes from all `Joint` classes.
* Removed argument `cutoff` from `LMiterJoint` as it was not used anywhere.
* Removed argument `gap` from `TButtJoint` as it was not used anywhere.
* Removed argument `gap` from `FrenchRidgeLap` as it was not used anywhere.
* Removed class `JointOptions` as not used anymore.
* Removed module `compas_timber.consumers`.
* Removed unused method `TButtJoint.get_cutting_plane()`.

## [0.7.0] 2024-02-15

### Added

* Added `debug_geometries` attribute to `BeamJoiningError`.
* (Re)added `BooleanSubtraction` feature.
* Added flag `modify_cross` to `L-Butt` joint.
* Added flag `reject_i` to `L-Butt` joint.
* Added new `NullJoint`.
* Added `mill_depth` argument to butt joints, with geometric representation of milled recess in cross beam.
* Added `ButtJoint` class with methods common to `LButtJoint` and `TButtJoint`
* Added new `L_TopologyJointRule`, `T_TopologyJointRule`, `X_TopologyJointRule` GH components
* Added GH component param support functions in `compas_timber.ghpython.ghcomponent_helpers.py`
* Added `topos` attribute to `CategoryRule` to filter when joints get applied
* Added new `SurfaceAssembly` class
* Added GH component `SurfaceAssembly` which directly generates a `TimberAssembly` with standard wall framing from a planar surface. 
* Added GH component `SurfaceAssemblyOptions`
* Added GH component `CustomBeamDimensions` for `SurfaceAssembly`

### Changed

* `BeamFromCurve` GH component accepts now referenced Rhino curves, referenced Rhino object IDs and internalized lines.
* `BeamFromCurve` GH component accepts now referenced Rhino curves, referenced Rhino object IDs and internalized lines.
* Fixed `FeatureError` when L-Butt applies the cutting plane.
* Fixed T-Butt doesn't get extended to cross beam's plane.
* `SimpleSequenceGenerator` updated to work with `compas.datastructures.assembly` and generates building plan acording to type.
* Changed GH Categories for joint rules.
* Made `beam_side_incident` a `staticmethod` of `Joint` and reworked it.
* Extended `DecomposeBeam` component to optionally show beam frame and faces.
* Changed `CategoryJointRule` and `DirectJointRule` to a dynamic interface where joint type is selected with right click menu
* Changed `Assembly` GH component to apply category joints if the detected topology is in `CategoryRule.topos`
* Changed `TopologyJoints` GH component to `DefaultJoints` Component, which applies default joints based on topology. 

### Removed

* Removed component `ShowBeamFrame`.
* Changed GH Categories for joint rules
* `BrepGeometryConsumer` continues to apply features even after the first error.
* `DrillHole` component calculates length from input line.
* `DrillHole` has default diameter proportional to beam cross-section.
* Removed input `Length` from `DrillHole` component.
* Fixed broken `TrimmingFeature` component.
* Removed all `JointOption` components. these are accessed in context menu of joint rules.

## [0.6.1] 2024-02-02

### Added

### Changed

### Removed


## [0.6.0] 2024-02-02

### Added

### Changed

* Updated COMPAS dependency to `2.0.0`!

### Removed


## [0.5.1] 2024-01-31

### Added

* Added missing documentation for module `ghpython.workflow.py`.
* Added missing documentation for package `connections`.
* `compas_timber.__version__` now returns current version.

### Changed

### Removed


## [0.5.0] 2024-01-31

### Added

* Added class `DebugInformation` to `workflow.py`.
* Added new component `ShowFeatureErrors`.
* Added new component `ShowJoiningErrors`.
* Added `FeatureApplicator` classes which report errors during feature application.
* Added `L-HalfLapJoint`.
* Added `T-HalfLapJoint`.
* Added `ShowTopologyTypes` GH Component.

### Changed

* Feature application now fails more gracefully (un-processed geometry is returned).
* Attempting to join beams which are already joined raises `BeamJoiningError` instead of `AssemblyError`
* `Joint.add_features` which fails to calculate anything raises `BeamJoiningError`.
* Changed COMPAS dependency to `compas==2.0.0beta.4`.
* Assembly component shows blanks when `CeateGeometry` flag is set to `False`. 

### Removed

* Removed `JointDef` GH components.
* Removed `AutomaticJoint` GH Component. Joint rules are now input directly into `TimberAssembly`.

## [0.4.0] 2024-01-24

### Added

* Added `fabrication` package 
* Added `BTLx` as a wrapper for `TimberAssembly` to generate .btlx files for machining timber beams
* Added `BTLxPart` as wrapper for `Beam`
* Added `joint_factories` folder and factories for existing joints except `X-HalfLap`
* Added `btlx_processes` folder and processes `JackCut` and `FrenchRidgeHalfLap`
* Added `BTLx` Grasshopper component
* Added `FrenchRidgeHalfLap` joint
* Added `DrillHole` Feature.
* Added `DrillHoleFeature` Grasshopper component.
* added `JointOptions` GH Components for all current joint types. This allows joint parameter definition in GH
* added `DirectJointRules` GH Component 
* added `TopologyJointRules` GH Component 
* added `BTLx` as a wrapper for `TimberAssembly` to generate .btlx files for machining timber beams
* added `BTLxPart` as wrapper for `Beam`
* added `joint_factories` folder and factories for existing joints except `X-HalfLap`
* added `btlx_processes` folder and processes `JackCut` and `FrenchRidgeHalfLap`
* added `BTLx` Grasshopper component
* added `FrenchRidgeHalfLap` joint


### Changed

* Changed `Beam` definition to include `blank_frame` and `blank_length` attributes 
* Replaced `Artist` with the new `Scene`.
* Changed type hint for argument `Centerline` of GH component `BeamFromCurve` to `Guid`.
* Curve ID of beam curves are now always stored in `Beam.attributes["rhino_guid"]`.
* Fixed `FindBeamByGuid` component.
* Bumped required COMPAS version to `2.0.0beta.2`.
* Changed docs theme to the new `sphinx_compas2_theme`.
* Re-worked component `BakeBoxMap` to advanced mode.
* Removed call to `rs.Redraw()` in `BakeBoxMap` which was causing GH document to lock (cannot drag).

### Removed


## [0.3.2] 2023-11-17

### Added

* Added now released COMPAS `2.0.0a1` to requirements.

### Changed

* Explicitly added attribute `key` to (de)serialization of `Beam`.

### Removed


## [0.3.1] 2023-09-18

### Added

### Changed

### Removed


## [0.3.0] 2023-09-18

### Added

* Added new joint type: Half-lap joint.

### Changed

* Beam transformed geometry with features is available using property `geometry`.
* Adapted the `Data` interface of `Beam` and `Assembly` according to the changes in COMPAS core.
* Beam geometry is created on demand.
* Adapted the `Data` interface of `Joint` and its implementations according to the changes in COMPAS core.
* Explicitly choosing `Grasshopper` context for the `Artist` in `ShowAssembly` component.

### Removed

* Removed method `Beam.get_geometry`.

## [0.2.16] 2023-05-16

### Added

### Changed

### Removed


## [0.2.15] 2023-05-15

### Added

### Changed

### Removed


## [0.2.14] 2023-05-15

### Added

### Changed

### Removed


## [0.2.13] 2023-05-15

### Added

### Changed

### Removed


## [0.2.12] 2023-05-15

### Added

### Changed

### Removed


## [0.2.11] 2023-05-15

### Added

### Changed

### Removed


## [0.2.10] 2023-05-14

### Added

### Changed

### Removed


## [0.2.9] 2023-05-12

### Added

### Changed

### Removed


## [0.2.8] 2023-05-12

### Added

### Changed

### Removed


## [0.2.7] 2023-05-12

### Added

### Changed

### Removed


## [0.2.6] 2023-05-12

### Added

### Changed

### Removed


## [0.2.5] 2023-05-12

### Added

### Changed

### Removed


## [0.2.4] 2023-05-12

### Added

### Changed

### Removed


## [0.2.3] 2023-05-12

### Added

### Changed

### Removed


## [0.2.2] 2023-05-12

### Added

### Changed

### Removed


## [0.2.1] 2023-05-12

### Added

### Changed

### Removed


## [0.2.0] 2023-05-11

### Added

* Integrated RTree search for neighboring beams using Rhino and CPython plugins.

### Changed

### Removed
