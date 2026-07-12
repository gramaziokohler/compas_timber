# Joints Contribution Guide

Joints represent the interaction between two or more timber elements to form structural connections. They coordinate the application of BTLx processings (features) across participating elements to achieve the desired joint geometry.

!!! note
    For implementing new BTLx Processings, see the [BTLx Contribution Guide](BTLx_contribution_guide.md).
    For an overview of the `Joint` class hierarchy and the topology solving machinery, see the [Class Diagrams](class_diagrams.md#connections-subsystem).

## Creating a New Joint

### 1. Define Joint Requirements and Analyze Element Relationships

Before implementation, establish the joint specifications and study how the involved elements interact geometrically:

**Joint Specifications:**

- The specific timber joint type you're creating
- Required BTLx processings for the joint geometry
- Target elements for each processing operation

**Identify Joint Topology**: Determine the connection topology using the `JointTopology` values (defined in `compas_timber.connections`):

- `TOPO_I`: End-to-end joint between two parallel beams (straight line)
- `TOPO_L`: End-to-end joint between two non-parallel beams (corner)
- `TOPO_T`: End-to-middle joint between two beams
- `TOPO_X`: Middle-to-middle joint between two beams (crossing)
- `TOPO_Y`: Joint between three or more beams where all beams meet at their ends (e.g. `YButtJoint`, `BallNodeJoint`)
- `TOPO_K`: Joint between three or more beams where at least one beam meets in the middle
- `TOPO_EDGE_EDGE`: Joint between two plates/panels whose edges are aligned (e.g. `PlateLButtJoint`, `PlateMiterJoint`)
- `TOPO_EDGE_FACE`: Joint between two plates/panels where the edge of one lies on the face of the other (e.g. `PlateTButtJoint`)

`TOPO_UNKNOWN` is the fallback used by the solvers when no topology could be determined.

**Define Element Roles**: Assign specific roles to each participating element, if relevant:

!!! note
    Some joint topologies or specific joint types require clear distinctions between participating elements (e.g., `main beam` vs. `cross beam`), while others treat all elements equally.
    Consider whether your joint implementation needs element role differentiation.
    For inline topologies (`TOPO_I`, e.g. `ISimpleScarf`), the elements are collinear rather than intersecting, so roles like `main_beam` and `cross_beam` simply denote the first and second connected segments.


### 2. Create the Joint Class

Create a new module in `src/compas_timber/connections/` that inherits from `Joint`.  Based on the identified topology and joint type, name the joint class accordingly (e.g., `TButtJoint` for a **TOPO-T** butt joint).
The following methods and attributes are the absolute minimum required to implement a joint:

- `SUPPORTED_TOPOLOGY` : Class attribute matching the joint topology (one of the `JointTopology` values listed above, e.g. `JointTopology.TOPO_T`)

- `__init__()` : Must accept its elements with `None` defaults (required for deserialization) and pass them to the base class via `elements=(...)`

- `__data__` : Property returning a dictionary of joint data for serialization (element GUIDs are stored by the base class)

!!! note
    Joints can inherit from a generic base class (e.g., `ButtJoint`) to share common logic across topology-specific implementations (e.g., `LButtJoint`, `TButtJoint`).
    The base class provides shared methods while concrete classes define topology-specific behavior.

#### Example:

```python
class TNewJoint(Joint):
    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T  # need to match the joint topology

    @property
    def __data__(self):
        data = super(TNewJoint, self).__data__
        data["arg_a"] = self.arg_a
        data["arg_b"] = self.arg_b
        return data

    def __init__(self, main_beam=None, cross_beam=None, arg_a=None, arg_b=None, **kwargs):
        super(TNewJoint, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.arg_a = arg_a or "default_value_a"
        self.arg_b = arg_b or "default_value_b"

        self.features = []  # List to hold BTLx processings (features) for this joint

    @property
    def main_beam(self):
        """Role-specific alias for the first element in the joint."""
        return self.element_a

    @property
    def cross_beam(self):
        """Role-specific alias for the second element in the joint."""
        return self.element_b
```

!!! note
    Element references cannot be directly serialized. The base `Joint` class stores element GUIDs and restores the references automatically during deserialization (`restore_elements_from_keys()`).
    If your joint has attributes derived from its elements that must be recomputed after deserialization, implement the `_set_unset_attributes()` hook — it is called by the base class once the elements have been restored.

See also:

- `TButtJoint`
- `LMiterJoint`
- `XLapJoint`
- `TBirdsmouthJoint`
- `TStepJoint`
- `LFrenchRidgeLapJoint`


### 3. Implement Core Methods

Implement the following methods in your joint class:

- `add_features()`: Create BTLx processing instances via their alternative constructors and assign them to target elements.

- `add_extensions()`: Modify element geometry (such as extending beam lengths) to accommodate the joint requirements and ensure geometric feasibility.

- `check_elements_compatibility()`: Validate that the elements meet necessary joint requirements if applicable, such as dimensions or coplanarity. This is a *classmethod* that receives the elements as an argument, so it can be called before the joint is instantiated; `process_joinery()` also calls it on each joint's elements.

#### Example:

```python
class TNewJoint(Joint):
    # ... other methods ...

    def add_extensions(self):
        """Calculates and adds the necessary extensions to the beams."""
        assert self.cross_beam and self.main_beam
        try:
            plane_a = self.main_beam_cutting_plane() # beam should be extended to this plane
            start_a, end_a = self.main_beam.extension_to_plane(plane_a) # calculate the extension lengths
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.guid) # apply the extension to the main beam, keyed by this joint's guid


    def add_features(self):
        """Adds the required features in the form of BTLxProcessings to both beams."""
        assert self.cross_beam and self.main_beam

        # create a BTLx processing for the main beam
        main_feature = NewProcessing.from_plane_and_beam(
            plane=self.main_beam_cutting_plane(),
            beam=self.main_beam,
            arg_a=self.arg_a,
            arg_b=self.arg_b,
            ref_side_index=self.main_ref_side_index()
        )
        self.main_beam.add_features(main_feature)  # register the feature to the main beam

        # create a BTLx processing for the cross beam
        cross_feature = # ... Similar logic to create the BTLx processing for the cross beam ...
        self.cross_beam.add_features(cross_feature)  # register the feature to the cross

        self.features.extend([main_feature, cross_feature])  # register the features to the joint itself

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks if the elements are compatible for the creation of the joint."""
        main_beam, cross_beam = elements
        are_compatible = # ... Logic to check if the main and cross beams are compatible for the joint ...
        if not are_compatible:
            if not raise_error:
                return False
            raise BeamJoiningError(
                beams=elements,
                joint=cls,
                debug_info="The main and cross beams are not compatible for the joint."
            )
        return True
```

!!! note
    In the `add_features()` method, register each BTLx processing (feature) both to the corresponding element using `element.add_features()` and to the joint itself using `self.features.append(feature)`.
    This ensures features are properly associated for both element modification and joint serialization.

See also:

- `ButtJoint.add_extensions()`
- `LMiterJoint.add_extensions()`
- `XLapJoint.add_features()`
- `TBirdsmouthJoint.add_features()`
- `TStepJoint.check_elements_compatibility()`
- `LFrenchRidgeLapJoint.check_elements_compatibility()`

### 4. Update Module Imports

Add your new joint class to `src/compas_timber/connections/__init__.py` so it can be imported by other modules.

### 5. Add Tests

Add unit tests in `tests/compas_timber/` to verify your joint works correctly. Ensure you cover:

- BTLx processing creation and assignment in the `add_features()` method
- Geometry modification in the `add_extensions()` method
- Compatibility checks in the `check_elements_compatibility()` method


## Key Considerations

**Inheritance Patterns**:
Use base classes for shared joint logic across topologies.
Concrete classes should define topology-specific behavior and declare their `SUPPORTED_TOPOLOGY`.
Avoid code duplication between similar joint types by leveraging inheritance.

**Element Ordering**:
Maintain consistent element ordering in joint constructors and method signatures.
When elements have specific roles, always use the same parameter order (e.g., `main_beam` first, `cross_beam` second) across all joint methods.

**Error Handling**:
Use `BeamJoiningError` for joint-specific failures with meaningful debug information.
Include element references and joint context in error messages to aid debugging.

**Serialization Requirements**:
Element GUIDs are stored and restored automatically by the base `Joint` class.
Implement `_set_unset_attributes()` if element-derived attributes need recomputing after deserialization.
Include all joint parameters in the `__data__` property for complete serialization.
