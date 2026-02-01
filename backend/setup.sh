#!/bin/zsh

ENV_NAME=db-trigger-ws

# source this file
conda create --name $ENV_NAME --clone base
conda activate $ENV_NAME
pip3 install -r "`dirname $0`/requirements.txt"
