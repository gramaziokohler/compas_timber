# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] 2026-02-18

### Added

### Changed

* Fixed models with `XLapJoint` fail to serialize.
* Print warning when CategoryRules are inspecting elements which have no `category` attributes set.

### Removed


## [1.0.4] 2025-12-18

### Added

### Changed

* Cherry picked the fix for the `PlanarSurface.point_at` bug from `main`.

### Removed


## [1.0.3] 2025-11-05

### Added

* Added BTLx Machining Limits component

### Changed

* Changed 'BTLxFromGeometry' to allow Brep as input.
* Fixed Shape options for Mortise and Tenon input.
* Fixed BTLx from Parameters component. 
* Exclude FreeContour from list of options for BTLxFromParams GH Component

### Removed


## [1.0.2] 2025-10-28

### Added

### Changed

* Fixed performance issue in GH Model component caused by naiive implementation of `MaxNCompositeAnalyzer`.

### Removed


## [1.0.1] 2025-10-16

### Added
* Added `TimberElement.add_feature` to override the `Element` method.
* Added new GH helper `get_createable_joints` to get all createable Joint classes.

### Changed

* Fixed a bug in `TLapJoint` and `XLapJoint` where the `cut_plane_bias` parameter was not passed to the `_create_negative_volumes()` method after its signature was changed.
* Replaced `JackRafterCut` and `Lap` with their Proxy counterparts in `LLapJoint` and `TLapJoint`.
* Fixed a bug in `TStepJoint` where beam dimensions were calculated incorrectly for certain reference side orientations. 
* Renamed `TOliGinaJoint` to `OliginaJoint` for consistency wrt to the supported topology.
* Replaced `get_leaf_subclasses(Joint)` with `get_createable_joints()` in the relevant GH components.
* Added inflation of the negative volume in `LapProxy` to fix boolean difference artifact.

### Removed


## [1.0.0] 2025-09-01

### Added

* Added attribute `tolerance` to `TimberModel`.
* Added `scaled` method to `compas_timber.fabrication.BTLxProcessing` to scale the BTLx parameters.
* Added `scaled` method to `compas_timber.fabrication.BTLxPart` to scale the BTLx parameters.
* Added `scale` method to `compas_timber.fabrication.JackRafterCut`.
* Added `scale` method to `compas_timber.fabrication.Drilling`.
* Added `scale` method to `compas_timber.fabrication.DoubleCut`.
* Added `scale` method to `compas_timber.fabrication.Lap`.
* Added `scale` method to `compas_timber.fabrication.FrenchRidgeLap`.
* Added `scale` method to `compas_timber.fabrication.Tenon`.
* Added `scale` method to `compas_timber.fabrication.Mortise`.
* Added `scale` method to `compas_timber.fabrication.StepJoint`.
* Added `scale` method to `compas_timber.fabrication.StepJointNotch`.
* Added `scale` method to `compas_timber.fabrication.DovetailTenon`.
* Added `scale` method to `compas_timber.fabrication.DovetailMortise`.
* Added `scale` method to `compas_timber.fabrication.Slot`.
* Added `scale` method to `compas_timber.fabrication.Pocket`.
* Added `scale` method to `compas_timber.fabrication.Text`.
* Added `is_joinery` flag to `BTLxProcessing` to indicate if the processing is a result of joinery operation.
* Added new `compas_timber.fabrication.LongitudinalCut`.
* Added tasks `update-gh-header` to update the version in the header of the GH components.
* Added new `compas_timber.connections.XNotchJoint`.
* Added a proxy class for `Pocket` BTLx processing for performance optimization. 
* Added `topology` to class `Joint`.
* Added `location` to class `Joint`.
* Added `NBeamKDTreeAnalyzer` to `compas_timber.connections`.
* Added `TripletAnalyzer` to `compas_timber.connections`.
* Added `QuadAnalyzer` to `compas_timber.connections`.
* Added `CompositeAnalyzer` to `compas_timber.connections`.
* Added method `connect_adjacent_beams` to `TimberModel`.
* Added `PlateJoint`.
* Added `PlateButtJoint`.
* Added `PlateMiterJoint`.
* Added `PlateConnectionSolver`.
* Added generic `ButtJoint` class from which `TButtJoint` and `LButtJoint` inherit.
* Added new `BTLxProcessingError` to `compas_timber.errors`.
* Added `errors` property to `BTLxWriter` class which can be used after call to `write()` to check for errors.
* Added `CategoryPlateJointRule`, `DirectPlateJointRule`, `EdgeEdgeTopologyPlateJointRule`, and `EdgeFaceTopologyPlateJointRule` Plate joint rule GH components.
* Added `joints_contribution_guide` in docs.
* Added `PlateJointCandidate` to `generic_joint.py`.
* Added `Joint.promote_cluster` and `Joint.promote_joint_candidate` constructors to `Joint`.
* Added `PlateJoint.promote_joint_candidate` as override.
* Added `joints_contribution_guide` in docs.
* Added `JointRuleSolver` class.
* Added `JointTopology.TOPO_Y` for Beam Connections.
* Added `JointTopology.TOPO_K` for Beam Connections.
* Added `JointTopology.TOPO_EDGE_EDGE` for Plate Connections.
* Added `JointTopology.TOPO_EDGE_FACE` for Plate Connections.
* Added `Cluster.topology`.
* Added `PlateSolverResult` and `BeamSolverResult` to package results from `PlateConnectionSolver.find_topology()` and `ConnectionSolver.find_topology()`.

