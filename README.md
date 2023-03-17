# compas_timber

COMPAS package for modeling, designing and fabricating timber assemblies

# Installation
## One-click Installer 

> This script relies on the presence of a `compas_timber` and `compas_future` wheels in the same directory

This batch installer:
1. Downloads `miniconda` from [here](https://repo.anaconda.com/miniconda/)
2. Installs `miniconda`
3. Creates a new `conda` virtual environment with COMPAS and required dependencies
4. Installs `compas_future` from an offline wheel present in the same directory
4. Installs `compas_timber` from an offline wheel present in the same directory
5. Installs `compas_timber` components to the local `Rhino` installation

### Usage

Obtain offline wheels for both `compas_timber` and `compas_future`, this can be done by donwloading both repositories 
as a `.zip` file. Place both `.zip` files in a directory together with the script.

#### Windows
Copy the `win_install.cmd` script along with a zipped `compas_timber` to the target machine.

Locate `win_install.cmd` and double click.

Alternatively, open a `cmd.exe` session, locate the script, and run:
```commandline
> win_install.cmd
```

#### Mac
Copy `mac_install.cmd` script along with a zipped `compas_timber` to the target machine.

Open a terminal session, and navigate to the script's location.

Run the installer using:
```commandline
> source mac_install.sh
```

## Grasshopper Plugin
### Tutorial and documentation: [see here](https://github.com/gramaziokohler/compas_timber_Grasshopper_wiki)


