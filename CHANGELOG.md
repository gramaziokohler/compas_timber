# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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

### Changed
* Changed `Beam` definition to include `blank_frame` and `blank_length` attributes 
* Replaced `Artist` with the new `Scene`.
* Changed type hint for argument `Centerline` of GH component `BeamFromCurve` to `Guid`.
* Curve ID of beam curves are now always stored in `Beam.attributes["rhino_guid"]`.
* Fixed `FindBeamByGuid` component.
* Bumped required COMPAS version to `2.0.0beta.2`.
* Changed docs theme to the new `sphinx_compas2_theme`.

### Removed

* Removed superfluous component `BeamFromCurveGuid`.

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
