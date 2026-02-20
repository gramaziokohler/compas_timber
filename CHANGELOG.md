# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

### Removed


## [2.0.0-dev0] 2026-02-19

### Added
* Added `get_element()` method to `compas_timber.model.TimberModel` for optional element access by GUID.
* Added `__getitem__` support to `TimberModel` to allow strict element access via `model[guid]`. 
* Added `add_elements()` method to `compas_timber.model.TimberModel`, following its removal from the base `Model`.
* Added `geometry` property in `compas_timber.elements.TimberElement` following its removal from the base `Element` that returns the result of `compute_modelgeometry()`.
* Added `compute_elementgeometry` method in `TimberElement` that returns the element geometry in local coordinates.
* Added `reset_computed_properties()` method to `TimberElement` to provide interface for invalidating `@reset_computed` decorated properties.
* Added `transform()` method override to `TimberModel` to properly invalidate element caches when model transformation is applied, fixing inconsistent element transformation behavior.
* Added `__from_data__` class method override in `TimberElement` to handle frame/transformation conversion during deserialization.
* Added standalone element support through minimal overrides in `compute_modeltransformation()` and `compute_modelgeometry()` methods in `TimberElement`.
* Added new `compas_timber.planning.Stock` base class for representing raw material stock pieces with polymorphic element handling.
* Added new `compas_timber.planning.BeamStock` class for 1D beam stock pieces with length-based nesting and dimensional compatibility checking.
* Added new `compas_timber.planning.PlateStock` class for 2D plate stock pieces with area-based nesting and dimensional compatibility checking.
* Added new `compas_timber.planning.BeamNester` class for automated beam nesting with first-fit and best-fit decreasing algorithms.
* Added new `compas_timber.planning.NestingResult` class as a serializable wrapper for nesting results with analysis properties and enhanced dimensional reporting.
* Added new `compas_timber.fabrication.BTLxGenericPart` as a new base class for BTLx part representations, upstreaming shared functionality from `BTLxPart` and `BTLxRawpart`.
* Added new `compas_timber.fabrication.BTLxRawpart`, inheriting from `BTLxGenericPart`, to support raw part handling and nesting operations within the BTLx framework.
* Added `reset_timber_attrs` decorator to invalidate cached `TimberElement` attributes.
* Added `PlateJoint.add_extensions()` which does the initial extension of plate outline edges. 
* Added `PlateGeometry` class.
* Fixed `TimberElement.transform` doesn't reflect in drawn geometry due to caching.
* Added new `DrillingProxy` and `DoubleCutProxy` classes.
* Added `planar_surface_point_at` to `compas_timber.utils`.
* Added new `compas_timber.connections.KMiterJoint` class for creating K-Topo joint with a cross beam and two main beams. 
* Added new `compas_timber.connections.KButtJoint` class for creating K-Topo joint with a cross beam and two main beams. 

* Added `Panel` class as a renaming of `Slab`.
* Added `**kwargs` argument to `LongitudinalCut` and `LongitudinalCutProxy` constructors to allow passing additional parameters, particularly `is_joinery=False` to keep the processing during serialization.
* Added `PanelJoint` abstract base class for panel joints.
* Added `PanelLButtJoint` class.
* Added `PanelTButtJoint` class.
* Added `PanelMiterJoint` class.
* Added `TimberModel.connect_adjacent_panels()` method to find and create joint candidates between panels.
* Added `PanelFeatureType` class for classifying panel feature types.
* Added `panel_features` directory and `PanelFeature` abstract base class.
* Added `Panel.remove_features()` method to remove `PanelFeature` objects from a panel.
* Added `Panel.interfaces` property to filter features for `PanelConnectionInterface` instances.
* Added `NestedElementData` class to `compas_timber.planning` for explicit typing of nested element information.
* Added new `summary` property in `compas_timber.planning.NestingResult` that returns a human-readable string summarizing the nesting operation.
* Added `move_polyline_segment_to_line` to compas_timber.utils.
* Added `join_polyline_segments` to compas_timber.utils.
* Added `polyline_from_brep_loop` to compas_timber.utils.
* Added `polylines_from_brep_face` to compas_timber.utils.
* Added `get_polyline_normal_vector` to compas_timber.utils.
* Added `combine_parallel_segments` to compas_timber.utils.
* Added alternative constructor `MachiningLimits.from_dict()`. 
* Added `compas_timber.structural.BeamStructuralElementSolver` class to generate structural analysis segments from beams and joints.
* Added `add_beam_structural_segments`, `get_beam_structural_segments`, and `remove_beam_structural_segments` to `TimberModel` to manage structural analysis segments for beams.
* Added `add_structural_connector_segments`, `get_structural_connector_segments`, and `remove_structural_connector_segments` to `TimberModel` to manage structural analysis segments for joints.
* Added `create_beam_structural_segments` to `TimberModel` to generate structural segments for all beams and joints.

