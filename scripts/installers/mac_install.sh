#!/bin/sh

CONDA_HOME=$HOME/miniconda
CONDA_BIN=$CONDA_HOME/condabin
CONDA_ENV_NAME=ct_env

if ! command -V conda &> /dev/null
then
	echo "Anaconda not found. Installing miniconda…"
	curl https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o ./miniconda.sh &> /dev/null
	bash ./miniconda.sh -b -p $CONDA_HOME &> /dev/null
	echo "Anaconda not found. Installing miniconda…Done!"

	echo "Configuring anaconda for first use…"
	$CONDA_BIN/conda init bash &> /dev/null
	source $HOME/.bash_profile &> /dev/null
	echo "Configuring anaconda for first use…Done!"
fi

echo "Setting up conda environment…"
conda create -n $CONDA_ENV_NAME -c conda-forge compas -y &> /dev/null
echo "Setting up conda environment…Done"

echo "Activating environment…"
conda activate $CONDA_ENV_NAME
echo "Activating environment…Done!"

echo "Installing compas_future…"
python -m pip install --force-reinstall --no-input --quiet ./compas_future-main.zip
python -m compas_rhino.install
echo "Installing compas_future…Done!"

echo "Installing compas_timber…"
python -m pip install --force-reinstall --no-input --quiet ./compas_timber-dev.zip
python -m compas_rhino.install
echo "Installing compas_timber…Done!"
