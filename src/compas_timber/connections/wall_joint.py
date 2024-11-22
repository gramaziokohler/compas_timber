from compas_model.interactions import Interaction

from .joint import JointTopology


class WallJoint(Interaction):
    """Models a wall to wall interaction.

    TODO:First in a very minimal way until we know where this is going.

    Parameters
    ----------
    wall_a : :class:`compas_timber.elements.Wall`
        The first wall.
    wall_b : :class:`compas_timber.elements.Wall`
        The second wall.
    topology : literal(JointTopology)
        The topology in which the walls are connected.

    Attributes
    ----------
    walls : tuple of :class:`compas_timber.elements.Wall`
        The walls that are connected.

    """

    @property
    def __data__(self):
        data = super(WallJoint, self).__data__
        data["wall_a_guid"] = self._wall_a_guid
        data["wall_b_guid"] = self._wall_b_guid
        data["topology"] = self.topology
        return data

    def __init__(self, wall_a, wall_b, topology=None, **kwargs):
        super(WallJoint, self).__init__(**kwargs)
        self.wall_a = wall_a
        self.wall_b = wall_b
        self._wall_a_guid = kwargs.get("wall_a_guid", None) or str(wall_a.guid)
        self._wall_b_guid = kwargs.get("wall_b_guid", None) or str(wall_b.guid)
        self.topology = topology or JointTopology.TOPO_UNKNOWN

    def __repr__(self):
        return "WallJoint({0}, {1}, {2})".format(
            self._wall_a_guid, self._wall_b_guid, JointTopology.get_name(self.topology)
        )

    @property
    def walls(self):
        return self.wall_a, self.wall_b
