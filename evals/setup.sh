#!/bin/bash

set -euo pipefail

scriptDir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")

(
    cd $scriptDir/apps/innovation-lab
    docker build -t innovation-lab-app:v1 .
    kind load docker-image innovation-lab-app:v1 --name troubleshooting-eval
)

(
    cd $scriptDir/apps/audit-server
    docker build -t audit-server:v1 .
    kind load docker-image audit-server:v1 --name troubleshooting-eval
)

kubectl apply -f $scriptDir/scenarios/

(
	rm -rf /tmp/kube-prometheus
	git clone https://github.com/prometheus-operator/kube-prometheus  --depth 1 /tmp/kube-prometheus
	cd /tmp/kube-prometheus
	kubectl apply --server-side -f manifests/setup
	kubectl wait \
		--for condition=Established \
		--all CustomResourceDefinition \
		--namespace=monitoring
	kubectl apply -f manifests/
)


echo "Waiting for all the pods in the monitoring namespace to be ready..."
kubectl wait --for=condition=ready --all pod --namespace=monitoring --timeout=300s
echo "All the pods in the monitoring namespace are ready"
