#!/bin/bash

(
    cd ./apps/innovation-lab
    docker build -t innovation-lab-app:v1 .
    kind load docker-image innovation-lab-app:v1 --name troubleshooting-eval
)
