# latest platform is local
export PLATFORM_LATEST ?= linux/amd64
# stable platform is target system
export PLATFORM_STABLE ?= linux/arm64/v8

export GITHUB_GHCR ?= ghcr.io
export GITHUB_USERNAME ?= gunny26
export REPOSITORY_NAME ?= $(shell pwd | rev | cut -d/ -f 1 | rev)

export DATESTRING ?= $(shell date -I)
export TAG ?= $(shell git describe --always)

export REGISTRY ?= $(GITHUB_GHCR)/$(GITHUB_USERNAME)/$(REPOSITORY_NAME)
export IMAGE_NAME ?= $(REGISTRY):$(DATESTRING)-$(TAG)
export IMAGE_NAME_LATEST ?= $(REGISTRY):latest
export IMAGE_NAME_STABLE ?= $(REGISTRY):stable

test:
	# needs docker-compose-v2 to be installed
	docker compose up -d && docker compose down

latest:
	git checkout latest
	echo "Image Tag $(IMAGE_NAME) and $(IMAGE_NAME_LATEST)"
	git commit -a -m "automatic pre latest image built commit"
	docker buildx build --platform $(PLATFORM_LATEST) --push -t $(IMAGE_NAME) -t $(IMAGE_NAME_LATEST) .
	# docker tag $(IMAGE_NAME) $(IMAGE_NAME_LATEST)
	git status && git commit -a -m "automatic post latest image built"
	git push origin latest

stable:
	git checkout main
	git pull latest
	echo "Image Tag $(IMAGE_NAME) and $(IMAGE_NAME_STABLE)"
	git commit -a -m "automatic pre stable commit"
	docker buildx build --platform $(PLATFORM_STABLE) --push -t $(IMAGE_NAME) -t $(IMAGE_NAME_STABLE) .
	git push origin main
	git checkout latest

lint:
	ruff check build/main.py
	ruff format build/main.py

clean:
	docker buildx prune
