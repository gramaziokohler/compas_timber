# Curated spec for gen_diagrams.py. Class bodies come from graph.json;
# this file only decides partitioning, prose, anchors, overrides, and edges.
# Edge tuples with 5 items are machine-checked: (owner, op, target, label, owner_attr).

HEADER = """# Class Diagrams

This section provides visual representations of the class hierarchies and relationships in different subsystems of COMPAS Timber. This is to help developers better understand the codebase and to document the interface of the different classes.

The diagrams are generated from the source code (attributes, methods and inheritance are extracted with Python's `ast`), so they reflect the code at the version noted in the changelog rather than an idealized design. Members inherited from `compas` / `compas_model` base classes are not repeated on subclasses.

[TOC]
"""

SECTIONS = [
    # ------------------------------------------------------------------ model
    dict(
        title="Model Overview",
        prose="""
`TimberModel` is the central class that ties the subsystems together. It extends compas_model's `Model`, which stores elements in a hierarchy (element tree) and their relationships in an interaction graph — elements are added with `add_element()`, inherited from `Model`. Joints are kept in a model-level registry and referenced from the edges of the interaction graph. Calling `process_joinery()` first applies the joints' blank extensions to the elements, then adds their features (`BTLxProcessing` instances), which `BTLxWriter` serializes to a BTLx file for fabrication.
""",
        diagrams=[
            dict(
                classes=["TimberModel"],
                anchors={
                    "Model": "compas_model",
                    "TimberElement": "abstract",
                    "Joint": "abstract",
                    "BTLxProcessing": "abstract",
                    "BTLxWriter": None,
                },
                overrides={
                    "TimberModel": dict(
                        include={
                            "beams", "plates", "panels", "fasteners", "joints", "joint_candidates",
                            "add_joint", "add_joint_candidate", "remove_joint",
                            "connect_adjacent_beams", "connect_adjacent_plates", "connect_adjacent_panels",
                            "process_joinery",
                        }
                    ),
                },
                edges_title="Composition and usage relationships",
                edges=[
                    ("TimberModel", "o--", "TimberElement", "elements"),
                    ("TimberModel", "o--", "Joint", "joints"),
                    ("Joint", "..>", "TimberElement", "joins"),
                    ("Joint", "..>", "BTLxProcessing", "generates"),
                    ("TimberElement", "o--", "BTLxProcessing", "features"),
                    ("BTLxWriter", "..>", "TimberModel", "serializes to BTLx"),
                ],
            ),
        ],
    ),
    # --------------------------------------------------------------- elements
    dict(
        title="Timber Element Subsystem",
        prose="""
The elements subsystem contains all the core timber elements that can be modeled and manipulated. `Beam` and `Plate` inherit from the base `TimberElement` class, while `Panel`, `Fastener` and `PanelFeature` inherit directly from compas_model's `Element`. `Plate` and `Panel` delegate their outline/plane logic to a shared, composed `PlateGeometry` object. `frame` and element-tree bookkeeping are inherited from compas_model's `Element` and are not repeated below. The legacy `Feature` classes (`CutFeature`, `DrillFeature`, `MillVolume`, `BrepSubtraction`) predate the BTLx-based features; they are no longer used internally but remain exported from `compas_timber.elements` for backward compatibility.
""",
        diagrams=[
            dict(
                classes=[
                    "TimberElement", "Beam", "Plate", "PlateGeometry",
                    "Fastener", "BallNodeFastener", "PlateFastener", "FastenerTimberInterface",
                    "Feature", "CutFeature", "DrillFeature", "MillVolume", "BrepSubtraction",
                    "Panel", "PanelType", "PanelFeature", "PanelFeatureType",
                    "Opening", "OpeningType", "PanelConnectionInterface", "InterfaceRole",
                ],
                anchors={"Element": "compas_model", "Data": "abstract"},
                overrides={
                    "Feature": dict(add_stereotypes=["abstract"]),
                    "PanelType": dict(add_stereotypes=["enumeration"]),
                    "PanelFeatureType": dict(add_stereotypes=["enumeration"]),
                    "OpeningType": dict(add_stereotypes=["enumeration"]),
                    "InterfaceRole": dict(add_stereotypes=["enumeration"]),
                },
                edges=[
                    ("Plate", "*--", "PlateGeometry", "delegates to", "plate_geometry"),
                    ("Panel", "*--", "PlateGeometry", "delegates to", "plate_geometry"),
                    ("Fastener", "o--", "FastenerTimberInterface", "contains", "interfaces"),
                    ("Panel", "o--", "PanelFeature", "contains", "features"),
                    ("Panel", "..>", "PanelType", "uses"),
                    ("PanelFeature", "..>", "PanelFeatureType", "uses", "panel_feature_type"),
                    ("Opening", "..>", "OpeningType", "uses", "opening_type"),
                    ("PanelConnectionInterface", "..>", "InterfaceRole", "uses", "interface_role"),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------ connections
    dict(
        title="Connections Subsystem",
        prose="""
The connections subsystem defines joints and the machinery that discovers them. All joints inherit from the base `Joint` class (a `compas.data.Data` subclass) and declare the topology they support via `SUPPORTED_TOPOLOGY`. Joints are registered in the `TimberModel` and referenced from the edges of its interaction graph. Because of its size, the subsystem is shown in three diagrams: topology solving, beam joints, and plate/panel joints.
""",
        diagrams=[
            dict(
                intro="""
### Topology Solving and Joint Candidates

`ConnectionSolver` (for beams) and `PlateConnectionSolver` (for plates) detect intersecting element pairs and classify their topology as one of the `JointTopology` values, returning `BeamSolverResult` / `PlateSolverResult`. `TimberModel.connect_adjacent_*()` uses these solvers to register `JointCandidate` / `PlateJointCandidate` placeholders, which can later be promoted to concrete joints with `Joint.promote_joint_candidate()`. A `Cluster` groups joints that share a location and can be promoted with `Joint.promote_cluster()`.
""",
                classes=[
                    "JointTopology", "ConnectionSolver", "PlateConnectionSolver",
                    "BeamSolverResult", "PlateSolverResult", "Cluster",
                    "JointCandidate", "PlateJointCandidate",
                ],
                anchors={"Data": "abstract", "Joint": "abstract", "PlateJoint": "abstract", "TimberModel": None},
                overrides={
                    "JointTopology": dict(add_stereotypes=["enumeration"]),
                },
                edges=[
                    ("ConnectionSolver", "..>", "BeamSolverResult", "returns"),
                    ("PlateConnectionSolver", "..>", "PlateSolverResult", "returns"),
                    ("ConnectionSolver", "..>", "JointTopology", "classifies as"),
                    ("TimberModel", "..>", "JointCandidate", "creates"),
                    ("TimberModel", "..>", "PlateJointCandidate", "creates"),
                    ("Joint", "..>", "Cluster", "promotes"),
                ],
            ),
            dict(
                intro="""
### Beam Joints

Beam joints join two or more `Beam` elements. Generic bases (`ButtJoint`, `LapJoint`, `MortiseTenonJoint`) share logic across topology-specific implementations. `CutPlaneSpec` and `MiterPlaneSpec` describe cutting planes relative to a beam's reference side (so they survive model transformations) and are passed to the butt/miter joint constructors via the `butt_plane_spec` / `back_plane_spec` / `miter_plane` parameters; the joints expose the resolved world-coordinate planes as `butt_plane` / `back_plane` / `miter_plane` properties.
""",
                classes=[
                    "Joint", "CutPlaneSpec", "MiterPlaneSpec",
                    "ButtJoint", "LButtJoint", "TButtJoint", "YButtJoint",
                    "TBirdsmouthJoint", "LMiterJoint",
                    "LapJoint", "TLapJoint", "LLapJoint", "XLapJoint", "LFrenchRidgeLapJoint",
                    "BallNodeJoint", "TDovetailJoint", "TStepJoint",
                    "MortiseTenonJoint", "TTenonMortiseJoint", "LTenonMortiseJoint", "TOliGinaJoint",
                    "ISimpleScarf", "XNotchJoint",
                ],
                anchors={"Data": "abstract"},
                overrides={
                    "Joint": dict(exclude={"element_guids"}),
                    "LButtJoint": dict(keep={"create"}),
                    "ISimpleScarf": dict(exclude={"main_beam_guid", "cross_beam_guid"}),
                    "LapJoint": dict(add_stereotypes=["abstract"]),
                    "MortiseTenonJoint": dict(add_stereotypes=["abstract"]),
                },
                edges_title="Usage relationships",
                edges=[
                    ("ButtJoint", "..>", "CutPlaneSpec", "uses"),
                    ("LMiterJoint", "..>", "MiterPlaneSpec", "uses"),
                ],
            ),
            dict(
                intro="""
### Plate and Panel Joints

Plate joints connect two `Plate` elements along their outlines and are classified by the edge/edge or edge/face topologies. Panel joints reuse the plate joint geometry logic through multiple inheritance and additionally create `PanelConnectionInterface` features on the joined panels.
""",
                classes=[
                    "PlateJoint", "PlateJointCandidate", "PlateButtJoint", "PlateLButtJoint",
                    "PlateTButtJoint", "PlateMiterJoint",
                    "PanelJoint", "PanelLButtJoint", "PanelTButtJoint", "PanelMiterJoint",
                ],
                anchors={"Joint": "abstract"},
                overrides={
                    "PlateJoint": dict(add_stereotypes=["abstract"]),
                    "PlateButtJoint": dict(add_stereotypes=["abstract"]),
                    "PanelJoint": dict(add_stereotypes=["abstract"]),
                },
                edges=[],
            ),
        ],
    ),
    # ------------------------------------------------------------ fabrication
    dict(
        title="Fabrication Subsystem",
        prose="""
The fabrication subsystem handles manufacturing features and BTLx processing. All fabrication features inherit from `BTLxProcessing`. The BTLx core classes live in the `compas_timber.fabrication` package, while `BTLxReader` lives in the separate `compas_timber.btlx` package. `BTLxWriter`, `BTLxReader` and the part classes are plain XML-serialization helpers and do not inherit from `Data`. The subsystem is shown in two diagrams: the serialization infrastructure and the catalog of BTLx processings.
""",
        diagrams=[
            dict(
                intro="""
### BTLx Infrastructure

`BTLxWriter` walks a `TimberModel` and wraps each element in a `BTLxPart` (or `BTLxRawpart` for nesting stock) whose processings are serialized to BTLx XML; `BTLxReader` performs the reverse. `BTLxFromGeometryDefinition` defers the construction of a processing from arbitrary geometry until the target element is known. `Contour` and `DualContour` are parameter objects for the `FreeContour` processing, and `MachiningLimits` bundles the face-limitation flags used by several processings.
""",
                classes=[
                    "BTLxProcessing", "BTLxFromGeometryDefinition",
                    "BTLxWriter", "BTLxReader",
                    "BTLxGenericPart", "BTLxPart", "BTLxRawpart",
                    "Contour", "DualContour", "MachiningLimits",
                ],
                anchors={"Data": "abstract", "Stock": "abstract"},
                overrides={
                    "BTLxGenericPart": dict(add_stereotypes=["abstract"]),
                },
                edges=[
                    ("BTLxWriter", "..>", "BTLxPart", "creates"),
                    ("BTLxWriter", "..>", "BTLxRawpart", "creates"),
                    ("BTLxReader", "..>", "BTLxProcessing", "deserializes"),
                    ("BTLxPart", "o--", "BTLxProcessing", "contains", "processings"),
                    ("BTLxRawpart", "..>", "Stock", "references", "stock"),
                ],
            ),
            dict(
                intro="""
### BTLx Processings

Each processing class represents one BTLx machining operation and is instantiated through alternative constructors (e.g. `from_plane_and_beam()`) rather than directly. The constants classes at the bottom (`OrientationType`, `StepShapeType`, `TenonShapeType`, `AlignmentType`, `EdgePositionType`, `LimitationTopType`) enumerate the allowed values of the string-valued parameters. Several processings also export a lightweight `*Proxy` companion (`JackRafterCutProxy`, `DoubleCutProxy`, `DrillingProxy`, `LapProxy`, `PocketProxy`, `LongitudinalCutProxy`) that defers the expensive parameter computation until the processing is actually applied; proxies mirror the alternative constructors of their processing and are omitted from the diagram.
""",
                classes=[
                    "JackRafterCut", "DoubleCut", "Drilling", "Lap", "Slot", "Pocket",
                    "Tenon", "Mortise", "DovetailTenon", "DovetailMortise",
                    "StepJoint", "StepJointNotch", "FrenchRidgeLap", "SimpleScarf",
                    "FreeContour", "Text", "LongitudinalCut",
                    "OrientationType", "StepShapeType", "TenonShapeType",
                    "AlignmentType", "EdgePositionType", "LimitationTopType",
                ],
                anchors={"BTLxProcessing": "abstract", "Contour": None, "DualContour": None},
                overrides={
                    "OrientationType": dict(add_stereotypes=["enumeration"]),
                    "StepShapeType": dict(add_stereotypes=["enumeration"]),
                    "TenonShapeType": dict(add_stereotypes=["enumeration"]),
                    "AlignmentType": dict(add_stereotypes=["enumeration"]),
                    "EdgePositionType": dict(add_stereotypes=["enumeration"]),
                    "LimitationTopType": dict(add_stereotypes=["enumeration"]),
                },
                edges=[
                    ("FreeContour", "o--", "Contour", "contains", "contour_param_object"),
                    ("FreeContour", "o--", "DualContour", "contains"),
                ],
            ),
        ],
    ),
    # --------------------------------------------------------------- planning
    dict(
        title="Planning Subsystem",
        prose="""
The planning subsystem covers fabrication planning: nesting elements into stock material and sequencing assembly instructions. It lives in `compas_timber.planning`.
""",
        diagrams=[
            dict(
                intro="""
### Nesting

`BeamNester` optimizes the 1D nesting of a model's beams into `BeamStock` pieces from a stock catalog, returning a serializable `NestingResult`. Each `Stock` piece records the elements assigned to it as `NestedElementData`.
""",
                classes=["Stock", "BeamStock", "PlateStock", "NestedElementData", "NestingResult", "BeamNester"],
                anchors={"Data": "abstract", "TimberModel": None},
                overrides={
                    "BeamStock": dict(exclude={"_remaining_length"}),
                },
                edges=[
                    ("BeamNester", "..>", "TimberModel", "nests beams of", "model"),
                    ("BeamNester", "..>", "NestingResult", "returns"),
                    ("NestingResult", "o--", "Stock", "contains", "stocks"),
                    ("Stock", "o--", "NestedElementData", "contains", "element_data"),
                ],
            ),
            dict(
                intro="""
### Assembly Sequencing

A `BuildingPlan` is an ordered collection of `Step`s, each holding the `Instruction`s (3D models, text overlays, dimensions) needed to assemble one or more elements, executed by an `Actor`. `SimpleSequenceGenerator` produces a one-step-per-element plan from a model, and `BuildingPlanParser` reads/writes plans as JSON.
""",
                classes=[
                    "BuildingPlan", "Step", "Instruction", "Model3d", "Text3d", "LinearDimension",
                    "Actor", "SimpleSequenceGenerator", "BuildingPlanParser",
                ],
                anchors={"Data": "abstract"},
                overrides={
                    "Instruction": dict(add_stereotypes=["abstract"]),
                    "Actor": dict(add_stereotypes=["enumeration"]),
                },
                edges=[
                    ("BuildingPlan", "o--", "Step", "contains", "steps"),
                    ("Step", "o--", "Instruction", "contains", "instructions"),
                    ("Step", "..>", "Actor", "executed by", "actor"),
                    ("SimpleSequenceGenerator", "..>", "BuildingPlan", "generates", "result"),
                    ("BuildingPlanParser", "..>", "BuildingPlan", "parses and serializes"),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------- structural
    dict(
        title="Structural Subsystem",
        prose="""
The structural subsystem (`compas_timber.structural`) derives a `StructuralGraph` — a compas `Graph` of `StructuralSegment`s — from a `TimberModel`, for downstream structural analysis. `BeamStructuralElementSolver` produces the segments: a `BeamSegmentGenerator` splits each beam's centerline at joint locations, and a `JointConnectorGenerator` adds connector segments between non-intersecting centerlines. `InteractionType` selects whether joints, joint candidates, or both are considered.
""",
        diagrams=[
            dict(
                classes=[
                    "StructuralGraph", "StructuralSegment", "BeamStructuralElementSolver",
                    "BeamSegmentGenerator", "SimpleBeamSegmentGenerator",
                    "JointConnectorGenerator", "SimpleJointConnectorGenerator",
                    "InteractionType",
                ],
                anchors={"Graph": "compas", "Data": "abstract", "TimberModel": None},
                overrides={},
                edges=[
                    ("StructuralGraph", "..>", "TimberModel", "built from"),
                    ("BeamStructuralElementSolver", "*--", "BeamSegmentGenerator", "uses", "beam_segment_generator"),
                    ("BeamStructuralElementSolver", "*--", "JointConnectorGenerator", "uses", "joint_connector_generator"),
                    ("BeamStructuralElementSolver", "..>", "StructuralSegment", "creates"),
                    ("BeamStructuralElementSolver", "..>", "InteractionType", "uses"),
                ],
            ),
        ],
    ),
    # ----------------------------------------------------------------- errors
    dict(
        title="Errors Subsystem",
        prose="""
The errors subsystem provides specialized exception classes for different types of failures that can occur during timber modeling, joint creation, fabrication, and processing operations.
""",
        diagrams=[
            dict(
                classes=[
                    "FeatureApplicationError", "BeamJoiningError", "FastenerApplicationError",
                    "BTLxProcessingError", "BTLxParsingError",
                ],
                anchors={"Exception": "builtin"},
                overrides={},
                edges=[],
            ),
        ],
    ),
]
