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
         +features : list[Feature]
         +debug_info : list
         +is_beam : bool
         +is_plate : bool
         +is_group_element : bool
         +is_fastener : bool
         +reset()
         +add_features(features)
         +remove_features(features)
         +remove_blank_extension()
      }

      class Beam {
         +attributes : dict
         +width : float
         +height : float
         +length : float
         +frame : Frame
         +shape : Box
         +blank : Box
         +blank_length : float
         +blank_frame : Frame
         +ref_frame : Frame
         +faces : list[Frame]
         +ref_sides : tuple[Frame]
         +ref_edges : tuple[Line]
         +centerline : Line
         +centerline_start : Point
         +centerline_end : Point
         +long_edges : list[Line]
         +midpoint : Point
         +is_beam : bool = True
         +from_centerline()
         +from_endpoints()
         +compute_geometry()
         +compute_aabb()
         +compute_obb()
         +compute_collision_mesh()
      }

      class Plate {
         +outline_a : Polyline
         +outline_b : Polyline
         +openings : list[Polyline]
         +frame : Frame
         +thickness : float
         +planes : tuple[Plane]
         +blank_length : float
         +width : float
         +height : float
         +ref_frame : Frame
         +is_plate : bool = True
         +compute_geometry()
         +compute_aabb()
         +compute_obb()
      }

      class Slab {
         +outline : Polyline
         +thickness : float
         +openings : list[Polyline]
         +frame : Frame
         +origin : Point
         +baseline : Line
         +centerline : Line
         +width : float
         +length : float
         +height : float
         +corners : tuple[Point]
         +faces : tuple[Frame]
         +end_faces : tuple[Frame]
         +envelope_faces : tuple[Frame]
         +is_group_element : bool = True
         +from_boundary()
         +from_brep()
         +compute_geometry()
         +compute_aabb()
         +compute_obb()
         +rotate()
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
      Element <|-- Slab
      TimberElement <|-- Fastener

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
	    +topology : JointTopology
	    +location : Point
	    +elements : list[Element]
	    +generated_elements : list[Element]
	    +features : list[Feature]
	    +SUPPORTED_TOPOLOGY : JointTopology
	    +MAX_ELEMENT_COUNT : int
	    +add_features()
	    +add_extensions()
	    +check_elements_compatibility()
	    +restore_beams_from_keys(model)
        +get_beam_direction_towards_joint()
	    +create(model, elements)
    }

      class JointCandidate {
         +element_a : TimberElement
         +element_b : TimberElement
         +element_a_guid : str
         +element_b_guid : str
      }

      class ButtJoint {
	    +main_beam : Beam
	    +cross_beam : Beam
	    +mill_depth : float
	    +modify_cross : bool
	    +butt_plane : Plane
	    +SUPPORTED_TOPOLOGY = TOPO_L | TOPO_T
        +get_pocket_on_cross_beam()  Pocket$
        +get_lap_on_cross_beam()  Lap$
        +get_cut_on_main_beam() JackRafterCutProxy$
      }

      class LButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_L
         +start_y : float
         +strut_inclination : float
      }

      class TButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_T
         +modify_cross = False
         +fasteners : list[Fastener]
         +base_fastener : Fastener
      }

      class TBirdsmouthJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +mill_depth : float
         +SUPPORTED_TOPOLOGY = TOPO_T
         +cross_ref_side_indices : tuple[int]
      }

      class LMiterJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +SUPPORTED_TOPOLOGY = TOPO_L
      }

      class LapJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +lap_length : float
         +mill_depth : float
      }

      class TLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_T
      }

      class LLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_L
      }

      class XLapJoint {
         +SUPPORTED_TOPOLOGY = TOPO_X
      }

      class BallNodeJoint {
         +beams : list[Beam]
         +ball_diameter : float
         +fastener : BallNodeFastener
         +SUPPORTED_TOPOLOGY = TOPO_X
         +MAX_ELEMENT_COUNT = -1
      }

      class TenonMortiseJoint {
         +main_beam : Beam
         +cross_beam : Beam
         +tenon_length : float
         +tenon_width : float
         +tenon_height : float
         +SUPPORTED_TOPOLOGY = TOPO_T
      }

      class PlateJoint {
         <<abstract>>
         +plate_a : Plate
         +plate_b : Plate
         +interface : PlateToPlateInterface
      }

      class PlateButtJoint {
         +SUPPORTED_TOPOLOGY = TOPO_L | TOPO_T
      }

      class KMiterJoint {
          +beams : list[Beam]
          +elements : list[Beam]
          +are_beams_coplanar : bool
          +promote_cluster()$
          +cross_beam_ref_side_index()
          +main_beam_red_side_index()
          +add_extensions()
          +add_features()
      }

      class KButtJoint {
          +beams : list[Beam]
          +elements : list[Beam]
          +are_beams_coplanar : bool
          +promote_cluster()$
          +cross_beam_ref_side_index()
          +main_beam_red_side_index()
          +add_extensions()
          +add_features()
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
      Joint <|-- PlateJoint
      Joint <|-- KMiterJoint
      Joint <|-- KButtJoint

      ButtJoint <|-- LButtJoint
      ButtJoint <|-- TButtJoint
      LapJoint <|-- TLapJoint
      LapJoint <|-- LLapJoint
      LapJoint <|-- XLapJoint
      PlateJoint <|-- PlateButtJoint



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

      class DoubleCut {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +angle_1 : float
         +inclination_1 : float
         +angle_2 : float
         +inclination_2 : float
         +is_concave : bool
         +PROCESSING_NAME = "DoubleCut"
         +from_plane_and_beam()
      }

      class Lap {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +strut_inclination : float
         +length : float
         +depth : float
         +is_pocket : bool
         +PROCESSING_NAME = "Lap"
         +from_plane_and_beam()
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
         +machining_limits : MachiningLimits
         +PROCESSING_NAME = "Slot"
         +from_plane_and_beam()
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
         +chamfer : float
         +PROCESSING_NAME = "Tenon"
      }

      class Mortise {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +length : float
         +width : float
         +depth : float
         +PROCESSING_NAME = "Mortise"
      }

      class Drilling {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +angle : float
         +inclination : float
         +diameter : float
         +depth : float
         +PROCESSING_NAME = "Drilling"
      }

      class Pocket {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +start_depth : float
         +angle : float
         +inclination : float
         +length : float
         +width : float
         +depth : float
         +PROCESSING_NAME = "Pocket"
      }

      class StepJoint {
         +orientation : OrientationType
         +start_x : float
         +start_y : float
         +strut_inclination : float
         +step_depth : float
         +heel_depth : float
         +step_shape : StepShapeType
         +PROCESSING_NAME = "StepJoint"
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
         +PROCESSING_NAME = "Text"
      }

      class LongitudinalCut {
         +orientation : OrientationType
         +start_x : float
         +inclination : float
         +start_limited : bool
         +end_limited : bool
         +length : float
         +depth_limited : bool
         +depth : float
         +angle_start : float
         +angle_end : float
         +PROCESSING_NAME = "LongitudinalCut"
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

      %% Inheritance relationships
      Data <|-- BTLxProcessing
      Data <|-- BTLxFromGeometryDefinition
      BTLxProcessing <|-- DoubleCut
      BTLxProcessing <|-- Lap
      BTLxProcessing <|-- Slot
      BTLxProcessing <|-- Tenon
      BTLxProcessing <|-- Mortise
      BTLxProcessing <|-- Drilling
      BTLxProcessing <|-- Pocket
      BTLxProcessing <|-- StepJoint
      BTLxProcessing <|-- Text
      BTLxProcessing <|-- LongitudinalCut

      %% Composition relationships
      BTLxWriter ..> BTLxPart : creates
      BTLxPart ..> BTLxProcessing : contains

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
