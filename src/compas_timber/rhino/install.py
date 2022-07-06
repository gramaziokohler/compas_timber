import compas.plugins


@compas.plugins.plugin(category="install")
def installable_rhino_packages():
    return [
        "compas_timber"
    ]  # add all other dependencies that are needed and work in rhino


@compas.plugins.plugin(category="install")
def after_rhino_install(installed_packages):
    if "compas_timber" not in installed_packages:
        return []

    import compas_timber.ghpython.components.install

    return compas_timber.ghpython.components.install.install()


@compas.plugins.plugin(category="install")
def after_rhino_uninstall(installed_packages):
    if "compas_timber" not in installed_packages:
        return []

    import compas_timber.ghpython.components.install

    return compas_timber.ghpython.components.install.uninstall()
