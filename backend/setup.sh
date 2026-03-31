#!/bin/zsh

ENV_NAME=db-trigger-ws

if [ -z "$CONDA_EXE" ]; then
    # CONDA_EXE not set, exit with error
    echo "Error: CONDA_EXE is not set" >&2
    exit 1
else
    CONDA_BASE="$(dirname $(dirname "$CONDA_EXE"))"
fi

if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
else
    echo "Error: conda.sh not found. Please install Conda." >&2
    exit 1
fi

# source this file
conda create --name $ENV_NAME --clone base
conda activate $ENV_NAME
pip3 install -r "`dirname $0`/requirements.txt"
