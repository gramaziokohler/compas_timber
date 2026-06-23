# Feature: PanelConnectionInterface FeatureAgent

## Proposal
Add a `PanelConnectionInterfaceAgent` system so that `PanelConnectionInterface` (PCI) features — added to panels by `PanelJoint.add_features()` — drive population of additional elements and fabrication features during panel population. The mechanism mirrors how `OpeningPopulatorAgent` handles `Opening` features, but must be flexible enough to express many different connection construction details.

## Reason
Currently `PanelJoint.add_features()` adds a PCI to each panel and `PanelPopulator.parse_default_feature_agents()` already auto-instantiates a FeatureAgent for any feature it finds in `panel.features` — but there is no FeatureAgent subclass for `PanelConnectionInterface`, so PCIs are silently ignored during population. The missing agent is what closes the loop between the panel-joint geometry and the physical construction detail at that joint.

## Concept
1. A `PanelJoint` (e.g. `PanelLLayerButtJoint`) runs `add_features()` → adds a `PanelConnectionInterface` to each panel.
2. The user provides a prototype `PanelConnectionInterfaceAgent` subclass in the `default_feature_agents` dict passed to `PanelPopulator`.
3. `parse_default_feature_agents()` finds the PCI in `panel.features`, clones the prototype, binds the concrete PCI feature, and appends it to `self.agents`.
4. During `generate_elements()`, the PCI agent creates connection-specific elements (e.g. doubler studs, nailing blocks, connectors, trimming plates) on the configured layers.
5. During `join_elements()`, the PCI agent's internal/external joint rules drive how those elements connect to the panel's other framing elements.

Usage scenario:
- Wall panel A (main) + wall panel B (cross) joined by a `PanelLLayerButtJoint`.
- The joint adds a `PanelConnectionInterface(role=MAIN)` to panel A and `PanelConnectionInterface(role=CROSS)` to panel B.
- A concrete `LButtConnectionAgent(PanelConnectionInterfaceAgent)` prototype is in the populator config.
- On population of panel A, the agent generates a doubled edge stud at the connection edge and sets up a joint rule between it and the standard edge stud.

## Location
- Abstract base: `timber_design/src/timber_design/populators/populator_agents/pci_agent.py`
  - Class: `PanelConnectionInterfaceAgent(FeatureAgent)`
- Concrete subclasses: same file (or separate files for large implementations)
- Registered in populator config via `default_feature_agents={PanelConnectionInterface: <prototype>}`

## Tools & dependencies
- `compas_timber.panel_features.PanelConnectionInterface` — the feature type triggering the agent
- `compas_timber.panel_features.InterfaceRole` — may inform agent behavior (not yet used)
- `FeatureAgent` (base class, `timber_design`)
- PCI geometry: `pci.polyline`, `pci.frame`, `pci.edge_index`, `pci.width`
- Layer geometry for projecting the PCI onto each layer (same approach as `OpeningPopulatorAgent._create_frame_polylines`)
- `Beam2D`, `ConnectionSolver2D`, `CategoryRule`, `DirectRule` — all already in scope

## Patterns to follow
- `OpeningPopulatorAgent` — primary model: abstract feature type, `generate_elements_for_layer()`, `_compute_outline_for_layer()`, `extend_elements()`, `INTERNAL_JOINT_RULES`, `EXTERNAL_JOINT_RULES`
- `EdgePopulatorAgent` — secondary model: how edge/boundary geometry is derived from panel outline + edge planes

## Open questions
- **What does v1 concrete subclass look like?** What is the simplest construction detail to implement alongside the abstract base? (e.g. a doubled edge stud, a nailing plate, a connector block, or simply a pass-through agent that only carries joint-rule overrides with no generated elements)
- **`_compute_outline_for_layer` footprint shape**: should the PCI agent's boundary outline be the thin edge strip (one edge × panel thickness), and if so, what `BOUNDARY_TYPE`? (NONE, INCLUSIVE at the edge, or EXCLUSIVE?)

## Agreed design
_To be filled once all questions are resolved._
