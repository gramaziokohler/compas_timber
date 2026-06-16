from __future__ import annotations

import warnings
from typing import Iterable
from typing import List
from typing import cast

from compas.geometry import Point
from compas.tolerance import TOL
from compas_model.elements import Element
from compas_model.models import Model

from compas_timber.connections import ConnectionSolver
from compas_timber.connections import Joint
from compas_timber.connections import JointCandidate
from compas_timber.connections import JointTopology
from compas_timber.connections import PanelJoint
from compas_timber.connections import PlateConnectionSolver
from compas_timber.connections import PlateJoint
from compas_timber.connections import PlateJointCandidate
from compas_timber.elements import Beam
from compas_timber.elements import Fastener
from compas_timber.elements import Panel
from compas_timber.elements import Plate
from compas_timber.elements import Layer
from compas_timber.errors import BeamJoiningError
from compas_timber.structural import BeamStructuralElementSolver
from compas_timber.structural import StructuralSegment


class TimberModel(Model):
    """Represents a timber model containing different elements such as panels, beams and joints.

    The timber model allows expressing the hierarchy and interactions between the different elements it contains.

    Attributes
    ----------
    beams : Generator[:class:`~compas_timber.elements.Beam`]
        A Generator object of all beams assigned to this model.
    plates : Generator[:class:`~compas_timber.elements.Plate`]
        A Generator object of all plates assigned to this model.
    joints : set[:class:`~compas_timber.connections.Joint`]
        A set of all actual joints assigned to this model.
    joint_candidates : set[:class:`~compas_timber.connections.JointCandidate`]
        A set of all joint candidates in the model.
    panels : Generator[:class:`~compas_timber.elements.Panel`]
        A Generator object of all panels assigned to this model.
    center_of_mass : :class:`~compas.geometry.Point`
        The calculated center of mass of the model.
    topologies :  list(dict)
        A list of JointTopology for model. dict is: {"detected_topo": detected_topo, "beam_a_key": beam_a_key, "beam_b_key":beam_b_key}
        See :class:`~compas_timber.connections.JointTopology`.
    tolerance : :class:`~compas.tolerance.Tolerance`
        The tolerance configuration used for this model. TOL if none provided.
    volume : float
        The calculated total volume of the model.

    """

    _TIMBER_GRAPH_EDGE_ATTRIBUTES = {"joints": None, "candidates": None, "structural_segments": None}
    _TIMBER_GRAPH_NODE_ATTRIBUTES = {"structural_segments": None}

    @property
    def __data__(self):
        data = super().__data__
        data["joints"] = self._joints
        return data

    @classmethod
    def __from_data__(cls, data):
        model = super().__from_data__(data)
        joints_data = data["joints"]
        for guid_str, joint in joints_data.items():
            model._joints[guid_str] = joint

        for joint in model._joints.values():
            joint.restore_elements_from_keys(model)

        return model

    def __init__(self, tolerance=None, **kwargs):
        super(TimberModel, self).__init__()
        self._joints = {}
        self._topologies = []  # added to avoid calculating multiple times
        self._tolerance = tolerance or TOL
        self._graph.update_default_edge_attributes(**self._TIMBER_GRAPH_EDGE_ATTRIBUTES)
        self._graph.update_default_node_attributes(**self._TIMBER_GRAPH_NODE_ATTRIBUTES)

    def __str__(self):
        # type: () -> str
        return "TimberModel ({}) with {} elements(s) and {} joint(s).".format(str(self.guid), len(list(self.elements())), len(list(self.joints)))

    # =============================================================================
    # Attributes
    # =============================================================================

    @property
    def tolerance(self):
        # type: () -> Tolerance
        return self._tolerance

    @property
    def beams(self):
        # type: () -> List[Beam]
        return self.find_all_elements_of_type(Beam)

    @property
    def plates(self):
        # type: () -> List[Plate]
        return self.find_all_elements_of_type(Plate)

    @property
    def panels(self):
        # type: () -> List[Panel]
        # ``Layer`` is a ``Panel`` subclass; exclude layers here so panel-level
        # operations (connection, top-level joinery) act on real panels only.
        return self.find_all_elements_of_type(Panel)

    @property
    def layers(self):
        # type: () -> List[Panel]
        """All :class:`~compas_timber.panel_features.Layer` elements in the model."""
        return self.find_all_elements_of_type(Layer)

    @property
    def fasteners(self):
        # type: () -> List[Fastener]
        return self.find_all_elements_of_type(Fastener)

    @property
    def joints(self) -> Iterable[Joint]:
        return self._joints.values()

    @property
    def joint_candidates(self):
        # type: () -> set[JointCandidate]
        candidates = set()
        for edge in self._graph.edges():
            edge_candidate = self._graph.edge_attribute(edge, "candidates")
            if edge_candidate is not None:
                candidates.add(edge_candidate)
        return candidates

    @property
    def unpromoted_joint_candidates(self) -> set[JointCandidate]:
        candidates = set()
        for edge in self._graph.edges():
            edge_candidate = self._graph.edge_attribute(edge, "candidates")
            joint = self._graph.edge_attribute(edge, "joints")
            if edge_candidate and not joint:
                candidates.add(edge_candidate)
        return candidates

    @property
    def topologies(self):
        return self._topologies

    @property
    def center_of_mass(self):
        # type: () -> Point
        total_vol = 0
        total_position = Point(0, 0, 0)

        for element in self.elements():
            vol = element.obb.volume  # TODO: include material density...? this uses volume as proxy for mass, which assumes all parts have equal density
            point = element.obb.frame.point
            total_vol += vol
            total_position += point * vol

        return Point(*total_position) * (1.0 / total_vol)

    @property
    def volume(self):
        # type: () -> float
        return sum([element.obb.volume for element in self.elements()])

    # =============================================================================
    # Elements
    # =============================================================================

    def get_element(self, guid):
        # type: (str) -> Element | None
        """Get an element by its unique identifier.

        Parameters
        ----------
        guid : str
            The GUID of the element to retrieve.

        Returns
        -------
        :class:`~compas_model.elements.Element` or None
            The element with the specified GUID.
            None if an element with this GUID is not in the Model.

        """
        return self._elements.get(guid)

    def __getitem__(self, guid):
        # type: (str) -> Element
        """Get an element by its unique identifier.

        Parameters
        ----------
        guid : str
            The GUID of the element to retrieve.

        Returns
        -------
        :class:`~compas_model.elements.Element`
            The element with the specified GUID.

        """
        return self._elements[guid]

    def element_by_guid(self, guid):
        # type: (str) -> Element
        """DEPRECATED
        Get an element by its unique identifier.

        Parameters
        ----------
        guid : str
            The GUID of the element to retrieve.

        Returns
        -------
        :class:`~compas_model.elements.Element`
            The element with the specified GUID.

        """
        warnings.warn("element_by_guid() is deprecated;use get_element() for optional access or TimberModel[guid] for strict access.", DeprecationWarning, stacklevel=2)
        return self[guid]

    # =============================================================================
    # Groups
    # =============================================================================

    def has_group(self, group_element):
        # type: (TimberElement) -> bool
        """Check if a group with `group_element` exists in the model.

        Parameters
        ----------
        group_element : class:`~compas_timber.elements.TimberElement`
            The group element to check for existence.

        Returns
        -------
        bool
            True if the group element exists in the model.
        """
        return self.has_element(group_element)

    def get_elements_in_group(self, group_element, filter_=None):
        """Get all elements in a group element.

        TODO: upstream this to compas_model

        Parameters
        ----------
        group_element : :class:`~compas_timber.elements.TimberElement`
            The group element to query.
        filter_ : callable, optional
            A filter function to apply to the elements.

        Returns
        -------
        Generator[:class:`~compas_timber.elements.TimberElement`]
            A generator of elements in the group.

        """
        # type: (TimberElement, callable | None) -> Generator[TimberElement, None, None]
        if not self.has_group(group_element):
            raise ValueError("Group {} not found in model.".format(group_element.name))

        filter_ = filter_ or (lambda _: True)
        elements = group_element.children
        return filter(filter_, elements)

    # =============================================================================
    # Interactions
    # =============================================================================

    def _safely_get_edge_attribute(self, node_pair, attribute):
        results = []
        node_a, node_b = node_pair
        try:
            attr_value = self._graph.edge_attribute((node_a, node_b), attribute)
            if attr_value:
                results.append(attr_value)
        except KeyError:
            pass
        try:
            attr_value = self._graph.edge_attribute((node_b, node_a), attribute)
            if attr_value:
                results.append(attr_value)
        except KeyError:
            pass
        return results

    def get_joints_for_element(self, element) -> List[Joint]:
        """Get all joints for a given element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element to query.

        Returns
        -------
        list[:class:`~compas_timber.connections.Joint`]
            A list of joints for the given element.
        """
        neighbors = self._graph.neighbors(element.graphnode)
        result = []
        for nbr in neighbors:
            joint_guids = self._safely_get_edge_attribute((element.graphnode, nbr), "joints")
            result.extend([self._joints[guid] for guid in joint_guids if guid in self._joints])
        return result

    def get_candidates_for_element(self, element) -> List[JointCandidate]:
        """Get all joint candidates for a given element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element to query.

        Returns
        -------
        list[:class:`~compas_timber.connections.JointCandidate`]
            A list of joint candidates for the given element.
        """
        neighbors = self._graph.neighbors(element.graphnode)
        result = []
        for nbr in neighbors:
            candidates = self._safely_get_edge_attribute((element.graphnode, nbr), "candidates")
            result.extend(candidates)
        return result

    def get_interactions_for_element(self, element):
        # type: (Element) -> List[Interaction]
        """Get all interactions (joints and candidates) for a given element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element to query.

        Returns
        -------
        list[:class:`~compas_model.interactions.Interaction`]
            A list of interactions for the given element.
        """
        result = self.get_joints_for_element(element)
        result.extend(self.get_candidates_for_element(element))
        return result

    def add_joint(self, joint):
        # type: (Joint) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint`
            An instance of a Joint class.
        """
        joint_guid = str(joint.guid)
        self._joints[joint_guid] = joint
        self.add_elements(joint.generated_elements)
        for interaction in joint.interactions:
            element_a, element_b = interaction
            edge = self.add_interaction(element_a, element_b)
            self._graph.edge_attribute(edge, "joints", value=joint_guid)

    def add_joint_candidate(self, candidate):
        # type: (JointCandidate) -> None
        """Add a joint candidate to the model.

        Joint candidates are stored on the graph edges under the "candidate" attribute,
        separate from actual joints which are stored under the "interaction" attribute.

        Parameters
        ----------
        candidate : :class:`~compas_timber.connections.JointCandidate`
            An instance of a JointCandidate class.
        """
        for interaction in candidate.interactions:
            element_a, element_b = interaction
            edge = (element_a.graphnode, element_b.graphnode)
            if edge not in self._graph.edges():
                self._graph.add_edge(*edge)

            # this is how joints and candidates co-exist on the same edge, they are stored under different attributes
            # (``joints`` vs. ``candidates``)
            self._graph.edge_attribute(edge, "candidates", candidate)

    def add_structural_connector_segments(self, element_a: Element, element_b: Element, segments: List[StructuralSegment]) -> None:
        """Adds structural segments to the interaction (edge) between two elements.

        Notes
        -----
        Normally, this method shouldn't be called directy. Use :meth:`create_beam_structural_segments` when possible to add structural segments.

        Parameters
        ----------
        element_a : :class:`~compas_timber.elements.TimberElement`
            The first element.
        element_b : :class:`~compas_timber.elements.TimberElement`
            The second element.
        segments : list[:class:`~compas_timber.structural.StructuralSegment`]
            The structural segments to add.
        """
        edge = (element_a.graphnode, element_b.graphnode)
        if edge not in self._graph.edges():
            edge = (element_b.graphnode, element_a.graphnode)
            if edge not in self._graph.edges():
                raise ValueError("Interaction between elements {} and {} does not exist in the model.".format(element_a.name, element_b.name))

        existing_segments = self._graph.edge_attribute(edge, "structural_segments") or []
        existing_segments.extend(segments)
        self._graph.edge_attribute(edge, "structural_segments", existing_segments)

    def get_structural_connector_segments(self, element_a: Element, element_b: Element) -> List[StructuralSegment]:
        """Gets the structural segments assigned to the interaction between two elements.

        Parameters
        ----------
        element_a : :class:`~compas_timber.elements.TimberElement`
            The first element.
        element_b : :class:`~compas_timber.elements.TimberElement`
            The second element.

        Returns
        -------
        list[:class:`~compas_timber.structural.StructuralSegment`]
            The structural segments assigned to the interaction.
        """
        edge = (element_a.graphnode, element_b.graphnode)
        if edge not in self._graph.edges():
            edge = (element_b.graphnode, element_a.graphnode)
            if edge not in self._graph.edges():
                return []

        return self._graph.edge_attribute(edge, "structural_segments") or []

    def remove_structural_connector_segments(self, element_a: Element, element_b: Element) -> None:
        """Removes all structural segments assigned to the interaction between two elements.

        Parameters
        ----------
        element_a : :class:`~compas_timber.elements.TimberElement`
            The first element.
        element_b : :class:`~compas_timber.elements.TimberElement`
            The second element.
        """
        edge = (element_a.graphnode, element_b.graphnode)
        if edge in self._graph.edges():
            self._graph.unset_edge_attribute(edge, "structural_segments")

    def add_beam_structural_segments(self, beam: Beam, segments: List[StructuralSegment]) -> None:
        """Adds a structural segment to the model node corresponding to the given beam.

        Notes
        -----
        Normally, this method shouldn't be called directy. Use :meth:`create_beam_structural_segments` when possible to add structural segments.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam to which the structural segments belong.
        segments : list[:class:`~compas_timber.structural.StructuralSegment`]
            The structural segments to add.
        """
        node = beam.graphnode
        existing_segments = cast(List[StructuralSegment], self._graph.node_attribute(node, "structural_segments")) or []
        existing_segments.extend(segments)
        self._graph.node_attribute(node, "structural_segments", existing_segments)

    def get_beam_structural_segments(self, beam: Beam) -> List[StructuralSegment]:
        """Gets the structural segments assigned to the given beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam whose structural segments to retrieve.

        Returns
        -------
        list[:class:`~compas_timber.structural.StructuralSegment`]
            The structural segments assigned to the beam.
        """
        segments = cast(List[StructuralSegment], self._graph.node_attribute(beam.graphnode, "structural_segments"))
        return segments or []

    def remove_beam_structural_segments(self, beam: Beam) -> None:
        """Removes all structural segments assigned to the given beam.

        Parameters
        ----------
        beam : :class:`~compas_timber.elements.Beam`
            The beam whose structural segments to remove.
        """
        self._graph.unset_node_attribute(beam.graphnode, "structural_segments")

    def remove_joint_candidate(self, candidate):
        # type: (JointCandidate) -> None
        """Removes this joint candidate from the model.

        Parameters
        ----------
        candidate : :class:`~compas_timber.connections.JointCandidate`
            The joint candidate to remove.
        """
        for interaction in candidate.interactions:
            element_a, element_b = interaction
            edge = (element_a.graphnode, element_b.graphnode)

            if edge in self._graph.edges():
                stored_candidate = self._graph.edge_attribute(edge, "candidates")
                if stored_candidate is candidate:
                    self._graph.unset_edge_attribute(edge, "candidates")

            if not self._is_remaining_attrs_on_edge(edge):
                # if there's no other timber related attributes on that edge, then remove the edge as well
                super().remove_interaction(element_a, element_b)

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
        self._joints.pop(str(joint.guid), None)
        for interaction in joint.interactions:
            element_a, element_b = interaction
            self.remove_interaction(element_a, element_b)
        for element in joint.generated_elements:
            self.remove_element(element)

    def remove_interaction(self, a, b, _=None):
        """Remove the interaction between two elements.

        Extends :meth:`Model.remove_interaction` to not remove the edge if there are still other timber related attribute on the same edge.

        Parameters
        ----------
        a : :class:`TimberElement`
        b : :class:`TimberElement`

        Returns
        -------
        None

        """
        edge = (a.graphnode, b.graphnode)
        if edge not in self._graph.edges():
            return

        self._graph.unset_edge_attribute(edge, "joints")

        if not self._is_remaining_attrs_on_edge(edge):
            # if there's no other timber related attributes on that edge, then remove the edge as well
            super().remove_interaction(a, b)

    def _is_remaining_attrs_on_edge(self, edge):
        # returns True if any TimeberModel attributes are left on edge
        for attr in self._TIMBER_GRAPH_EDGE_ATTRIBUTES:
            if self._graph.edge_attribute(edge, attr):
                return True
        return False

    # =============================================================================
    # Other Methods
    # =============================================================================

    def transform(self, transformation):
        """Transform the model and reset all computed properties of all elements."""
        # Override the base method to also reset computed properties of elements
        super().transform(transformation)
        for element in self.elements():
            element.reset_computed_properties()  # TODO: Find a better way to only update transformations of elements instead of resetting all computed properties.  # noqa: E501

    def set_topologies(self, topologies):
        """TODO: calculate the topologies inside the model using the ConnectionSolver."""
        self._topologies = topologies

    def process_panel_joinery(self, stop_on_first_error=False):
        """Process the joinery of panels in the model. This methods checks the feasibility of the joints and instructs all joints to add their extensions and features.

        The sequence is important here since the feature parameters must be calculated based on the extended blanks.
        For this reason, the first iteration will only extend the beams, and the second iteration will add the features.

        Parameters
        ----------
        stop_on_first_error : bool, optional
            If True, the method will raise an exception on the first error it encounters. Default is False.

        Returns
        -------
        list[:class:`~compas_timber.errors.BeamJoiningError`]
            A list of errors that occurred during the joinery process.

        """
        errors = []
        joints = self.joints
        for joint in joints:
            if not any([isinstance(e, Panel) for e in joint.elements]):
                continue
            try:
                joint.add_extensions()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje

        # Only iterate top-level panels: ``Panel.apply_edge_extensions`` already
        # cascades to its layers, and ``Layer.apply_edge_extensions`` recurses to
        # sublayers — so a panel applies its whole layer tree exactly once.
        # Adding ``self.layers`` here would re-apply each layer (and re-apply each
        # sublayer once per ancestor), and edge extensions are not idempotent
        # across shared corner vertices, producing wrong outlines.
        for panel in self.panels:
            panel.apply_edge_extensions()

        for joint in joints:
            if not any([isinstance(e, Panel) for e in joint.elements]):
                continue
            try:
                joint.add_features()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
            # TODO: should we be handling the BTLxProcessing application errors differently?
            # TODO: Maybe a ProcessingApplicationError raised for the processing(s) that failed when adding the features to the elements?
            # TODO: This would allow us to catch the processing that failed with the necessary info, while applying the rest of the required by the joint processings that were sucessfull.  # noqa: E501
            except ValueError as ve:
                bje = BeamJoiningError(joint.elements, joint, debug_info=str(ve))
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
        return errors





    def process_joinery(self, stop_on_first_error=False, include_panels=True):
        """Process the joinery of the model. This methods checks the feasibility of the joints and instructs all joints to add their extensions and features.

        The sequence is important here since the feature parameters must be calculated based on the extended blanks.
        For this reason, the first iteration will only extend the beams, and the second iteration will add the features.

        Parameters
        ----------
        stop_on_first_error : bool, optional
            If True, the method will raise an exception on the first error it encounters. Default is False.
        include_panels : bool, optional
            If True (default), all joints are processed.  If False, joints that
            involve a :class:`~compas_timber.elements.Panel` are skipped — use
            this when panel joinery has already been processed separately via
            :meth:`process_panel_joinery` so it is not applied twice (panel-joint
            extensions are not idempotent).

        Returns
        -------
        list[:class:`~compas_timber.errors.BeamJoiningError`]
            A list of errors that occurred during the joinery process.

        """
        errors = []
        joints = self.joints
        if not include_panels:
            joints = [joint for joint in joints if not any(isinstance(e, Panel) for e in joint.elements)]

        for joint in joints:
            try:
                joint.add_extensions()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje

        for joint in joints:
            try:
                joint.add_features()
            except BeamJoiningError as bje:
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
            # TODO: should we be handling the BTLxProcessing application errors differently?
            # TODO: Maybe a ProcessingApplicationError raised for the processing(s) that failed when adding the features to the elements?
            # TODO: This would allow us to catch the processing that failed with the necessary info, while applying the rest of the required by the joint processings that were sucessfull.  # noqa: E501
            except ValueError as ve:
                bje = BeamJoiningError(joint.elements, joint, debug_info=str(ve))
                errors.append(bje)
                if stop_on_first_error:
                    raise bje
        return errors

    def create_beam_structural_segments(self, solver=None) -> None:
        """Creates structural segments for all beams in the model based on their joints.

        Parameters
        ----------
        solver : :class:`~compas_timber.structural.BeamStructuralElementSolver`, optional
            The solver to use for creating structural segments.
            If not provided, a default solver is created.

        """
        if not self.beams:
            raise ValueError("No beams in the model to create structural segments for.")

        for beam in self.beams:
            self.remove_beam_structural_segments(beam)

        for edge in self._graph.edges():
            self._graph.unset_edge_attribute(edge, "structural_segments")

        solver = solver or BeamStructuralElementSolver()
        _, joints_traversed = solver.add_structural_segments(model=self)
        solver.add_joint_structural_segments(model=self, joints=joints_traversed)

    def connect_adjacent_beams(self, max_distance=None):
        # Clear existing joint candidates
        for candidate in list(self.joint_candidates):
            self.remove_joint_candidate(candidate)

        max_distance = max_distance or TOL.relative
        beams = self.beams
        solver = ConnectionSolver()
        pairs = solver.find_intersecting_pairs(beams, rtree=True, max_distance=max_distance)
        for pair in pairs:
            beam_a, beam_b = pair
            result = solver.find_topology(beam_a, beam_b, max_distance=max_distance)
            if result.topology == JointTopology.TOPO_UNKNOWN:
                continue
            assert beam_a and beam_b

            # Create candidate and add it to the model
            candidate = JointCandidate(
                result.beam_a, result.beam_b, topology=result.topology, distance=result.distance, location=result.location
            )  # use the beam order determined by find_topology to keep main, cross relationship
            self.add_joint_candidate(candidate)

    def connect_adjacent_plates(self, max_distance=None):
        """Connects adjacent plates in the model.

        Parameters
        ----------
        max_distance : float, optional
            The maximum distance between plates to consider them adjacent. Default is 0.0.
        """
        to_remove = [joint for joint in self.joints if isinstance(joint, PlateJoint)]
        for joint in to_remove:
            self.remove_joint(joint)# TODO do we want to remove plate joints?

        max_distance = max_distance or TOL.absolute
        plates = self.plates
        solver = PlateConnectionSolver()
        pairs = solver.find_intersecting_pairs(plates, rtree=True, max_distance=max_distance)
        for pair in pairs:
            plate_a, plate_b = pair
            result = solver.find_topology(plate_a, plate_b, tol=TOL.relative, max_distance=max_distance)

            if result.topology is JointTopology.TOPO_UNKNOWN:
                continue
            kwargs = {"topology": result.topology, "a_segment_index": result.a_segment_index, "distance": result.distance, "location": result.location}

            if result.topology == JointTopology.TOPO_EDGE_EDGE:
                kwargs["b_segment_index"] = result.b_segment_index

            candidate = PlateJointCandidate(result.plate_a, result.plate_b, **kwargs)
            self.add_joint_candidate(candidate)

    def connect_adjacent_panels(self, max_distance=None):
        """Connects adjacent plates in the model.

        Parameters
        ----------
        max_distance : float, optional
            The maximum distance between plates to consider them adjacent. Default is 0.0.
        """
        to_remove = [joint for joint in self.joints if isinstance(joint, PanelJoint)]
        for joint in to_remove:
            self.remove_joint(joint)# TODO do we want to remove plate joints?

        max_distance = max_distance or TOL.absolute
        panels = self.panels
        solver = PlateConnectionSolver()
        pairs = solver.find_intersecting_pairs(panels, rtree=True, max_distance=max_distance)
        for pair in pairs:
            panel_a, panel_b = pair
            result = solver.find_topology(panel_a, panel_b, tol=TOL.relative, max_distance=max_distance)

            if result.topology is JointTopology.TOPO_UNKNOWN:
                continue
            kwargs = {"topology": result.topology, "a_segment_index": result.a_segment_index, "distance": result.distance, "location": result.location}

            if result.topology == JointTopology.TOPO_EDGE_EDGE:
                kwargs["b_segment_index"] = result.b_segment_index

            candidate = PlateJointCandidate(result.plate_a, result.plate_b, **kwargs)
            self.add_joint_candidate(candidate)

    # =============================================================================
    # Model sub-tree surgery
    # =============================================================================

    def remove_element_subtree(self, element):
        """Remove all children (and their descendants) of *element* from the model.

        *element* itself is kept in the model as a childless leaf.  Any joints
        whose both elements are among the removed descendants are also removed;
        joints that span a removed element and an element outside the subtree are
        removed as well.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element whose descendants are removed.  Must already be in the model.
        """
        _, _ = self._detach_subtree(element)

    def _detach_subtree(self, parent=None):
        # type: (Element | None) -> tuple[list, list]
        """Remove elements from the model and return the information needed to re-attach them.

        Parameters
        ----------
        parent : :class:`~compas_model.elements.Element`, optional
            When given, *parent* is **kept** in the model and only its descendants
            are removed.  The direct children are recorded under ``None`` in the
            returned tuples so they can be re-rooted under a different parent on
            re-insertion.
            When ``None``, every element in the model is removed.

        Returns
        -------
        tuple(list, list)
            * ``tuples`` — list of ``(parent_element_or_None, [children])`` pairs,
              ordered parents-before-children so ``_attach_subtree`` can re-insert
              them in a single pass while preserving hierarchy.
            * ``joints`` — list of joints that were removed because all their
              elements were part of the detached subtree.  Joints that spanned a
              removed element and a kept element are dropped entirely.
        """
        tuples = []
        elements_children_first = []

        def walk(element, is_kept_root):
            children = list(element.children)
            if children:
                tuples.append((None if is_kept_root else element, children))
                for child in children:
                    walk(child, is_kept_root=False)
            if not is_kept_root:
                elements_children_first.append(element)

        if parent:
            walk(parent, is_kept_root=True)
        else:
            tops = [element for element in self.elements() if element.parent is None]
            tuples.append((None, tops))
            for top in tops:
                walk(top, is_kept_root=False)

        joints = []
        for j in list(self.joints):
            elements_in_joint = [e in elements_children_first for e in j.elements]
            if all(elements_in_joint):
                joints.append(j)
                self.remove_joint(j)
            elif any(elements_in_joint):
                self.remove_joint(j)

        for e in elements_children_first:
            self.remove_element(e)
            e.clear_model_dependent_cache()

        return tuples, joints

    def _attach_subtree(self, tuples, joints=None, parent=None):
        # type: (list, list | None, Element | None) -> None
        """Re-add elements described by *tuples* into this model.

        Parameters
        ----------
        tuples : list
            ``(tuple_parent, [children])`` pairs as returned by :meth:`_detach_subtree`.
            Pairs whose ``tuple_parent`` is ``None`` are rooted under *parent*
            (or at the model root when *parent* is also ``None``).
        joints : list, optional
            Joints to restore after all elements have been re-added.
        parent : :class:`~compas_model.elements.Element`, optional
            Default parent for top-level elements (those recorded under ``None``).
            When ``None``, they are added as model-root elements.
        """
        for tuple_parent, children in tuples:
            target_parent = tuple_parent if tuple_parent is not None else parent
            for child in children:
                self.add_element(child, parent=target_parent)
                child.clear_model_dependent_cache()
        if joints:
            for joint in joints:
                self.add_joint(joint)

    def extract_model_from_parent(self, parent):
        # type: (Element) -> TimberModel
        """Detach *parent*'s child subtree into a new, standalone :class:`TimberModel`.

        The *parent* element itself stays in its current model; its descendants are
        removed from that model and re-rooted (hierarchy preserved) in a fresh
        :class:`TimberModel`, which is returned.

        A child element detached from its parent reports its geometry in the
        parent's local frame — convenient for operating on, e.g., a panel's layers
        in isolation, then merging them back with :func:`merge_model_into_model`.

        Parameters
        ----------
        parent : :class:`~compas_model.elements.Element`
            The element whose children are extracted.  Must be in a model.

        Returns
        -------
        :class:`TimberModel`
            A new model containing *parent*'s former subtree.
        """
        tuples, joints = self._detach_subtree(parent)
        new_model = TimberModel()
        new_model._attach_subtree(tuples, joints=joints)
        return new_model

    def merge_model(self, model, parent=None):
        # type: (TimberModel, TimberModel, Element | None) -> None
        """Move every element (and joints) of *model* into *target_model* under *parent*.

        All of *model*'s top-level elements and their subtrees are detached and
        re-added beneath *parent* in *target_model* (or under the root when *parent*
        is ``None``), preserving the hierarchy and resetting each moved element's
        computed properties.  Joints defined on *model* are copied across.

        Parameters
        ----------
        model : :class:`TimberModel`
            The source model whose contents are moved out.
        target_model : :class:`TimberModel`
            The model to merge *model*'s elements into.
        parent : :class:`~compas_model.elements.Element`, optional
            The element under which the moved elements are re-rooted.  ``None``
            attaches them under the target model's root.
        """
        tuples, joints = model._detach_subtree()
        self._attach_subtree(tuples, joints=joints, parent=parent)
