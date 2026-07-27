# Curated spec for gen_diagrams.py. Class bodies come from graph.json;
# this file only decides partitioning, prose, anchors, overrides, and edges.
# Edge tuples with 5 items are machine-checked: (owner, op, target, label, owner_attr).

HEADER = """# Class Diagrams

This section provides visual representations of the class hierarchies and relationships in different subsystems of COMPAS Timber. This is to help developers better understand the codebase and to document the interface of the different classes.

The diagrams are generated from the source code (attributes, methods and inheritance are extracted with Python's `ast`), so they reflect the code at the version noted in the changelog rather than an idealized design. Members inherited from `compas` / `compas_model` base classes are not repeated on subclasses.

This page is generated — do not edit it by hand. To regenerate it after code changes, see the pipeline in [`scripts/docs_class_diagrams/`](https://github.com/gramaziokohler/compas_timber/tree/main/scripts/docs_class_diagrams).

[TOC]
"""

SECTIONS = [
    # --------------------------------------------------------------- elements
    dict(
        title="Elements Subsystem",
        prose="""
The elements subsystem contains all the core timber elements that can be modeled and manipulated. `Beam` and `Plate` inherit from the base `TimberElement` class, while `Panel`, `Fastener` and `PanelFeature` inherit directly from compas_model's `Element`. `Plate` and `Panel` delegate their outline/plane logic to a shared, composed `PlateGeometry` object. `frame` and element-tree bookkeeping are inherited from compas_model's `Element` and are not repeated below. The legacy `Feature` classes (`CutFeature`, `DrillFeature`, `MillVolume`, `BrepSubtraction`) predate the BTLx-based features; they are no longer used internally and are omitted from the diagram, but remain exported from `compas_timber.elements` for backward compatibility.
""",
        diagrams=[
            dict(
                classes=[
                    "TimberElement", "Beam", "Plate", "PlateGeometry",
                    "Fastener", "BallNodeFastener", "PlateFastener", "FastenerTimberInterface",
                    "Panel", "PanelType", "PanelFeature", "PanelFeatureType",
                    "Opening", "OpeningType", "PanelConnectionInterface", "InterfaceRole",
                ],
                anchors={"Element": "compas_model"},
                overrides={
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
The connections subsystem defines joints and their relationships. All joints inherit from the abstract `Joint` class (a `compas.data.Data` subclass; `Data` is omitted from the diagram since every class here derives from it) and declare the topology they support via `SUPPORTED_TOPOLOGY`. Joints are registered in the `TimberModel` and referenced from the edges of its interaction graph.

Beam joints join two or more `Beam` elements; the generic bases `ButtJoint`, `LapJoint` and `MortiseTenonJoint` share logic across the topology-specific implementations. `CutPlaneSpec` and `MiterPlaneSpec` describe cutting planes relative to a beam's reference side (so they survive model transformations) and are passed to the butt/miter joint constructors via the `butt_plane_spec` / `back_plane_spec` / `miter_plane` parameters.

Plate joints connect two `Plate` elements along their outlines; panel joints reuse the plate joint geometry logic through multiple inheritance. `JointCandidate` / `PlateJointCandidate` are placeholders registered by `TimberModel.connect_adjacent_*()`, which can later be promoted to concrete joints with `Joint.promote_joint_candidate()`.
""",
        diagrams=[
            dict(
                classes=[
                    "Joint", "JointCandidate", "CutPlaneSpec", "MiterPlaneSpec",
                    "ButtJoint", "LButtJoint", "TButtJoint", "YButtJoint",
                    "TBirdsmouthJoint", "LMiterJoint",
                    "LapJoint", "TLapJoint", "LLapJoint", "XLapJoint", "LFrenchRidgeLapJoint",
                    "BallNodeJoint", "TDovetailJoint", "TStepJoint",
                    "MortiseTenonJoint", "TTenonMortiseJoint", "LTenonMortiseJoint", "TOliGinaJoint",
                    "ISimpleScarf", "XNotchJoint",
                    "PlateJoint", "PlateJointCandidate", "PlateButtJoint", "PlateLButtJoint",
                    "PlateTButtJoint", "PlateMiterJoint",
                    "PanelJoint", "PanelLButtJoint", "PanelTButtJoint", "PanelMiterJoint",
                ],
                anchors={},
                overrides={
                    "Joint": dict(exclude={"element_guids"}),
                    "LButtJoint": dict(keep={"create"}),
                    "ISimpleScarf": dict(exclude={"main_beam_guid", "cross_beam_guid"}),
                    "LapJoint": dict(add_stereotypes=["abstract"]),
                    "MortiseTenonJoint": dict(add_stereotypes=["abstract"]),
                    "PlateJoint": dict(add_stereotypes=["abstract"]),
                    "PlateButtJoint": dict(add_stereotypes=["abstract"]),
                    "PanelJoint": dict(add_stereotypes=["abstract"]),
                },
                edges_title="Usage relationships",
                edges=[
                    ("ButtJoint", "..>", "CutPlaneSpec", "uses"),
                    ("LMiterJoint", "..>", "MiterPlaneSpec", "uses"),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------ fabrication
    dict(
        title="Fabrication Subsystem",
        prose="""
The fabrication subsystem handles manufacturing features and BTLx processing. All fabrication features inherit from `BTLxProcessing` (a `compas.data.Data` subclass; `Data` is omitted from the diagram); each processing class represents one BTLx machining operation and is instantiated through alternative constructors (e.g. `from_plane_and_beam()`) rather than directly. Several processings also export a lightweight `*Proxy` companion (`JackRafterCutProxy`, `DoubleCutProxy`, `DrillingProxy`, `LapProxy`, `PocketProxy`, `LongitudinalCutProxy`) that defers the expensive parameter computation until the processing is actually applied; proxies mirror the alternative constructors of their processing and are omitted from the diagram.

`BTLxWriter` walks a `TimberModel` and wraps each element in a `BTLxPart` (or `BTLxRawpart` for nesting stock) whose processings are serialized to BTLx XML; `BTLxReader` (in the separate `compas_timber.btlx` package) performs the reverse. `BTLxWriter`, `BTLxReader` and the part classes are plain XML-serialization helpers and do not inherit from `Data`.

The remaining classes are parameter helpers. `BTLxFromGeometryDefinition` defers the construction of a processing from arbitrary geometry until the target element is known. `Contour` and `DualContour` are parameter objects for the `FreeContour` processing, and `MachiningLimits` bundles the face-limitation flags used by `Lap`, `Slot` and `Pocket`. The constants classes (`OrientationType`, `StepShapeType`, `TenonShapeType`, `AlignmentType`, `EdgePositionType`, `LimitationTopType`) enumerate the allowed values of the string-valued parameters; `OrientationType` in particular is used by the `orientation` parameter of nearly every processing, so only a representative edge from `BTLxProcessing` is drawn.
""",
        diagrams=[
            dict(
                classes=[
                    "BTLxProcessing", "BTLxFromGeometryDefinition",
                    "BTLxWriter", "BTLxReader",
                    "BTLxGenericPart", "BTLxPart", "BTLxRawpart",
                    "Contour", "DualContour", "MachiningLimits",
                    "JackRafterCut", "DoubleCut", "Drilling", "Lap", "Slot", "Pocket",
                    "Tenon", "Mortise", "DovetailTenon", "DovetailMortise",
                    "StepJoint", "StepJointNotch", "FrenchRidgeLap", "SimpleScarf",
                    "FreeContour", "Text", "LongitudinalCut",
                    "OrientationType", "StepShapeType", "TenonShapeType",
                    "AlignmentType", "EdgePositionType", "LimitationTopType",
                ],
                anchors={"Stock": "abstract"},
                overrides={
                    "BTLxGenericPart": dict(add_stereotypes=["abstract"]),
                    "OrientationType": dict(add_stereotypes=["enumeration"]),
                    "StepShapeType": dict(add_stereotypes=["enumeration"]),
                    "TenonShapeType": dict(add_stereotypes=["enumeration"]),
                    "AlignmentType": dict(add_stereotypes=["enumeration"]),
                    "EdgePositionType": dict(add_stereotypes=["enumeration"]),
                    "LimitationTopType": dict(add_stereotypes=["enumeration"]),
                },
                edges=[
                    ("BTLxWriter", "..>", "BTLxPart", "creates"),
                    ("BTLxWriter", "..>", "BTLxRawpart", "creates"),
                    ("BTLxReader", "..>", "BTLxProcessing", "deserializes"),
                    ("BTLxPart", "o--", "BTLxProcessing", "contains", "processings"),
                    ("BTLxRawpart", "..>", "Stock", "references", "stock"),
                    ("BTLxFromGeometryDefinition", "..>", "BTLxProcessing", "instantiates", "processing"),
                    ("FreeContour", "o--", "Contour", "contains", "contour_param_object"),
                    ("FreeContour", "o--", "DualContour", "contains"),
                    ("Lap", "..>", "MachiningLimits", "uses", "machining_limits"),
                    ("Slot", "..>", "MachiningLimits", "uses", "machining_limits"),
                    ("Pocket", "..>", "MachiningLimits", "uses", "machining_limits"),
                    ("BTLxProcessing", "..>", "OrientationType", "orientation values"),
                    ("BTLxProcessing", "..>", "AlignmentType", "uses", "tool_position"),
                    ("Text", "..>", "AlignmentType", "uses", "alignment_vertical"),
                    ("StepJoint", "..>", "StepShapeType", "uses", "step_shape"),
                    ("StepJointNotch", "..>", "StepShapeType", "uses", "step_shape"),
                    ("Tenon", "..>", "TenonShapeType", "uses", "shape"),
                    ("Mortise", "..>", "TenonShapeType", "uses", "shape"),
                    ("DovetailTenon", "..>", "TenonShapeType", "uses", "shape"),
                    ("DovetailMortise", "..>", "TenonShapeType", "uses", "shape"),
                    ("DovetailMortise", "..>", "LimitationTopType", "uses", "limitation_top"),
                    ("FrenchRidgeLap", "..>", "EdgePositionType", "uses", "ref_position"),
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