* Added `joint_candidates` property to `TimberModel`.
* Added `add_joint_candidate` method to `TimberModel`.
* Added `remove_joint_candidate` method to `TimberModel`.

### Changed

* BTLx Write now considers the `TimberModel.tolerance` attribute and scales parts and processings it when units are set to meters.
* Added missing `__data__` to `compas_timber.fabrication.Drilling`.
* Added missing `__data__` to `compas_timber.fabrication.Slot`.
* Fixed `TypeError` when deepcopying beams with `debug_info` on them.
* Processings which are not the result of joinery are now serialized with `TimberElement`.
* Fixed visualization bug in `Plate` due to loft resulting in flipped volume.
* Fixed a few bugs in the `WallPopulator` workflow including GH component updates.
* Renamed `NullJoint` to `JointCandidate`.
* Fixed bug in show_ref_faces GH component.
* `BTLxProcessing.ref_side_index` defaults to `0` if not set, instead of the invalid `None`.
* Updated `BTLx_contribution_guide` in docs.
* Fixed several GH Components for Rhino8 compatibility.
* Fixed `graph_node` is `None` after deserializing a `TimberModel`.
* Fixed a bug in `BeamsFromMesh` GH Component.
* Fixed attribute error when creating a `TButtJoint`.
* Changed default value for `modify_cross` to `True` for `LButtJoint`.
* Minor fixes to GH Components.
* Fixed `elements` and geometry creation for `BallNodeJoint`.
* Changed `PlateConnectionSolver.find_topology()` to solve for `TOPO_EDGE_EDGE` or `TOPO_EDGE_FACE`.
* Changed `PlateConnectionSolver.find_topology()` to return a `PlateSolverResult` instance.
* Reworked `ConnectionSolver.find_topology()` for readability and to implement `TOPO_I`.
* Changed `ConnectionSolver.find_topology()` to return a `BeamSolverResult` instance.
* Removed `topology`, `a_segment_index` and `b_segment_index` from `PlateJoint` subclass `__init__()` methods. These can now be passed as kwargs.
* `Platejoint`s can now be isntantiated with just 2 Plates as arguments. If no topology or segment index data is in kwargs, the joint will solve for those. 
* Fixed ironpython compatibility issues.
* `NBeamKDTreeAnalyzer` now uses `model.joint_candidates` instead of filtering `model.joints`.
* Fixed element interaction gets removed even if there are still attributes on it.
* Changed `elements` argument in `promote_joint_candidate` to `reordered_elements` for clarity.
* Fixed `TStepJoint` deserialization error where `__init__()` was accessing beam properties before beams were restored from GUIDs.
* Removed the `cut_plane_bias` parameter from the `LapJoint.__init__()` method, as it is not required by all subclasses.
* Added the `cut_plane_bias` parameter to the constructors of `TLapJoint`, `LLapJoint`, and `XLapJoint`.
* Updated the `__data__` methods of `TLapJoint`, `LLapJoint`, and `XLapJoint` to serialize the `cut_plane_bias` value.
* Updated the `__data__` method of `LFrenchRidgeLapJoint` to serialize the `drillhole_diam` value.
* Changed the `_create_negative_volumes()` method in `LapJoint` to accept `cut_plane_bias` as an argument.
* Renamed `set_default_values()` to `_update_default_values()` and moved method call from `__init__()` to `add_features()` in `TenonMortiseJoint` to avoid inconsistencies during deserialization.
* Set minimum `compas_timber` version in CPython GH components to `1.0.0`.
* Reworked `ConnectionSolver.find_topology()` for readability and to implement `TOPO_I`.
* Changed `JointRule.joints_from_beams_and_rules()` to `JointRule.apply_rules_to_model` which now adds `Joint`s to the
  `TimberModel` directly.
