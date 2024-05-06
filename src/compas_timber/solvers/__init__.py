"""
********************************************************************************
solvers
********************************************************************************

.. currentmodule:: compas_timber.solvers

.. rst-class:: lead

This module contains pluggable functions for the sequence generating puzzle checker extensions.

Pluggables
==========
.. autosummary::
    :toctree: generated/
    :nosignatures:

    next_removable_part
    create_dissassembly_sequence

"""

from compas.plugins import PluginNotInstalledError, pluggable


@pluggable(category="solvers")
def next_removable_part(assembly, removed_part_ids, part_ids_to_remove, number_of_parts_to_remove, **kwargs):
    """Returns the next part to remove from the assembly.

    One or more parts of the assembly are choosen to be removed next based on the particular solver implementation.

    Parameters
    ----------
    assembly : `compas.datastructures.Assembly`
        The assembly to remove parts from.
    removed_part_ids : list
        The list of part ids that have already been removed.
    part_ids_to_remove : list
        The list of part ids that are to be removed.
    number_of_parts_to_remove : int
        The number of parts to remove from the assembly.

    Returns
    -------
    :class:`compas_monosashi.sequencer.Step`
        A step which contains one or more Instructions which specify
        the parts to remove from the assembly and the corresponding removal direction.

    """
    raise PluginNotInstalledError


@pluggable(category="solvers")
def create_dissassembly_sequence(assembly, **kwargs):
    """Returns a sequence of steps to disassemble the assembly.

    This function's implementation decides on the strategy used to generate the collection of
    steps to disassemble the assembly and determines their order.

    The order of steps can be revered in order to generate a sequence of steps to assemble the assembly.

    Parameters
    ----------
    assembly : `compas.datastructures.Assembly`
        The assembly to disassemble.

    Returns
    -------
    :class:`compas_monosashi.sequencer.BuildingPlan`
        A sequence of steps to disassemble the assembly.

    See Also
    --------
    :func:`~compas_timber.solvers.next_removable_part`

    """
    raise PluginNotInstalledError
