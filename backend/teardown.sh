#!/bin/zsh

ENV_NAME=db-trigger-ws-sse

# source this file to tear down the environment
if [[ $- != *i* ]]; then
    echo "Please run 'source $0' to tear down the environment."
    exit 0
fi

conda activate base
env_exists=$(conda env list | grep -w $ENV_NAME)
if [[ -n "$env_exists" ]]; then
    conda env remove --name $ENV_NAME -y
fi
