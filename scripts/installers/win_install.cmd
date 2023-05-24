@ECHO OFF

SET conda_path=%UserProfile%\Miniconda3
SET env_name=ct_env

CALL curl -S -s -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
IF %ERRORLEVEL% neq 0 GOTO miniconda_download_failed

ECHO Installing miniconda...

CALL Miniconda3-latest-Windows-x86_64.exe /InstallationType=JustMe /RegisterPython=0 /S /D=%conda_path%

ECHO Installing miniconda...Done!

CALL %conda_path%\condabin\conda activate %env_name% >nul 2>&1
IF %ERRORLEVEL%==0 GOTO compas_install_main

ECHO Creating virtual environment...
CALL %conda_path%\condabin\conda create -n %env_name% python=3.10 -y >nul 2>&1
ECHO Creating virtual environment...Done!

ECHO Activating virtual environment...
CALL %conda_path%\condabin\conda activate %env_name%
IF %ERRORLEVEL% neq 0 GOTO conda_activate_failed
ECHO Activating virtual environment...Done

:compas_install_main
ECHO Installing compas from main...
python -m pip install --no-input --quiet compas@git+https://github.com/compas-dev/compas@main
ECHO Installing compas from main...Done!

:timber_install_pip
ECHO Installing compas_timber...
python -m pip install --force-reinstall --no-input --quiet compas_timber
python -m compas_rhino.install
ECHO Installing compas_timber...Done!

PAUSE
EXIT /B %errorlevel%

:conda_activate_failed
ECHO Could not activate virtual environment. Exiting.
PAUSE
EXIT /B %errorlevel%

:miniconda_download_failed
ECHO Could not download miniconda. Exiting.
PAUSE
EXIT /B %errorlevel%

