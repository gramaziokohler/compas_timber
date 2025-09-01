def test_ipy_syntax():
    # this is a rather superficial check that these are importable i.e. don't contain any python2.7 syntax errors
    # actual unittests aren't being executed because they occasionally use advanced pytest features which aren't available in ironpython-pytest
    # and it probably makes little sense to add this support due to the imminent deprecation of ironpython support
    import compas_timber.connections  # noqa: F401
    import compas_timber.elements  # noqa: F401
    import compas_timber.solvers  # noqa: F401
    import compas_timber.errors  # noqa: F401
    import compas_timber.fabrication  # noqa: F401
    import compas_timber.model  # noqa: F401
    import compas_timber.planning  # noqa: F401
    import compas_timber.ghpython  # noqa: F401
    import compas_timber.rhino  # noqa: F401
