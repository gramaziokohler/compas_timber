---
config:
  layout: dagre
  class:
    hideEmptyMembersBox: true
  theme: redux
---
classDiagram
direction TB
    class Element {
    }
    class Fastener {
	    +shape : Geometry
	    +frame : Frame
	    +interfaces : list[FastenerTimberInterface]
	    +is_fastener : bool = True
	    +compute_geometry()
    }
    class Opening {
	    +polyline : Polyline
	    +opening_type : str
	    +orient_polyline(normal)
    }
    class ContainerElement {
	    +elements : list[TimberElement or ContainerElement]
	    +ref_sides : tuple[Frame]
	    +ref_edges : tuple[Line]
	    +transformation : Frame
	    +debug_info : list
	    +add_element()
	    +remove_element()
	    +reset()
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
	    +features : [BTLxProcessing]
	    +is_beam : bool = True
	    +from_centerline()
	    +from_endpoints()
	    +compute_geometry()
	    +compute_aabb()
	    +compute_obb()
	    +compute_collision_mesh()
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
    class PlateLike {
	    +outline_a : Polyline
	    +outline_b : Polyline
	    +frame : Frame
	    +planes : tuple[Plane]
	    +length : float
	    +width : float
	    +height : float
	    +from_outline_thickness()
	    +from_brep()
	    +compute_geometry()
	    +compute_aabb()
	    +compute_obb()
	    +compute_collision_mesh()
    }
    class Plate {
	    +openings : list[Polyline]
	    +blank_length : float
	    +blank : Box
	    +ref_frame : Frame
	    +features : [BTLxProcessing]
	    +is_plate : bool = True
    }
    class Slab {
	    +openings : list[Opening]
	    +type : str =  ["wall",  "floor" or "roof"]
	    +is_slab : bool = True
	    +is_group_element : bool = True
    }
    class TimberElement {
	    +transformation : Frame
	    +features : list[Feature]
	    +debug_info : list
	    +is_beam : bool
	    +is_plate : bool
	    +is_wall : bool
	    +is_fastener : bool
	    +reset()
	    +add_features(features)
	    +remove_features(features)
	    +remove_blank_extension()
    }

	<<abstract>> ContainerElement
	<<abstract>> PlateLike
	<<abstract>> TimberElement

    Element <|-- ContainerElement
    Element <|-- TimberElement
    TimberElement <|-- Beam
    TimberElement <|-- Plate
    PlateLike <|-- Plate
    PlateLike <|-- Slab
    ContainerElement <|-- Slab
    Element <|-- Fastener
    Slab ..> Opening : contains
    Fastener ..> FastenerTimberInterface : contains
