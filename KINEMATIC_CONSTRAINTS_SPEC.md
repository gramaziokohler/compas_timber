# Feature Specification: Assembly Sequencing via Kinematic Escape Constraints

## Overview
This document outlines the architecture for automatically calculating robotic assembly sequences and insertion vectors in `compas_timber`. 

Because forward-planning an assembly sequence can lead to kinematic dead-ends, this architecture uses **Disassembly Planning**. By defining the mathematical "escape constraints" of individual joints, a solver can work backwards from the completed `TimberModel` to deduce a collision-free, kinematically sound assembly sequence.

---

## 1. The Geometric Constraints (Degrees of Freedom)
When querying a joint for its freedom, it will return one of the following `compas.geometry` objects representing the mathematical space the `moving_element` can travel assuming the other element is frozen:

* **`compas.geometry.Line` (1 DOF):** Strict linear sliding (e.g., Mortise & Tenon, Dovetail).
* **`compas.geometry.Plane` (2 DOF):** Planar sliding (e.g., Lap Joint).
* **`compas.geometry.Vector` (3 DOF):** A Half-Space defined by a normal. The beam can move anywhere as long as the dot product with this vector is positive (e.g., Simple Butt Joint).

---

## 2. Base Joint Interface
**Target File:** `src/compas_timber/connections/joint.py`

We must define the contract for all joints and provide a generic 3-DOF fallback. Add the following imports and method to the base `Joint` class.

### Code to Add:
```python
# Add to imports in joint.py
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Vector

# Add to the Joint class (around line 230)
    def get_kinematic_constraint(self, moving_element):
        """Returns the geometric freedom to pull `moving_element` out of this joint.
        
        This assumes the other element in the joint is completely static/fixed.
        
        Parameters
        ----------
        moving_element : :class:`~compas_timber.elements.Beam`
            The element being extracted from the joint.
            
        Returns
        -------
        compas.geometry.Line | compas.geometry.Plane | compas.geometry.Vector
            The kinematic escape constraint.
        """
        if moving_element not in self.elements:
            raise ValueError(f"Element {moving_element} is not part of {self.name}.")
            
        # Generic Fallback: 3-DOF Half-Space separating the two elements
        static_element = self.element_a if moving_element == self.element_b else self.element_b
        
        v = Vector.from_start_end(static_element.centerline.midpoint, moving_element.centerline.midpoint)
        v.unitize()
        return v
```

## 3. Specific Joint Implementations (Polymorphism)
Subclasses must override the base method to provide exact, parameter-driven kinematics.

### 3.1 L-Butt Joint
**Target File:** `src/compas_timber/connections/l_butt.py`

An L-Butt joint allows sliding anywhere along the cut plane, or pulling directly away from it.

### Code to Add:
```python
# Add to the LButtJoint class
    def get_kinematic_constraint(self, moving_element):
        """Calculates the escape constraint for the L-Butt joint.
        
        Returns a Plane representing the 2-DOF sliding freedom along the cut face.
        """
        if moving_element not in self.elements:
            raise ValueError("Element is not part of this joint.")

        if moving_element == self.cross_beam:
            # The cross beam slides against the butt_plane of the main beam.
            # Normal should point AWAY from the main beam.
            return self.butt_plane 
            
        elif moving_element == self.main_beam:
            # The main beam slides against the cut face of the cross beam.
            # We invert the plane normal so it points AWAY from the cross beam.
            plane = self.butt_plane.copy()
            plane.normal = plane.normal * -1
            return plane
```

### 3.2 T-Dovetail Joint (Example Template)
**Target File:** `src/compas_timber/connections/t_dovetail.py` (or equivalent dovetail implementation)

A Dovetail joint physically locks the beam in all directions except exactly along the dovetail groove axis.

### Code to Add:
```python
# Example logic to add to a Dovetail Joint class
    def get_kinematic_constraint(self, moving_element):
        """Calculates the 1-DOF strict linear escape constraint for a dovetail."""
        if moving_element not in self.elements:
            raise ValueError("Element is not part of this joint.")
            
        # Assuming `calculate_groove_axis()` returns the Vector of the groove
        groove_axis = self.calculate_groove_axis() 
        
        if moving_element == self.cross_beam:
            return Line(self.location, self.location + groove_axis)
            
        elif moving_element == self.main_beam:
            return Line(self.location, self.location + (groove_axis * -1))
```

## 4. The Sequencer / Constraint Solver
**Target File:** `src/compas_timber/planning/insertion_solver.py` (New File)

This solver takes a TimberModel and iteratively works backwards, computing the mathematical intersection of the geometries returned by get_kinematic_constraint.

### Code to Add:
```python
from compas.geometry import cross_vectors, Vector, Plane, Line

class InsertionSolver:
    def __init__(self, model):
        self.model = model
        
    def resolve_constraints(self, constraints):
        """Calculates the mathematical intersection of multiple kinematic constraints.
        
        Parameters
        ----------
        constraints : list of (Line | Plane | Vector)
        
        Returns
        -------
        compas.geometry.Vector | None
            The single valid escape vector, or None if kinematically locked.
        """
        lines = [c for c in constraints if isinstance(c, Line)]
        planes = [c for c in constraints if isinstance(c, Plane)]
        vectors = [c for c in constraints if isinstance(c, Vector)]
        
        candidate_vector = None
        
        # 1. Strict 1-DOF lock
        if len(lines) > 0:
            # If multiple lines exist, they MUST be parallel, otherwise it's locked
            candidate_vector = lines[0].direction
            
        # 2. Planar 2-DOF Intersection
        elif len(planes) >= 2:
            # Intersection of two planes is a line (Cross product of normals)
            v = cross_vectors(planes[0].normal, planes[1].normal)
            if v.length == 0:  # Planes are parallel
                candidate_vector = planes[0].normal
            else:
                candidate_vector = Vector(*v).unitized()
                
        elif len(planes) == 1:
            candidate_vector = planes[0].normal
            
        elif len(vectors) > 0:
            candidate_vector = vectors[0] # Simplification: average or merge half-spaces
            
        # Validate candidate against all half-spaces (Vectors) to ensure no collisions
        if candidate_vector:
            for v in vectors:
                if candidate_vector.dot(v) < 0:
                    # Trying to push through solid wood
                    return None 
                    
        return candidate_vector

    def get_extraction_vector(self, element, active_joints):
        """Gets the final extraction vector for a given element."""
        constraints = [joint.get_kinematic_constraint(element) for joint in active_joints]
        return self.resolve_constraints(constraints)
```
