from __future__ import annotations

import warnings
from typing import List
from typing import cast

from compas.geometry import Point
from compas.tolerance import TOL
from compas_model.elements import Element
from compas_model.models import Model

from compas_timber.connections import ConnectionSolver
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

    @classmethod
    def __from_data__(cls, data):
        model = super(TimberModel, cls).__from_data__(data)
        for joint in model.joints:  # TODO: allow for modifiers as well once they are implemented in compas_timber
            joint.restore_beams_from_keys(model)  # type: ignore
        return model

    def __init__(self, tolerance=None, **kwargs):
        super(TimberModel, self).__init__()
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
        return self.find_all_elements_of_type(Panel)

    @property
    def fasteners(self):
        # type: () -> List[Fastener]
        return self.find_all_elements_of_type(Fastener)

    @property
    def joints(self):
        # type: () -> set[Joint]
        joints = set()  # some joints might apear on more than one interaction
        for edge in self._graph.edges():
            edge_joints = self._graph.edge_attribute(edge, "joints") or []
            for joint in edge_joints:
                joints.add(joint)
        return joints

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

    def _safely_get_interactions(self, node_pair):
        # type: (tuple) -> List[Interaction]
        interactions = []
        try:
            interactions.extend(self._graph.edge_attribute(node_pair, "joints"))
        except KeyError:
            pass
        try:
            interactions.append(self._graph.edge_attribute(node_pair, "candidates"))
        except KeyError:
            pass

    def get_interactions_for_element(self, element):
        # type: (Element) -> List[Interaction]
        """Get all interactions for a given element.

        Parameters
        ----------
        element : :class:`~compas_model.elements.Element`
            The element to query.

        Returns
        -------
        list[:class:`~compas_model.interactions.Interaction`]
            A list of interactions for the given element.
        """

        neighbors = self._graph.neighbors(element.graphnode)
        result = []
        for nbr in neighbors:
            result.extend(self._safely_get_interactions((element.graphnode, nbr)))
            result.extend(self._safely_get_interactions((nbr, element.graphnode)))
        return result

    def add_joint(self, joint):
        # type: (Joint) -> None
        """Add a joint object to the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.joint`
            An instance of a Joint class.
        """
        # TODO: should we be removing the joint candidate(s) edge attributes when adding an actual joint?
        self.add_elements(joint.generated_elements)
        for interaction in joint.interactions:
            element_a, element_b = interaction
            edge = self.add_interaction(element_a, element_b)
            joints = self._graph.edge_attribute(edge, "joints") or []  # GET
            joints.append(joint)
            self._graph.edge_attribute(edge, "joints", value=joints)  # SET
            # TODO: should we create a bidirectional interaction here?

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

                # HACK: calls to `model.joints` expect there to be a "joints" on any edges
                self._graph.edge_attribute(edge, "joints", [])

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
                super(TimberModel, self).remove_interaction(element_a, element_b)

    def remove_joint(self, joint):
        # type: (Joint) -> None
        """Removes this joint object from the model.

        Parameters
        ----------
        joint : :class:`~compas_timber.connections.Joint`
            The joint to remove.

        """
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

        edge_interactions = self._graph.edge_attribute(edge, "joints")
        edge_interactions.clear()  # type: ignore

        if not self._is_remaining_attrs_on_edge(edge):
            # if there's no other timber related attributes on that edge, then remove the edge as well
            super(TimberModel, self).remove_interaction(a, b)

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

    def process_joinery(self, stop_on_first_error=False):
        """Process the joinery of the model. This methods checks the feasibility of the joints and instructs all joints to add their extensions and features.

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
            try:
                joint.check_elements_compatibility(joint.elements)  # TODO: is this necessary here? This should be done at joint creation.
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

    def create_beam_structural_segments(self) -> None:
        """Creates structural segments for all beams in the model based on their joints."""
        if not self.joints:
            raise ValueError("No joints in the model to create structural segments from.")

        if not self.beams:
            raise ValueError("No beams in the model to create structural segments for.")

        for beam in self.beams:
            self.remove_beam_structural_segments(beam)

        for edge in self._graph.edges():
            self._graph.unset_edge_attribute(edge, "structural_segments")

        solver = BeamStructuralElementSolver()
        for beam in self.beams:
            solver.add_structural_segments(beam, model=self)

        for joint in self.joints:
            solver.add_joint_structural_segments(joint, model=self)

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
        for joint in self.joints:
            if isinstance(joint, PlateJoint):
                self.remove_joint(joint)  # TODO do we want to remove plate joints?

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
        for joint in self.joints:
            if isinstance(joint, PanelJoint):
                self.remove_joint(joint)  # TODO do we want to remove plate joints?

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