* Changed `WallPopulator.create_joint_definitions()` to `WallPopulator.create_joints()`, which now returns `DirectRule` instances.
* Changed `tolerance` argument to `max_distance` in `NBeamKDTreeAnalyzer` for clarity and consisten naming. 
* Changed `Joint.check_elements_compatibility()` to a class method to check Joint-type specific requirements before instantiation. 

### Removed

* Removed Grasshopper after-install plugin. Components should be installed via Rhino's Plugin Manager.
* Removed `get_face_most_towards_beam` from `Joint` as not used anywhere.
* Removed `get_face_most_ortho_to_beam` from `Joint` as not used anywhere.
* Removed `angle_vectors_projected` from `compas_timber.utils` since this has been upstreamed to core.
* Removed `comply()` from JointRule and its child classes.
* Removed `JointDefinition`. 
* Removed `FeatureDefinition`. 
* Removed redundant checks in `TopologyRule` GH components.

## [0.16.2] 2025-05-07

### Added

### Changed

* Fixed max recursion depth error when copying `TimberModel`/`Beam` with proxy processings.

### Removed



## [0.16.1] 2025-04-30

### Added

### Changed

### Removed


## [0.16.0] 2025-04-30

### Added

* Added new `compas_timber.fabrication.Pocket`.
* Added `front_side`, `back_side`, `opp_side` methods to the `Beam` class for retrieving specific sides relative to a reference side.
* Added processing `Text` to `compas_timber.fabrication`.
* Added `TextParams` to `compas_timber.fabrication`.
* Added new Grasshopper components for Rhino8/cpython. 
* Added new methods to handle adaptive GH_component parameters using cpython.

### Changed

* Fixed `AttributeError` when deserializing a model with Lap joints.
* Fixed a bug in `compas_timber.fabrication.Lap` where `ref_side_index` failed for `0` by checking for `None` instead.
* Fixed a bug in `compas_timber.fabrication.Lap` to handle the case when the vectors used to calculate the `inclination` angle are perpendicular.

### Removed


## [0.15.3] 2025-03-25

### Added

* Added `DualContour` BTLx Contour type for ruled surface Swarf contours.

### Changed

* Removed `main_ref_side_index` property from `TBirdsmouthJoint` since it's now defined in the `DoubleCut` BTLxProcessing.
* Added `mill_depth` argument in `TBirdsmouthJoint` for creating pockets on the cross_beam if asked.
* Refactored the `check_element_compatibility` method in `YButtJoint` so that it checks for coplanarity and dimensioning of the cross elements.
* Enhanced `DoubleCut.from_planes_and_beam` to verify that provided planes are not parallel and raise a `ValueError` if they are.
* Adjusted `process_joinery` method to catch `ValueError` exceptions during `BTLxProcessing` generation and wrap them in `BeamJoiningError` objects.
* Refactored and renamed `are_beams_coplanar` function to `are_beams_aligned_with_cross_vector`.
* Refactored `_create_negative_volumes()` in `LapJoint` so that it generates box-like volumes. 
* Refactored `XLapJoint`, `LLapJoint`, `TLapJoint` so that they use the `_create_negative_volumes()` method to get the negative volumes and use the alt constructor `Lap.from_volume_and_beam()`.
* Fixed an error occuring in `BTLxPart.shape_strings` by ensuring the polyline is always closed.
* Implemented `Inclination` in the `FreeContour` BTLx Processing.
* Changed `Plate` element to be defined by top and bottom contours instead of one contour and thickness. 

### Removed

