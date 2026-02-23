********************************************************************************
Class Diagrams
********************************************************************************

This section provides visual representations of the class hierarchies and relationships in different subsystems of COMPAS Timber. This is to help developers better understand the codebase and to document the interface of the different classes.

.. contents::
   :local:
   :depth: 2

Timber Element Subsystem
========================

The elements subsystem contains all the core timber elements that can be modeled and manipulated. These inherit from the base :class:`~compas_timber.elements.TimberElement` class.

.. mermaid::

   classDiagram

      class TimberElement {
         <<abstract>>
         +frame : Frame
         +length : float
         +width : float
         +height : float
         +features : list[BTLxProcessing]
         +attributes : dict
         +geometry : Geometry
         +debug_info : list
         +is_beam() : bool
         +is_plate() : bool
         +is_group_element() : bool
         +reset()
         +add_feature(feature)
         +add_features(features)
         +remove_features(features=None)
         +transformation_to_local()
         +ref_frame()
         +ref_sides()
         +ref_edges()
      }

      class Beam {
         +shape : Box
         +blank : Box
         +blank_length : float
         +centerline : Line
         +from_centerline(centerline, width, height)
         +from_endpoints(p1, p2, width, height)
         +compute_elementgeometry(include_features=True)
         +compute_aabb(inflate=0.0)
         +compute_obb(inflate=0.0)
         +compute_collision_mesh()
         +add_blank_extension(start, end, joint_key=None)
         +remove_blank_extension(joint_key=None)
      }

      class Plate {
         +plate_geometry : PlateGeometry
         +outline_a : Polyline
         +outline_b : Polyline
         +openings : list[Polyline]
         +planes : tuple[Plane]
         +blank : Box
         +blank_length : float
         +compute_elementgeometry(include_features=True)
         +compute_aabb(inflate=0.0)
         +compute_obb(inflate=0.0)
         +compute_collision_mesh()
         +from_outlines(outline_a, outline_b)
         +from_outline_thickness(outline, thickness)
         +from_brep(brep, thickness)
         +set_extension_plane(edge_index, plane)
         +apply_edge_extensions()
      }

      class Panel {
         +frame : Frame
         +length : float
         +width : float
         +thickness : float
         +plate_geometry : PlateGeometry
         +outline_a : Polyline
         +outline_b : Polyline
         +openings : list[Polyline]
         +planes : tuple[Plane]
         +normal : Vector
         +edge_planes : dict[int, Plane]
         +name : str
         +interfaces : list
         +attributes : dict
         +is_group_element : bool = True
         +compute_elementgeometry(include_features=True)
         +compute_aabb(inflate=0.0)
         +compute_obb(inflate=0.0)
         +compute_collision_mesh()
         +transformation_to_local()
         +from_outlines(outline_a, outline_b)
         +from_outline_thickness(outline, thickness)
         +from_brep(brep, thickness)
         +set_extension_plane(edge_index, plane)
         +apply_edge_extensions()
         +remove_blank_extension(edge_index=None)
         +reset()
         +remove_features(features=None)
      }


      class Fastener {
         +shape : Geometry
         +frame : Frame
         +interfaces : list[FastenerTimberInterface]
         +is_fastener : bool = True
         +compute_geometry()
      }


      class FastenerTimberInterface {
         +outline_points : list[Point]
         +thickness : float
         +holes : list[dict]
         +frame : Frame
         +element : TimberElement
         +shapes : list[Geometry]
         +features : list[Feature]
      }

      %% Inheritance relationships
      Element <|-- TimberElement
      TimberElement <|-- Beam
      TimberElement <|-- Plate
      Element <|-- Panel
      Element <|-- Fastener

      %% Composition relationships
      Fastener ..> FastenerTimberInterface : contains

Connections Subsystem
=====================

The connections subsystem defines joints and their relationships. All joints inherit from the base :class:`~compas_timber.connections.Joint` class and are categorized by topology.

