from .joint import JointTopology
from .tenon_mortise_joint import TenonMortiseJoint


class TTenonMortiseJoint(TenonMortiseJoint):
    """
    Represents a TenonMortise type joint which joins two beams, one of them at its end (main) and the other one along its centerline (cross) or both of them at their ends.
    A tenon is added on the main beam, and a corresponding mortise is made on the cross beam to fit the main beam's tenon.

    This joint type is compatible with beams in T and L topology.

    Please use `TenonMortiseJoint.create()` to properly create an instance of this class and associate it with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined. This is the beam that will receive the tenon.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined. This is the beam that will receive the mortise.
    start_y : float, optional
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float, optional
        Depth of the tenon from the surface of the main beam.
    rotation : float, optional
        Rotation of the tenon around the main beam's axis.
    length : float, optional
        Length of the tenon.
    width : float, optional
        Width of the tenon.
    height : float, optional
        Height of the tenon.
    shape : int, optional
        The shape of the tenon, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float, optional
        The radius used to define the shape of the tenon, if applicable.


    Attributes
    ----------
    main_beam : :class:`~compas_timber.parts.Beam`
        First beam to be joined.
    cross_beam : :class:`~compas_timber.parts.Beam`
        Second beam to be joined.
    main_beam_guid : str
        GUID of the main beam.
    cross_beam_guid : str
        GUID of the cross beam.
    start_y : float
        Start position of the tenon along the y-axis of the main beam.
    start_depth : float
        Depth of the tenon from the surface of the main beam.
    rotation : float
        Rotation of the tenon around the main beam's axis.
    length : float
        Length of the tenon along the main beam.
    width : float
        Width of the tenon.
    height : float
        Height of the tenon.
    shape : int
        The shape of the tenon, represented by an integer index: 0: AUTOMATIC, 1: SQUARE, 2: ROUND, 3: ROUNDED, 4: RADIUS.
    shape_radius : float
        The radius used to define the shape of the tenon, if applicable.
    features : list
        List of features or machining processings applied to the elements.
    """

    SUPPORTED_TOPOLOGY = [JointTopology.TOPO_T]

    def __init__(self, main_beam, cross_beam, start_y=None, start_depth=None, rotation=None, length=None, width=None, height=None, shape=None, shape_radius=None, **kwargs):
        super(TTenonMortiseJoint, self).__init__(
            main_beam=main_beam,
            cross_beam=cross_beam,
            start_y=start_y,
            start_depth=start_depth,
            rotation=rotation,
            length=length,
            width=width,
            height=height,
            shape=shape,
            shape_radius=shape_radius,
            **kwargs,
        )