* Removed `check_elements_compatibility` method from the parent `LapJoint` since non co-planar lap joints can be achieved.
* Removed the `is_pocket` argument in `Lap.from_plane_and_beam()` since this class method will now only serve for pockets in Butt joints.
* Removed `opposing_side_index` and `OPPOSING_SIDE_MAP` from `Beam` class since they have now been replaced by `front_side`, `back_side`, `opp_side` methods.
* Removed the deprecated `main_beam_opposing_side_index` property from `LButtJoint` and `TButtJoint` as it is no longer in use.

## [0.15.2] 2025-03-05

### Added

### Changed

* Fixed `ValueError` occurring when connecting just a slab to the GH model component.

### Removed


## [0.15.1] 2025-03-04

### Added

### Changed

* Fixed "No intersection found between walls" error when walls connect in unsupported topology.
* Implemented slab perimeter offset workaround.

### Removed


## [0.15.0] 2025-03-04

### Added

* Added `BTLx_From_Params` GH component which contains the definiton for class `DeferredBTLxProcessing` to allow directly defining BTLx parameters and passing them to the model.
* Added `Shape` to BTLx output, showing finished element geometry in BTLx Viewer instead of just blank.
* Added `as_plane()` to `WallToWallInterface`.
* Added optional argument `max_distance` to `WallPopulator.create_joint_definitions()`.

### Changed

* Added `max_distance` to `TimberModel.connect_adjacent_walls()`.
* Fixed plate doesn't get properly extended to the end of an L detail.
* Fixed detail edge beams don't get LButt.
* Fixed walls might not be considered connecting depending on the surface's orientation.

### Removed


## [0.14.2] 2025-02-17

### Added

### Changed

* Adjusted `LMiterJoint` so that it now applies an extra cut to elements when the `cutoff` flag is enabled.

### Removed


## [0.14.1] 2025-02-17

### Added

* Added missing arguments in configuration set component.
* Added `FlipDirection` flag to flip stud direction of a slab.

### Changed

* Fixed rotating stud direction in slab causes breaks plates and connections.
* Restructured some Gh Toolboxes & added Icons for Walls & Slabs

### Removed


## [0.14.0] 2025-02-17

### Added

* Added `distance_segment_segment` to `compas_timber.utils`
* Added `BTLxFromGeometryDefinition` class to replace the depricated `FeatureDefinition`. This allows deferred calculation of BTLx processings.
* Added `from_shapes_and_element` class method to `Drilling`, `JackRafterCut`, and `DoubleCut` as a wrapper for their geometry based constructors for use with `BTLxFromGeometryDefinition`.
* Added `YButtJoint` which joins the ends of three joints where the `cross_beams` get a miter cut and the `main_beam` gets a double cut.
* Added `JackRafterCutProxy` to allow for deferred calculation of the `JackRafterCut` geometry thus improving visualization performance.
* Added class "WallPopulator" to `compas_timber.design`.
* Added class "WallPopulatorConfigurationSet" to `compas_timber.design`.
* Added class "WallSelector" to `compas_timber.design`.
* Added class "AnyWallSelector" to `compas_timber.design`.
* Added class "LConnectionDetailA" to `compas_timber.design`.
* Added class "LConnectionDetailB" to `compas_timber.design`.
* Added class "TConnectionDetailA" to `compas_timber.design`.
* Added `from_brep` to `compas_timber.elements.Wall.
* Added `from_polyline` to `compas_timber.elements.Wall.
* Added `WallJoint` to `compas_timber.connections`.
* Added error handling when BTLx processing from geometry fails in GH.
* Added new `Slab` class to `compas_timber.elements`.
* Added `Slab` GH component.
* Added `FreeContour` BTLx processing and applied it to the `Plate` type so that plates can be machined.

### Changed