.. mermaid::

   classDiagram
      class Interaction {
         <<abstract>>
         +name : str
      }

      class Joint {
         <<abstract>>
         +topology : JointTopology
         +location : Point
         +elements : list[Element]
         +generated_elements : list[Element]
         +features : list[Feature]
         +SUPPORTED_TOPOLOGY : JointTopology
         +MAX_ELEMENT_COUNT : int
         +features : list[BTLxProcessing]
         +create(model, *elements)
         +add_features()
         +add_extensions()
         +check_elements_compatibility()
         +restore_beams_from_keys(model)
         +create(model, elements)
      }

      class JointCandidate {
         +element_a : TimberElement
         +element_b : TimberElement
         +element_a_guid : str
         +element_b_guid : str
      }

      class ButtJoint {
         <<abstract>>
         +main_beam : Beam
         +cross_beam : Beam
         +main_beam_guid : str
         +cross_beam_guid : str
         +mill_depth : float
         +modify_cross : bool
         +butt_plane : Plane
      }

      class LButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_L
         +start_y : float
         +strut_inclination : float
         +small_beam_butts : bool
         +back_plane : Plane
         +reject_i : bool
      }

      class TButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_T
         +modify_cross = False
         +fasteners : list[Fastener]
         +base_fastener : Fastener
         +fasteners : list
         +base_fastener : object
      }

      class TBirdsmouthJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +main_beam_guid : str
         +cross_beam_guid : str
         +mill_depth : float
         +SUPPORTED_TOPOLOGY = TOPO_T
         +cross_ref_side_indices : tuple[int]
         +cross_ref_side_indices : list[int]
      }

      class LMiterJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +beam_a_guid : str
         +beam_b_guid : str
         +cutoff : bool
         +SUPPORTED_TOPOLOGY = TOPO_L
         +get_cutting_planes()
         +get_cutoff_plane()
      }

      class LapJoint {
         <<abstract>>
         +main_beam : Beam
         +cross_beam : Beam
         +lap_length : float
         +mill_depth : float
         +beam_a_guid : str
         +beam_b_guid : str
         +flip_lap_side : bool
         +ref_side_index_a : int
         +ref_side_index_b : int
         +cutting_plane_a : Plane
         +cutting_plane_b : Plane
      }

      class TLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_T
         +cut_plane_bias : float
      }

      class LLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_L
         +cut_plane_bias : float
      }

      class XLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_X
         +cut_plane_bias : float
      }

      class LFrenchRidgeLapJoint {
         +drillhole_diam : float
      }

      class BallNodeJoint {
         +beams : list[Beam]
         +_beam_guids : list[str]
         +ball_diameter : float
         +fastener : BallNodeFastener
         +SUPPORTED_TOPOLOGY = TOPO_Y
         +MAX_ELEMENT_COUNT = None
         +fastener_guid : str
         +generated_elements : list
      }

      class TDovetailJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +main_beam_guid : str
         +cross_beam_guid : str
         +start_y : float
         +start_depth : float
         +rotation : float
         +length : float
         +width : float
         +cone_angle : float
         +tool_diameter : float
         +tool_height : float
      }

      class TStepJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +main_beam_guid : str
         +cross_beam_guid : str
         +step_shape : int
         +step_depth : float
         +heel_depth : float
         +tapered_heel : bool
         +tenon_mortise_height : float
      }

      class TenonMortiseJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +tenon_length : float
         +tenon_width : float
         +tenon_height : float
         +SUPPORTED_TOPOLOGY = TOPO_T
         +main_beam_guid : str
         +cross_beam_guid : str
         +start_y : float
         +start_depth : float
         +rotation : float
         +length : float
         +width : float
         +height : float
         +shape : int
      }

      class YButtJoint {
         +main_beam : Beam
         +cross_beam_a : Beam
         +cross_beam_b : Beam
         +main_beam_guid : str
         +cross_beam_a_guid : str
         +cross_beam_b_guid : str
         +mill_depth : float
         +beams : list
      }

      class PlateJoint {
         <<abstract>>
         +plate_a : Plate
         +plate_b : Plate
      }

      class PlateButtJoint {
         <<abstract>>
         +main_plate : Plate
         +cross_plate : Plate
      }

      class PlateLButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_EDGE_EDGE
      }

      class PlateTButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_EDGE_FACE
      }

      class PlateMiterJoint {
         +SUPPORTED_TOPOLOGY = TOPO_EDGE_EDGE
      }

      class PanelJoint {
         <<abstract>>
         +panel_a : Panel
         +panel_b : Panel
      }

      class PanelLButtJoint {
         +main_panel : Panel
         +cross_panel : Panel
      }

      class PanelTButtJoint {
         +main_panel : Panel
         +cross_panel : Panel
      }

      class PanelMiterJoint {
         
      }

      %% Inheritance relationships
      Interaction <|-- Joint
      Joint <|-- JointCandidate
      Joint <|-- ButtJoint
      Joint <|-- TBirdsmouthJoint
      Joint <|-- LMiterJoint
      Joint <|-- LapJoint
      Joint <|-- BallNodeJoint
      Joint <|-- TenonMortiseJoint
      Joint <|-- TDovetailJoint
      Joint <|-- TStepJoint
      Joint <|-- YButtJoint
      Joint <|-- PlateJoint
      PlateJoint <|-- PanelJoint

      ButtJoint <|-- LButtJoint
      ButtJoint <|-- TButtJoint
      LapJoint <|-- TLapJoint
      LapJoint <|-- LLapJoint
      LapJoint <|-- XLapJoint
      LapJoint <|-- LFrenchRidgeLapJoint
      PlateJoint <|-- PlateButtJoint
      PlateButtJoint <|-- PlateLButtJoint
      PlateButtJoint <|-- PlateTButtJoint
      PlateJoint <|-- PlateMiterJoint
      PanelJoint <|-- PanelLButtJoint
      PanelJoint <|-- PanelTButtJoint
      PlateLButtJoint <|-- PanelLButtJoint
      PlateTButtJoint <|-- PanelTButtJoint
      PanelJoint <|-- PanelMiterJoint
      PlateMiterJoint <|-- PanelMiterJoint

