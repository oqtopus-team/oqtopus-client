SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := generate-models

OAS_FILE ?= openapi.yaml
OAS_URL ?= https://raw.githubusercontent.com/oqtopus-team/oqtopus-cloud/develop/backend/oas/user/openapi.yaml
OPENAPI_GENERATOR_IMAGE ?= openapitools/openapi-generator-cli:v7.8.0
MODEL_OUTPUT_DIR ?= ../src/oqtopus_client/models/generated/models
GEN_TMP_DIR ?= .openapi-generator-output

.PHONY: download-oas generate-models

download-oas:
	mkdir -p $$(dirname "$(OAS_FILE)")
	curl -fsSL $(OAS_URL) -o $(OAS_FILE)

generate-models:
	test -f "$(OAS_FILE)" || $(MAKE) download-oas
	mkdir -p $(GEN_TMP_DIR)
	docker run --rm -u $$(id -u):$$(id -g) \
		-v "$$(pwd):/local/spec" \
		-v "$$(pwd)/$(GEN_TMP_DIR):/local/out" \
		$(OPENAPI_GENERATOR_IMAGE) generate \
		-g python \
		-i /local/spec/$(OAS_FILE) \
		-o /local/out \
		--global-property=models,modelDocs=false,modelTests=false,apis=false,apiDocs=false,apiTests=false \
		--additional-properties=packageName=oqtopus_client.models.generated,projectName=oqtopus-client,hideGenerationTimestamp=true
	mkdir -p $(MODEL_OUTPUT_DIR)
	rsync -a $(GEN_TMP_DIR)/oqtopus_client/models/generated/models/ $(MODEL_OUTPUT_DIR)/
