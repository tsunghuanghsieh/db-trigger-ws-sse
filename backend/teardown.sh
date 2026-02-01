#!/bin/zsh

ENV_NAME=db-trigger-ws-sse

# source this file
conda activate base
conda env remove --name $ENV_NAME