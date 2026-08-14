"""Opt-in tracing.

Library code here never prints. It emits messages to a tracer you install, which is off by
default and costs nothing when off.

The indirection exists because the interesting output has to reach wherever you happen to
be. A terminal wants ``print``. Grasshopper wants the messages appended to a list you can
wire to a panel -- Rhino's handling of ``stdout`` varies with how the component was created
and which Python runtime is behind it, so writing to a list is the only way that always
works.

Examples
--------
>>> from assembly_sequencing import set_tracer, trace
>>> set_tracer(True)  # print
>>> lines = []
>>> _ = set_tracer(lines.append)  # or collect, for a Grasshopper panel
>>> trace("hello")
>>> lines
['hello']
>>> _ = set_tracer(None)  # off again

"""

_TRACER = None


def set_tracer(tracer):
    """Install a tracer.

    Parameters
    ----------
    tracer : callable or bool or None
        A callable taking one string. ``True`` installs :func:`print`. ``None`` or
        ``False`` turns tracing off.

    Returns
    -------
    callable or None
        The tracer that was previously installed, so it can be restored.

    """
    global _TRACER
    previous = _TRACER
    if tracer is True:
        _TRACER = print
    elif tracer is None or tracer is False:
        _TRACER = None
    elif callable(tracer):
        _TRACER = tracer
    else:
        raise TypeError("tracer must be callable, True, False or None, not {!r}".format(type(tracer).__name__))
    return previous


def get_tracer():
    """The installed tracer, or None.

    Returns
    -------
    callable or None

    """
    return _TRACER


def tracing():
    """Whether tracing is on.

    Check this before building an expensive message.

    Returns
    -------
    bool

    """
    return _TRACER is not None


def trace(message):
    """Emit a message to the installed tracer, if any.

    Parameters
    ----------
    message : str

    """
    if _TRACER is not None:
        _TRACER(message)
