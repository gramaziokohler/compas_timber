"""Test scenario for merge_model feature.

This script demonstrates the expected behavior of merging two TimberModels.
"""

from compas.geometry import Frame, Point, Vector
from compas_timber.elements import Beam
from compas_timber.connections import LButtJoint
from compas_timber.model import TimberModel

# ============================================================================
# Setup: two independent models
# ============================================================================

# model_a: two beams with a joint
model_a = TimberModel()
a1 = Beam(Frame.worldXY(), length=1.0, width=0.1, height=0.1)
a2 = Beam(Frame.worldYZ(), length=1.0, width=0.1, height=0.1)
model_a.add_element(a1)
model_a.add_element(a2)
LButtJoint.create(model_a, a1, a2)

print("model_a before merge:")
print("  beams:", len(model_a.beams))
print("  joints:", len(list(model_a.joints)))
print("  graph nodes:", len(list(model_a.graph.nodes())))
print("  graph edges:", len(list(model_a.graph.edges())))

# model_b: two beams with a joint
model_b = TimberModel()
b1 = Beam(Frame(Point(5, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=1.0, width=0.1, height=0.1)
b2 = Beam(Frame(Point(5, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)), length=1.0, width=0.1, height=0.1)
model_b.add_element(b1)
model_b.add_element(b2)
LButtJoint.create(model_b, b1, b2)

print("\nmodel_b before merge:")
print("  beams:", len(model_b.beams))
print("  joints:", len(list(model_b.joints)))

# ============================================================================
# Merge model_b into model_a (no parent => under root)
# ============================================================================

model_a.merge_model(model_b)

print("\nmodel_a after merge:")
print("  beams:", len(model_a.beams))  # expect 4
print("  joints:", len(list(model_a.joints)))  # expect 2
print("  graph nodes:", len(list(model_a.graph.nodes())))  # expect 4
print("  graph edges:", len(list(model_a.graph.edges())))  # expect 2

assert len(model_a.beams) == 4, f"Expected 4 beams, got {len(model_a.beams)}"
assert len(list(model_a.joints)) == 2, f"Expected 2 joints, got {len(list(model_a.joints))}"
assert len(list(model_a.graph.nodes())) == 4, f"Expected 4 graph nodes, got {len(list(model_a.graph.nodes()))}"
assert len(list(model_a.graph.edges())) == 2, f"Expected 2 graph edges, got {len(list(model_a.graph.edges()))}"

# All four beams should be accessible
assert b1 in model_a.beams
assert b2 in model_a.beams
assert a1 in model_a.beams
assert a2 in model_a.beams

print("\n--- All assertions passed! ---")

# ============================================================================
# Merge with parent: model_c into model_d under a specific parent element
# ============================================================================

model_d = TimberModel()
parent_beam = Beam(Frame.worldXY(), length=2.0, width=0.2, height=0.2)
model_d.add_element(parent_beam)

model_c = TimberModel()
c1 = Beam(Frame(Point(10, 0, 0), Vector(1, 0, 0), Vector(0, 1, 0)), length=0.5, width=0.05, height=0.05)
model_c.add_element(c1)

model_d.merge_model(model_c, parent=parent_beam)

# c1 should be a child of parent_beam in the tree hierarchy
assert c1 in model_d.beams
assert c1.treenode.parent.element is parent_beam

print("--- Parent merge assertions passed! ---")
