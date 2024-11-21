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

.PHONY: python-sdk-codegen
python-sdk-codegen: # generate the python sdk
	echo "Generating the python sdk..."
	sudo rm -rf sdk/python
	mkdir -p sdk/python
	docker run --rm \
		-v $(PWD)/sdk:/local/sdk \
		swaggerapi/swagger-codegen-cli-v3:3.0.64 generate \
		-i /local/sdk/spec/apiserver/openapi.json \
		--api-package api \
		--model-package models \
		-l python \
		--additional-properties packageName=opsmatesdk version=0.1.0 \
		-o /local/sdk/python
