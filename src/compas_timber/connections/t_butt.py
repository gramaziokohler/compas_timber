from .butt_joint import ButtJoint
from .solver import JointTopology


class TButtJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket/lap to be milled in the cross beam.
        If `butt_plane_id` is provided, the pocket/lap's depth direction will be along the main beam's centerline direction.
        Otherwise, the pocket/lap's depth direction will be along the normal of the butt_plane.
    butt_plane_id : int, optional
        The BTLx integer ID (>= 100) of a `user_ref_plane` registered on `cross_beam` via :meth:`~compas_timber.base.TimberElement.add_user_ref_plane`.
        Overrides the automatic calculation of the closest butt plane to the main_beam.
    force_pocket : bool
        If `True` applies a `:~compas_timber.fabrication.Pocket` feature instead of a `:~compas_timber.fabrication.Lap` on the cross beam. Default is `False`.
    conical_tool : bool
        If `True` it can apply smaller than 90 degrees angles to the TiltSide parameters of the `:~compas_timber.fabrication.Pocket` feature. Default is `False`.
    fastener : :class:`~compas_timber.elements.Fastener`, optional
        The fastener to be used in the joint.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    butt_plane : :class:`~compas.geometry.Plane`
        The plane used to cut the main beam. If not overridden via `butt_plane_id`, the closest side of the cross beam will be used.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        mill_depth=None,
        butt_plane_id=None,
        force_pocket=False,
        conical_tool=False,
        fastener=None,
        **kwargs,
    ):
        super(TButtJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            butt_plane_id=butt_plane_id,
            force_pocket=force_pocket,
            conical_tool=conical_tool,
            **kwargs,
        )

        self.fasteners = []
        if fastener:
            if fastener.outline is None:
                fastener = fastener.copy()  # make a copy to avoid modifying the original fastener
                fastener.set_default(joint=self)
            self.base_fastener = fastener
            if self.base_fastener:
                self.base_fastener.place_instances(self)

    @property
    def interactions(self):
        """Returns interactions between elements used by this joint."""
        interactions = []
        interactions.append((self.main_beam, self.cross_beam))
        for fastener in self.fasteners:
            for interface in fastener.interfaces:
                if interface is not None:
                    interactions.append((interface.element, fastener))
        return interactions

    @property
    def generated_elements(self):
        return self.fasteners