### Changed
* Deprecated `element_by_guid()` in `TimberModel`; use `get_element()` for optional access or `model[guid]` for strict access.
* Updated `compas_model` version pinning from `0.4.4` to `0.9.1` to align with the latest development.
* Changed `compas_timber.connections.Joint` to inherit from `Data` instead of the deprecated `Interaction`.
* Replaced `face.frame_at()` with `surface.frame_at()` on NURBS surfaces in `Lap.from_volume_and_element` to avoid `NotImplementedError` in `OCC`.
* Changed `TimberModel.element_by_guid()` to use `self._elements[guid]` instead of `self._guid_element[guid]` for element lookup.
* Replaced all `GroupNode` references with the new `Group` element class from `compas_model`.
* Changed `joints` and `joint_candidates` properties in `TimberModel` to use direct edge-based lookup instead of interactions.
* Updated default edge attributes in the model graph to include `joints` and `candidates`.
* Updated `graph_node` property to `graphnode` following the changes in the parent `compas_model.elements.Element` class.
* Upstreamed `ref_frame` property from `compas_timber.elements.Beam` to `compas_timber.elements.TimberElement`.
* Upstreamed `ref_sides` property from `compas_timber.elements.Beam` and `compas_timber.elements.Plate` to `compas_timber.elements.TimberElement`.
* Upstreamed `ref_edges` property from `compas_timber.elements.Beam` and `compas_timber.elements.Plate` to `compas_timber.elements.TimberElement`.
* Upstreamed `front_side`, `back_side`, `opp_side` methods from `compas_timber.elements.Beam` to `compas_timber.elements.TimberElement`.
* Upstreamed `side_as_surface` method from `compas_timber.elements.Beam` to `compas_timber.elements.TimberElement`.
* Upstreamed `get_dimensions_relative_to_side` method from `compas_timber.elements.Beam` to `compas_timber.elements.TimberElement`.
* Refactored `TimberElement.__init__()` to accept `frame` parameter and convert to `transformation` for parent `Element` class, bridging frame-based user interface with transformation-based inheritance.
* Changed the way the `ref_frame` is computed from the `Blank`'s geometry in `TimberElement`.
* Changed the way the `blank` is computed in `compas_timber.elements.Beam` applying the `modeltransformation` to a locally generated geometry.
* Changed the `apply()` method in `DoubleCut`, `DovetailMortise`, `DovetailTenon`, `Drilling`, `FrenchRidgeLap`, `JackRafterCut`, `Lap`, `LongitudinalCut`, `Mortise`, `Pocket`, `StepJointNotch`, `StepJoint`, `Tenon` by transforming the computed feature geometry in the element's local space to allow the element geometry computation to happen in local coordinates.
* Fixed bug in `LongitudinalCut` that occured when the cutting plane intersected a ref_side but the normals pointed away from each other, resulting in the cut parameter being out of range. 
* Changed `JointRuleSolver.apply_rules_to_model()` to consider `JointCandidate`s pairwise if larger clusters fail to create joints. 
* Improved performance of `TimberModel.process_joinery()` by caching some attributes of `TimberElement`. 
* Changed `Fastener`, `Slab`, `Wall` to inherit from `compas_model.Element` instead of `TimberElement`. `TimberElement` now represents BTLx parts exclusively.
* Changed core definition of `Plate` to be same as `Beam`, (frame, length, width, height) with `outline_a` and `outline_b` optional arguments.
* Changed `Plate` to inherit from `TimberElement` and `PlateGeometry`.
* Fixed the `ShowTopologyTypes` GH Component.
* Changed `Slot.apply()` to visualize the slot geometry. 
* Changed `BTLxProcessing` `*Proxy` classes to define geometry locally to the element to enable transform operations on elements with features defined with Proxies.
* Refactored `ButtJoint.__init__()` to accept `force_pocket: bool` and `conical_tool: bool` parameters.
* Fixed minor bug in `Pocket.apply()` that caused to the tilt angle to be assigned wrong. 
* Changed default values for `Pocket.__init__()` to match BTLx standard values. 
* Replaced calls to `PlanarSurface.point_at()` with calls to the new `planar_surface_point_at` to fix processing visualization issue since `compas==2.15.0`. 
* Changed `Slab` to inherit from `PlateGeometry` and `compas_model.Element`.
* Changed `Slab.from_boundary` to `Slab.from_outline_thickness`, inherited from `PlateGeometry`.
* Renamed `Slab` to `Panel` everywhere in code and docs. 
* Changed `LongitudinalCut` to properly generate `tool_position` parameter.
* Changed `JackRafterCut` to compute `orientation` based on the beam centerline and plane normal instead of ref_frame.point and plane normal for when the plane does not fully cross the beam.
* Changed `JackRafterCut` to allow negative `start_x` values in case the cutting plane does not fully cross the beam.
* Changed `Panel.__data__` to enable proper serialization.
* Changed some `PlateJoint` properties and methods to private.
* Changed `FreeContour` to compute geometry in local element coordinates.
* Changed how `FreeContour` computes the `ref_side_index` when not provided.
* Changed `FreeContour` constructors to work with new local geometry computation.
* Fixed models with `XLapJoint` fail to serialize.
* Fixed circular import cause by typing import in `slot.py`.
* Fixed a bug in `FreeContour.from_top_bottom_and_element` where `DualContour` is expecting a `Polyline` instead of a list of `Points`.
* Refactored `BTLxGenericPart` to accept an optional name, now used for the `Annotation` and `ElementNumber` attributes in the `BTLxPart` and `BTLxRawpart` outputs.
* Changed `element_data` dictionary in `compas_timber.planning.Stock` to now map each element GUID to a `NestedElementData` object containing its frame, a human-readable key, and length.
* Changed the constructor of `compas_timber.planning.NestingResult` to optionally accept a `Tolerance` object, allowing each result to specify its own units and precision for reporting and summaries.
* Changed `main_beam` to `beam_a` and `cross_beam` to `beam_b` in `LapJoint`, `LLapJoint`, `FrenchRidgeLapJoint`, and `XLapJoint`.
* Changed features creation in `ButtJoint` to staticmethods.
* Changed `Panel` and `Plate` to no longer inherit from 'PlateGeometry`.
* Implemented `compute_modeltransformation()` and `compute_modelgeometry()` in `Panel` and `Plate` to handle local geometry computation.
* Implemented alternate constructors `from_brep`,`from_outlines` and `from_outline_thickness` in `Panel` and `Plate`.
* Changed `MachiningLimits` to accept machining limits parameters in the constructors.
* Changed `Lap`, `Pocket` and `Slot` to accepte a `MachiningLimits` instance instead of a dictionary. 
* Moved `attributes` dictionary to `TimberElement` which carries arbitrary attributes set in it or given as `kwargs` accross serialization.
* Added `attributes` dictionary contet to serialization of `Panel`.
* Updated the `class_diagrams.rst` to reflect the changes in the class structure and inheritance.
* Removed all GH components as was migrated to the `timber_design` project.
* Removed pacakge `compas_timber.design` as it was migrated to the `timber_design` project.
* Removed package `compas_timber.ghpython` as it was migrated to the `timber_design` project.
* Moved `timber.py` module out of the `elements` package and renamed to `base.py`. This is to avoid circular dependencies between the `element` and `fabrication` packages.