* Updated Grasshopper Toolbox and Icons
* Fixed `ValueErrorException` in `as_dict()` method of `BTLxProcessingParams` class by ensuring precision specifiers are used with floats.
* Removed model argument from `BTLxWriter` in the GH component and updated it to always return the BTLx string.
* Fixed a bug in `compas_timber.Fabrication.StepJointNotch` related to the `orientation` and `strut_inclination` parameters.
* Fixed the error message when beam endpoints coincide, e.g. when a closed polyline is used as input. 
* Changed `index` input of `ShowFeatureErrors` and `ShowJoiningErrors` do have default value of 0.
* Fixed spelling of `BeamJoinningError` to `BeamJoiningError`.
* Changed `process_joinery()` method to handle `BeamJoiningError` exceptions and return them. Also updated `Model` GH component.
* Updated `add_joint_error()` method in `DebugInformation` class to handle lists.
* Changed `compas_timber.fabrication.Lap` so that the volume is generated fully from the relevant BTLx params.
* Refactored `compas_timber.connections.LapJoint` to comply with the new system.
* Changed `THalfLapJoint`, `LHalfLapJoint`, `XHalfLapJoint` from `compas_timber.connections` so that they use the `Lap` BTLx processing.
* Renamed all `X/T/LHalfLapJoint` classes to `X/T/LLapJoint`.
* Enhanced lap behavior for optimal beam orientation in `LapJoint` class.
* Fixed `restore_beams_from_keys` in `LMiterJoint` to use the correct variable names.
* Reworked `DoubleCut` to more reliably produce the feature and geometry with the `from_planes_and_element` class method.
* Renamed `intersection_box_line()` to `intersection_beam_line_param()`, which now take a beam input and outputs the intersecting ref_face_index.
* Added `max_distance` argument to `JointRule` subclasses and GH components so that max_distance can be set for each joint rule individually.
* Changed referenced to `beam` in `Drilling` to `element`. 
* Changed `Drill Hole` and `Trim Feature` GH components to generate the relevant `BTLxProcessing` type rather than the deprecated `FeatureDefinition` type.
* Changed `Show_beam_faces` gh component to `Show_ref_sides`, which now takes an `int` index and shows the corresponding face including origin corner.
* Bug fixes after adding `max_distance` to joint defs.
* Using new `JackRafterCutProxy` in LMiterJoint, LButtJoint and TButtJoint.
* Changed input type from `Element` to `Beam` in components that currently only support beams.
* Fixed drilling GH component not taking diameter as a string.
* Reworked `Wall` class to be defined with a standard polyline, frame and thickness.
* Changed labels in `Show_ref_sides` GH component to be 1-based to match the spec.

### Removed


## [0.13.0] 2025-01-13

### Added

* Added API documentation for `design` and `error` packages.
* Added `guess_joint_topology_2beams` and `set_default_joints` functions to `design.__init__.py`.
* Added `list_input_valid`, `item_input_valid`, `get_leaf_subclasses`, `rename_gh_input` functions to `ghpython.__init__.py`.
* Added `Instruction`, `Model3d`, `Text3d`, `LinearDimension`, `BuildingPlanParser` classes to `planning.__init__.py`.
* Added `subprocessings` property to `BTLxProcessing` to allow nesting of processings.

### Changed

* Fixed comma incompatible with py27 in `Slot` module.
* Updated the API documentation for `connections`, `elements`, `fabrication`, `ghpython`, `planning` packages.
* Refactored all btlx `process` references to `processing`, including base classes, properties, variables, and docstrings.
* Refactored `BTLx` to `BTLxWriter` in the `compas_timber.Fabrication` package.

### Removed

* Removed `BeamJoiningError` from `connections.__init__.py`.
* Removed duplicate entries from the `__all__` list in the `elements.__init__.py` module.
* Removed package `compas_timber._fabrication`.
* Removed `btlx_processes` anf `joint_factories` from `compas_timber.fabrication` package.
* Removed `.btlx` files from `.gitignore`.


## [0.12.0] 2025-01-07

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
* Added new method `add_group_element` to `TimberModel`.
* Added new method `has_group` to `TimberModel`.
* Added new method `get_elements_in_group` to `TimberModel`.
* Added attribute `is_group_element` to `TimberElement`.
* Added `JointRule.joints_from_beams_and_rules()` static method 
* Added `Element.reset()` method.
* Added new `fasteners.py` module with new `Fastener` element type.
* Added new `compas_timber._fabrication.Lap`.
* Added `Joint_Rule_From_List` GH Component that takes lists of beams to create joints.
* Added `MIN_ELEMENT_COUNT` and `MAX_ELEMENT_COUNT` class attributes to `Joint`.
* Added `element_count_complies` class method to `Joint`.
* Added `compas_timber.fasteners.FastenerTimberInterface`.
* Added `compas_timber.connections.BallNodeJoint`.
* Added `compas_timber.elements.BallNodeFastener`.
* Added `transform()` method to `Feature` types.
* Added `FastenerInterfaceComponent` GH component.
* Added `ShowElementsByType` GH Component.
* Added `fasteners` property to `TimberModel`.
* Added `BTLx_Feature` GH component.
* Added `CT_Beams_From_Mesh` GH component.
* Added new `compas_timber._fabrication.FrenchRidgeLap`.
* Added new `compas_timber.connections.LFrenchRidgeLapJoint`.
* Added new `compas_timber._fabrication.Tenon` and `compas_timber._fabrication.Mortise`.
* Added new `compas_timber.connections.TTenonMortiseJoint`.
* Added `create` override to `BallNodeJoint`.
* Added `PlateFastener` class.
* Added `errors` directory and `__init__.py` module.
* Added new `compas_timber._fabrication.Slot`.
* Added new `compas_timber._fabrication.SlotParams`.

 

