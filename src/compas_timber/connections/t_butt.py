from .butt_joint import ButtJoint
from .solver import JointTopology


class TButtJoint(ButtJoint):
    """Represents a T-Butt type joint which joins the end of a beam along the length of another beam,
    trimming the main beam.

    This joint type is compatible with beams in T topology.

    Please use `TButtJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.
    butt_plane : :class:`~compas.geometry.Plane`, optional
        The plane used to cut the main beam. If not provided, the closest side of the cross beam will be used.
    fastener : :class:`~compas_timber.parts.Fastener`, optional
        The fastener to be used in the joint.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        The main beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        The cross beam to be joined.
    mill_depth : float
        The depth of the pocket to be milled in the cross beam.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    def __init__(self, main_beam=None, cross_beam=None, mill_depth=None, butt_plane=None, fastener=None, **kwargs):
        super(TButtJoint, self).__init__(main_beam=main_beam, cross_beam=cross_beam, mill_depth=mill_depth, butt_plane=butt_plane, **kwargs)
        self.modify_cross = False
        self.fasteners = []
        if fastener:
            if fastener.outline is None:
                fastener = fastener.copy()  # make a copy to avoid modifying the original fastener
                fastener.set_default(joint=self)
            self.base_fastener = fastener
            if self.base_fastener:
                self.base_fastener.place_instances(self)

    @classmethod
    def create(cls, model, main_beam, cross_beam, mill_depth=None, small_beam_butts=False, modify_cross=True, reject_i=False, butt_plane=None, **kwargs):
        """Creates an L-Butt joint and associates it with the provided model.

        Parameters
        ----------
        model : :class:`~compas_timber.model.Model`
            The model to which the joint will be added.
        main_beam : :class:`~compas_timber.parts.Beam`
            The main beam to be joined.
        cross_beam : :class:`~compas_timber.parts.Beam`
            The cross beam to be joined.
        mill_depth : float
            The depth of the pocket to be milled in the cross beam. This will be ignored if `butt_plane` is provided.
        small_beam_butts : bool, default False
            If True, the beam with the smaller cross-section will be trimmed. Otherwise, the main beam will be trimmed."""

        if butt_plane:
            butt_plane = butt_plane.transformed(main_beam.modeltransformation.inverse())

        joint = TButtJoint(
            main_beam=main_beam,
            cross_beam=cross_beam,
            mill_depth=mill_depth,
            small_beam_butts=small_beam_butts,
            modify_cross=modify_cross,
            reject_i=reject_i,
            butt_plane=butt_plane,
            **kwargs,
        )
        model.add_joint(joint)
        return joint

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
    def elements(self):
        return self.beams + self.fasteners

    @property
    def generated_elements(self):
        return self.fasteners
