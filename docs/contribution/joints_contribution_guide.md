# Joints Contribution Guide

Joints represent the interaction between two or more timber elements to form structural connections. They coordinate the application of BTLx processings (features) across participating elements to achieve the desired joint geometry.

!!! note
    For implementing new BTLx Processings, see the [BTLx Contribution Guide](BTLx_contribution_guide.md).

## Creating a New Joint

### 1. Define Joint Requirements and Analyze Element Relationships

Before implementation, establish the joint specifications and study how the involved elements interact geometrically:

**Joint Specifications:**

- The specific timber joint type you're creating
- Required BTLx processings for the joint geometry
- Target elements for each processing operation

**Identify Joint Topology**: Determine the connection topology using standard notation:

- `TOPO-X`: Elements both interacting somewhere along their lengths
- `TOPO-L`: Elements meeting at their ends at an angle
- `TOPO-T`: One element's end intersecting another element along its length
- `TOPO-I`: Elements joined end-to-end in a straight line

**Define Element Roles**: Assign specific roles to each participating element, if relevant:

!!! note
    Some joint topologies or specific joint types require clear distinctions between participating elements (e.g., `main beam` vs. `cross beam`), while others treat all elements equally.
    Consider whether your joint implementation needs element role differentiation.


### 2. Create the Joint Class

Create a new module in `src/compas_timber/connections/` that inherits from `Joint`.  Based on the identified topology and joint type, name the joint class accordingly (e.g., `TButtJoint` for a **TOPO-T** butt joint).
The following methods and attributes are the absolute minimum required to implement a joint:

- `SUPPORTED_TOPOLOGY` : Class attribute matching the joint topology (`JointTopology.TOPO_X`, `JointTopology.TOPO_L`, `JointTopology.TOPO_T`, or `JointTopology.TOPO_I`)

- `__init__()` :

- `__data__` : Property returning a dictionary of joint data for serialization

- `elements` : Property returning a list of participating elements

- `restore_beams_from_keys()` : Method for restoring beam references after deserialization

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
        data["main_beam_guid"] = self.main_beam_guid
        data["cross_beam_guid"] = self.cross_beam_guid
        data["arg_a"] = self.arg_a
        data["arg_b"] = self.arg_b
        return data

    def __init__(self, main_beam, cross_beam, arg_a=None, arg_b=None, **kwargs):
        super(TNewJoint, self).__init__(**kwargs)
        self.main_beam = main_beam
        self.cross_beam = cross_beam
        self.main_beam_guid = kwargs.get("main_beam_guid", None) or str(main_beam.guid)
        self.cross_beam_guid = kwargs.get("cross_beam_guid", None) or str(cross_beam.guid)
        self.arg_a = arg_a or "default_value_a"
        self.arg_b = arg_b or "default_value_b"

        self.features = []  # List to hold BTLx processings (features) for this joint

    @property
    def elements(self):
        """Returns a list of participating elements in the joint."""
        return [self.main_beam, self.cross_beam]

    def restore_beams_from_keys(self):
        """After de-serialization, restores references to the main and cross beams saved in the model."""
        self.main_beam = model[self.main_beam_guid]
        self.cross_beam = model[self.cross_beam_guid]
```

!!! note
    Element references cannot be directly serialized, so joints store element GUIDs for persistence and restore references during deserialization.

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

- `check_elements_compatibility()`: Validate that the elements meet necessary joint requirements if applicable, such as dimensions or coplanarity.

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
            raise BeamJoiningError(self.main_beam, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start_a, end_a, self.main_beam_guid) # apply the extension to the main beam


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

    def check_elements_compatibility(self):
        """Checks if the elements are compatible for the creation of the joint."""
        assert self.cross_beam and self.main_beam
        are_compatible = # ... Logic to check if the main and cross beams are compatible for the joint ...
        if not are_compatible:
            raise BeamJoiningError(
                self.elements,
                self,
                debug_info="The main and cross beams are not compatible for the joint."
            )
```

!!! note
    In the `add_features()` method, register each BTLx processing (feature) both to the corresponding element using `element.add_features()` and to the joint itself using `self.features.append(feature)`.
    This ensures features are properly associated for both element modification and joint serialization.

See also:

- `TButtJoint.add_extensions()`
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
Store element GUIDs, not direct references, for persistence.
Implement proper `restore_beams_from_keys()` to rebuild element relationships after deserialization.
Include all joint parameters in the `__data__` property for complete serialization.
