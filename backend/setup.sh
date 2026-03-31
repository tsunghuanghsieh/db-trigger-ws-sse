#!/bin/zsh

ENV_NAME=db-trigger-ws

# source this file to set up the environment
if [[ $- != *i* ]]; then
    echo "Please run 'source $0' to set up the environment."
    exit 0
fi

env_exists=$(conda env list | grep -w $ENV_NAME)
if [[ -z "$env_exists" ]]; then
    conda create --name $ENV_NAME python=3.12 -y | sed '/^#$/,/^# To deactivate/ d'
    conda activate $ENV_NAME
    pip3 install -r "`dirname $0`/requirements.txt"
else
    conda activate $ENV_NAME
fi

