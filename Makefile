# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
GOBIN=$(shell go env GOPATH)/bin
else
GOBIN=$(shell go env GOBIN)
endif


SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

LOCALBIN ?= $(shell pwd)/.bin

KIND ?= $(LOCALBIN)/kind

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

.PHONY: kind
kind: $(LOCALBIN)
	test -s $(LOCALBIN)/kind || curl -Lo $(LOCALBIN)/kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64 && chmod +x $(LOCALBIN)/kind

.PHONY: kind-cluster
kind-cluster: kind
	$(KIND) create cluster --config eval/bootstrap/kind.yaml

.PHONY: kind-destroy
kind-destroy: kind
	$(KIND) delete cluster --name troubleshooting-eval


.PHONY: api-gen
api-gen: # generate the api spec
	echo "Generating the api spec..."
	poetry run python scripts/api-gen.py
