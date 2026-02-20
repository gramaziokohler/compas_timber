# Installation

## User

!!! note
    While there are many similar tools, we recommend using `mamba` to manage your Python environments.
    It can be installed from [here](https://github.com/conda-forge/miniforge/releases/tag/25.3.0-3).

```bash
mamba create -n <myenvname> compas_timber -c conda-forge --yes
mamba activate <myenvname>
```

## Developer

If you wish to contribute to or modify COMPAS Timber, [fork the repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) and clone the fork

```bash
git clone https://github.com/<yourgithub_username>/compas_timber.git
cd compas_timber
```

Create a new environment if necessary

```bash
mamba create -n <myenvname> python=3.10 --yes
mamba activate <myenvname>
```

Install the package in editable mode with its development dependencies

```bash
pip install -e .[dev]
```

To compile the Rhino8 Grasshopper components

```bash
invoke build-cpython-ghuser-components
```