Fabrication Subsystem
======================

The fabrication subsystem handles manufacturing features and BTLx processing. All fabrication features inherit from :class:`~compas_timber.fabrication.BTLxProcessing`.

.. mermaid::

   classDiagram
      class Data {
         <<abstract>>
         +__data__ : dict
         +__from_data__(data)
      }

      class BTLxProcessing {
         <<abstract>>
         +ref_side_index : int
         +is_joinery : bool
         +priority : int
         +process_id : str
         +subprocessings : list[BTLxProcessing]
         +PROCESSING_NAME : str
         +add_subprocessing(subprocessing)
         +apply(geometry, element)
         +scale(factor)
      }


      class BTLxFromGeometryDefinition {
         +processing : type[BTLxProcessing]
         +geometries : list[Geometry]
         +elements : list[TimberElement]
         +kwargs : dict
         +feature_from_element(element)
         +transform(transformation)
         +transformed(transformation)
      }

      class BTLxWriter {
         +model : TimberModel
         +errors : list[BTLxProcessingError]
         +write_btlx_file(filepath)
         +_create_part(element, order_num)
         +_create_processing(feature)
      }

      class BTLxPart {
         +element : TimberElement
         +order_num : int
         +length : float
         +width : float
         +height : float
         +frame : Frame
         +processings : list[BTLxProcessing]
         +part_guid : str
         +et_grain_direction : Element
         +et_reference_side : Element
         +et_transformations : Element
         +et_shape : Element
      }

      class Contour {
         +polyline : Polyline
         +depth : float
         +depth_bounded : bool
         +inclination : list[float]
         +to_brep()
      }

      class DualContour {
         +principal_contour : Polyline
         +associated_contour : Polyline
         +depth_bounded : bool
         +to_brep()
      }
      class DoubleCut {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +angle_1 : float
         +inclination_1 : float
         +angle_2 : float
         +inclination_2 : float
      }

      class Lap {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +angle : float
         +inclination : float
         +slope : float
         +length : float
         +width : float
         +depth : float
         +lead_angle_parallel : bool
         +lead_angle : float
         +lead_inclination_parallel : bool
         +lead_inclination : float
         +machining_limits : dict
      }

      class Slot {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +length : float
         +depth : float
         +thickness : float
         +angle_ref_point : float
         +angle_opp_point : float
         +add_angle_opp_point : float
         +machining_limits : dict
      }

      class Tenon {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +rotation : float
         +length_limited_top : bool
         +length_limited_bottom : bool
         +length : float
         +width : float
         +height : float
         +shape : TenonShapeType
         +shape_radius : float
         +chamfer : bool
      }

      class Mortise {
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +slope : float
         +inclination : float
         +length_limited_top : bool
         +length_limited_bottom : bool
         +length : float
         +width : float
         +depth : float
         +shape : TenonShapeType
         +shape_radius : float
      }

      class Drilling {
         +start_x : float
         +start_y : float
         +angle : float
         +inclination : float
         +depth_limited : bool
         +depth : float
         +diameter : float
      }

      class JackRafterCut {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
      }

      class Pocket {
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +slope : float
         +length : float
         +width : float
         +internal_angle : float
         +tilt_ref_side : float
         +tilt_end_side : float
         +tilt_opp_side : float
         +tilt_start_side : float
         +machining_limits : dict
      }

      class StepJoint {
         +orientation : OrientationType
         +start_x : float
         +strut_inclination : float
         +step_depth : float
         +heel_depth : float
         +step_shape : StepShapeType
         +tenon : bool
         +tenon_width : float
         +tenon_height : float
      }

      class StepJointNotch {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +strut_inclination : float
         +notch_limited : bool
         +notch_width : float
         +step_depth : float
         +heel_depth : float
         +strut_height : float
         +step_shape : StepShapeType
         +mortise : bool
         +mortise_width : float
         +mortise_height : float
      }

      class DovetailTenon {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +rotation : float
         +length_limited_top : bool
         +length_limited_bottom : bool
         +length : float
         +width : float
         +height : float
         +cone_angle : float
         +use_flank_angle : bool
         +flank_angle : float
         +shape : TenonShapeType
         +shape_radius : float
      }

      class DovetailMortise {
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +slope : float
         +inclination : float
         +limitation_top : LimitationTopType
         +length_limited_bottom : bool
         +length : float
         +width : float
         +depth : float
         +cone_angle : float
         +use_flank_angle : bool
         +flank_angle : float
         +shape : TenonShapeType
         +shape_radius : float
      }

      class FrenchRidgeLap {
         +orientation : OrientationType
         +start_x : float
         +angle : float
         +ref_position : EdgePositionType
         +drillhole : bool
         +drillhole_diam : float
      }

      class FreeContour {
         +contour_param_object : Contour | DualContour
         +counter_sink : bool
         +tool_position : AlignmentType
         +depth_bounded : bool
      }

      class Text {
         +start_x : float
         +start_y : float
         +angle : float
         +alignment_vertical : str
         +alignment_horizontal : str
         +alignment_multiline : str
         +stacked_marking : bool
         +text_height_auto : bool
         +text_height : float
         +text : str
      }

      class LongitudinalCut {
         +start_x : float
         +start_y : float
         +inclination : float
         +start_limited : bool
         +end_limited : bool
         +length : float
         +depth_limited : bool
         +depth : float
         +angle_start : float
         +angle_end : float
         +tool_position : AlignmentType
      }

      %% Inheritance relationships (Fabrication subsystem)
      Data <|-- BTLxProcessing
      Data <|-- BTLxFromGeometryDefinition
      Data <|-- Contour
      Data <|-- DualContour

      BTLxProcessing <|-- DoubleCut
      BTLxProcessing <|-- Lap
      BTLxProcessing <|-- Slot
      BTLxProcessing <|-- Tenon
      BTLxProcessing <|-- Mortise
      BTLxProcessing <|-- Drilling
      BTLxProcessing <|-- JackRafterCut
      BTLxProcessing <|-- Pocket
      BTLxProcessing <|-- StepJoint
      BTLxProcessing <|-- StepJointNotch
      BTLxProcessing <|-- DovetailTenon
      BTLxProcessing <|-- DovetailMortise
      BTLxProcessing <|-- FrenchRidgeLap
      BTLxProcessing <|-- FreeContour
      BTLxProcessing <|-- Text
      BTLxProcessing <|-- LongitudinalCut

      %% Composition relationships
      BTLxWriter ..> BTLxPart : creates
      BTLxPart ..> BTLxProcessing : contains
      FreeContour ..> Contour|DualContour : contains

Errors Subsystem
=================

The errors subsystem provides specialized exception classes for different types of failures that can occur during timber modeling, joint creation, fabrication, and processing operations.

.. mermaid::

   classDiagram
      class Exception {
         <<builtin>>
         +message : str
      }

      class FeatureApplicationError {
         +feature_geometry : Geometry
         +element_geometry : Geometry
         +message : str
      }

      class BeamJoiningError {
         +beams : list[Beam]
         +joint : Joint
         +debug_info : str
         +debug_geometries : list[Geometry]
      }

      class FastenerApplicationError {
         +elements : list[TimberElement]
         +fastener : Fastener
         +message : str
      }

      class BTLxProcessingError {
         +message : str
         +part : BTLxPart
         +failed_processing : BTLxProcessing
      }

      %% Inheritance relationships
      Exception <|-- FeatureApplicationError
      Exception <|-- BeamJoiningError
      Exception <|-- FastenerApplicationError
      Exception <|-- BTLxProcessingError
