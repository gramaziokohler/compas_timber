# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

* Reduced some boilerplate code in `Joint` subclasses.
* Added argument `beams` to `Joint.__init__()` which expects tuple containing beams from implementing class instance.

### Removed

* Removed `joint_type` attributes from all `Joint` classes.
* Removed argument `cutoff` from `LMiterJoint` as it was not used anywhere.
* Removed argument `gap` from `TButtJoint` as it was not used anywhere.
* Removed argument `gap` from `FrenchRidgeLap` as it was not used anywhere.

## [0.7.0] 2024-02-15

### Added

* Added `debug_geometries` attribute to `BeamJoiningError`.
* (Re)added `BooleanSubtraction` feature.
* Added flag `modify_cross` to `L-Butt` joint.
* Added flag `reject_i` to `L-Butt` joint.
* Added new `NullJoint`.
* Added `mill_depth` argument to butt joints, with geometric representation of milled recess in cross beam.
* Added `ButtJoint` class with methods common to `LButtJoint` and `TButtJoint`
* Added BTLx support for `TButtJoint` and `LButtJoint`
* Added `BTLxLap` process class

### Changed

* `BeamFromCurve` GH component accepts now referenced Rhino curves, referenced Rhino object IDs and internalized lines.
* `BeamFromCurve` GH component accepts now referenced Rhino curves, referenced Rhino object IDs and internalized lines.
* Fixed `FeatureError` when L-Butt applies the cutting plane.
* Fixed T-Butt doesn't get extended to cross beam's plane.
* `SimpleSequenceGenerator` updated to work with `compas.datastructures.assembly` and generates building plan acording to type.
* Changed GH Categories for joint rules.
* Made `beam_side_incident` a `staticmethod` of `Joint` and reworked it.
* Extended `DecomposeBeam` component to optionally show beam frame and faces.
* Changed `Beam.faces` to match position and orientation of BTLx `ReferenceSide`

### Removed

* Removed component `ShowBeamFrame`.
* Changed GH Categories for joint rules
* `BrepGeometryConsumer` continues to apply features even after the first error.
* `DrillHole` component calculates length from input line.
* `DrillHole` has default diameter proportional to beam cross-section.
* Removed input `Length` from `DrillHole` component.
* Fixed broken `TrimmingFeature` component.

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