### Changed

* Changed incorrect import of `compas.geometry.intersection_line_plane()` to `compas_timber.utils.intersection_line_plane()`
* Renamed `intersection_line_plane` to `intersection_line_plane_param`.
* Renamed `intersection_line_line_3D` to `intersection_line_line_param`.
* Adjusted functions in `compas_timber._fabrication.DovetailMortise` and `compas_timber.connections.TDovetailJoint`.
* Added `conda-forge` channel to installation instructions.
* Fixed `**kwargs` inheritance in `__init__` for joint modules: `LMiterJoint`, `TStepJoint`, `TDovetailJoint`, `TBirdsmouthJoint`.
* Fixed GUID assignment logic from `**kwargs` to ensure correct fallback behavior for joint modules: `LMiterJoint`, `TStepJoint`, `TDovetailJoint`, `TBirdsmouthJoint`.
* Changed `model.element_by_guid()` instead of direct `elementsdict[]` access for beam retrieval in joint modules: `LMiterJoint`, `TStepJoint`, `TDovetailJoint`, `TBirdsmouthJoint`.
* Reworked the model generation pipeline.
* Reworked `comply` methods for `JointRule`s. 
* Fixed error with angle and inclination calculation in `compas_timber._fabrication.JackRafterCut` 
* Changed `compas_timber.connections.TButtJoint` and `compas_timber.connections.LButtJoint` by using the new implemented BTLx Processes to define the Joints
* Changed `DirectJointRule` to allow for more than 2 elements per joint.
* Changed `beam` objects get added to `Joint.elements` in `Joint.create()`.
* Fixed bug in vizualization of tenon/mortise in `compas_timber._fabrication.StepJoint`and `compas_timber._fabrication.StepJointNotch`.
* Changed `model.process_joinery()`so that it calls `joint.check_elements_compatibility()` before adding extensions and features.
* Fixed incorrect data keys for `beam_guid` in the `__data__` property for joint modules: `LMiterJoint`, `TStepJoint`, `TDovetailJoint`, `TBirdsmouthJoint`, `LFrenchRidgeLapJoint`.
* Fixed `JointRuleFromList` GH component.
* Changed `TButtJoint` to take an optional `PlateFastener`.
* Moved `FeatureApplicationError`, `BeamJoiningError`, and `FastenerApplicationError` to `errors.__init__.py`.
* Fixed a bug that occured when parallel beams are joined in the BallNodeJoint.
* Fixed `L_TopoJointRule`, `T_TopoJointRule` and `X_TopoJointRule` for cases where `Joint.SUPPORTED_TOPOLOGY` is a single value or a list.
* Fixed bug in `JointRule.joints_from_beams_and_rules()` that caused failures when topology was not recognized.
* Implemented `max_distance` parameter in `JointRule.joints_from_beams_and_rules()` and `JointRule.comply` methods.
* Bux fixes from extra comma argument and `max_distance` not implemented in `DirectRule.comply`.

### Removed

* Removed module `compas_timber.utils.compas_extra`.
* Removed a bunch of spaghetti from `CT_model` GH component.
* Removed module `compas_timber.fabrication.joint_factories.t_butt_factory`.
* Removed module `compas_timber.fabrication.joint_factories.l_butt_factory`.
* Removed module `compas_timber.connections.butt_joint`.
* Removed module `compas_timber.connections.french_ridge_lap`.
* Removed module `compas_timber.fabrication.joint_factories.french_ridge_factory`.
* Removed module `compas_timber.fabrication.btlx_processes.btlx_french_ridge_lap`.

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
