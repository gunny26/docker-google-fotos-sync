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

testrun:
	export APP_REDIS_HOST=redis-lmp.messner.click
	export APP_INTERFACE=wlp4s0
	sudo python3 build/main.py

latest:
	echo $(IMAGE_NAME)
	git commit -a -m "automatic pre latest image built commit"
	echo "using $(DATESTRING)-$(TAG)"
	docker buildx build --platform $(PLATFORM_LATEST) --push -t $(IMAGE_NAME),$($IMAGE_NAME_LATEST) .
	# docker tag $(IMAGE_NAME) $(IMAGE_NAME_LATEST)
	git commit -a -m "automatic post latest image built"

stable:
	echo $(IMAGE_NAME)
	git commit -a -m "automatic pre deployment commit"
	echo "using $(DATESTRING)-$(TAG)"
	# docker build --no-cache --platform $(PLATFORM) -t $(IMAGE_NAME) .
	docker buildx build --platform $(PLATFORM_STABLE) --push -t $(IMAGE_NAME_STABLE) .
	docker buildx build --platform $(PLATFORM_STABLE) --push -t $(IMAGE_NAME_STABLE) .
	git push origin main

lint:
	ruff check build/main.py
	ruff format build/main.py

clean:
	docker buildx build prune
