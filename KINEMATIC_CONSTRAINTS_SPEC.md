# Feature Specification: Assembly Sequencing via Kinematic Escape Constraints

## Overview
This document outlines the architecture for automatically calculating robotic assembly sequences and insertion vectors in `compas_timber`. 

Because forward-planning an assembly sequence can lead to kinematic dead-ends, this architecture uses **Disassembly Planning**. By defining the mathematical "escape constraints" of individual joints, a solver can work backwards from the completed `TimberModel` to deduce a collision-free, kinematically sound assembly sequence.

---

## 1. The Geometric Constraints (Degrees of Freedom)
When querying a joint for its freedom, it will return one of the following `compas.geometry` objects (or lists thereof) representing the mathematical space the `moving_element` can travel assuming the other element is frozen:

* **`compas.geometry.Line` (1 DOF):** Strict linear sliding (e.g., Mortise & Tenon, Dovetail). The beam must move exactly along this line.
* **`list[compas.geometry.Vector]` (>= 2 DOF):** A collection of normal vectors, each defining a Half-Space. The beam can move anywhere as long as the dot product with *all* these vectors is positive (e.g., L-Butt Joint, Lap Joint). The intersection of these half-spaces (or half-spheres) represents the continuous space of valid insertion/extraction possibilities.

---

## 2. Base Joint Interface
**Target File:** `src/compas_timber/connections/joint.py`

The base `Joint` class defines the contract for all joints. It implements a generic fallback behavior for the kinematic constraint.

### Fallback Behavior
If a specific joint type does not override the kinematic constraint method, it falls back to a generic 3-DOF half-space. The generic half-space is defined by a single vector pointing from the midpoint of the static element's centerline to the midpoint of the moving element's centerline. This ensures that by default, the solver assumes the moving element can simply be pulled away from the static element.

---

## 3. Specific Joint Implementations (Polymorphism)
Subclasses override the base constraint method to provide exact, parameter-driven kinematics depending on their geometry.

### 3.1 L-Butt Joint
**Target File:** `src/compas_timber/connections/l_butt.py`

An L-Butt joint generally allows sliding anywhere along the cut plane or pulling directly away from it. 

- If it is a simple butt joint, it returns a single vector representing the normal of the butt plane pointing away from the static element.
- If a lap or pocket is milled, the movement is further constrained by the side walls of the pocket. In this case, the joint returns a list of vectors containing both the butt plane normal and the normal of the opposing pocket wall, creating an intersection of half-spaces that mathematically defines the restricted movement.

### 3.2 T-Dovetail Joint
**Target File:** `src/compas_timber/connections/t_dovetail.py`

A Dovetail joint physically locks the beam in all directions except exactly along the dovetail groove axis. Therefore, instead of a half-space, this joint returns a single `Line` object. The line defines the strict 1-DOF path the element must follow to slide into or out of the joint.

---

## 4. The Sequencer / Constraint Solver
**Target File:** `src/compas_timber/planning/insertion_solver.py` (New File)

The insertion solver takes a `TimberModel` and iteratively works backwards, computing the mathematical intersection of the geometries returned by the kinematic constraints of the joints.

For a single element, the solver must merge all constraints from its active joints:
- **Strict 1-DOF lock:** If **any** joint enforces a `Line` (1 DOF), the final escape vector must align with that line. If **multiple** joints enforce a `Line`, the solver verifies they are parallel; otherwise, the element is kinematically locked and cannot be extracted. The chosen line direction (or its reverse) must then be tested against all half-space constraints to ensure it doesn't push through solid material.
- **>= 2-DOF Intersection:** If there are **only** half-space constraints (`list[Vector]`), the solver must find a vector inside the intersecting convex cone. A simple heuristic is to unitize all boundary normals and sum them. If the resulting vector satisfies all half-space constraints (i.e., its dot product with all vectors is $\ge 0$), it is a valid extraction vector.

---

## 5. Assembly Sequence Deduction Algorithm

The overarching sequence is determined by **Disassembly Planning** (working backwards from the completed state). The solver attempts to greedily "pull" elements out of the structure one by one.

### The Algorithm:
1. **Initialize State:** Create a list of `remaining_elements` containing all beams in the assembly.
2. **Find a Free Element:** Iterate over `remaining_elements` and test if an element can be extracted.
    - To test an element, we must gather its `active_joints`. These are only the joints connecting it to **other elements still in `remaining_elements`**. Joints connected to already-removed elements are ignored (since there is no physical blockage).
    - If the solver can resolve the constraints and return a valid extraction vector, the element is free to move.
3. **Record and Remove:** Remove the free element from `remaining_elements`. Add it to the disassembly sequence along with its insertion vector (which is simply the extraction vector inverted).
4. **Repeat:** Restart the search for a free element until `remaining_elements` is empty.
    - **Deadlock:** If the list is not empty but no elements can be extracted, the structure contains interlocking geometry or requires multi-element simultaneous insertion (which is beyond the scope of this single-element sequential solver).
5. **Reverse:** The final assembly sequence is simply the reverse of the disassembly sequence.