### Removed
* Removed the `add_element()` method from `compas_timber.model.TimberModel`, as the inherited method from `Model` now covers this functionality.
* Removed `interactions` property from `TimberModel` in favor of direct edge-based joint lookup.
* Removed `blank_frame` property from `compas_timber.elements.Beam` since the ref_frame could serve it's purpose.
* Removed `faces` property from `compas_timber.elements.Beam` since it wasn't used anywhere.
* Removed `has_features` property from `compas_timber.elements.Beam` since it wasn't used anywhere.
* Removed `key` property from `compas_timber.elements.Beam` and `compas_timber.elements.Plate` since it is not used anymore.
* Removed all Rhino7 components!
* Removed method `add_group_element` from `TimberModel`.
* Removed `PlateToPlateInterface` since plates should be given `BTLxProcessing` features.
* Removed `Wall`, `WallJoint`, `WallToWallInterface`, `InterfaceRole`, `InterfaceLocation`, `Opening`, `OpeningType`,
  `TimberModel.connect_adjacent_walls`, `TimberModel._clear_wall_joints` and related
  GH components and component functionality.
* Removed `Slab` class and renamed to `Panel`.
* Removed unused `main_outlines` and `cross_outlines` properties from `PlateButtJoint`.
* Removed unused module `compas_timber.solvers`.

## [1.0.1] 2025-10-16

### Added
* Added `TimberElement.add_feature` to override the `Element` method.
* Added new GH helper `get_createable_joints` to get all createable Joint classes.

### Changed

* Fixed a bug in `TLapJoint` and `XLapJoint` where the `cut_plane_bias` parameter was not passed to the `_create_negative_volumes()` method after its signature was changed.
* Replaced `JackRafterCut` and `Lap` with their Proxy counterparts in `LLapJoint` and `TLapJoint`.
* Changed `BTLxPart` transformation GUID to use the `TimberElement`'s GUID instead of generating a random UUID in `compas_timber.fabrication.BTLxPart`.
* Updated the `write()` and `model_to_xml()` methods of the `BTLxWriter` class to optionally accept a `NestingResult` object, enabling inclusion of beam nesting information in the BTLx output.
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
