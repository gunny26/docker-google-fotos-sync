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
	echo $(IMAGE_NAME) > latest.tmp
	git commit -a -m "automatic pre latest image built commit" | tee -a latest.tmp
	echo "using $(DATESTRING)-$(TAG)" | tee -a latest.tmp
	docker build --platform $(PLATFORM_LATEST) -t $(IMAGE_NAME) . | tee -a latest.tmp
	docker tag $(IMAGE_NAME) $(IMAGE_NAME_LATEST) | tee -a latest.tmp
	mv latest.tmp latest.log
	git add latest.log
	git commit -a -m "automatic post latest image built"

stable:
	echo $(IMAGE_NAME) > stable.tmp
	git add * | tee -a stable.tmp
	git commit -a -m "automatic pre deployment commit" | tee -a stable.tmp
	echo "using $(DATESTRING)-$(TAG)" | tee -a stable.tmp
	# docker build --no-cache --platform $(PLATFORM) -t $(IMAGE_NAME) . | tee -a stable.tmp
	docker build --platform $(PLATFORM_STABLE) -t $(IMAGE_NAME) . | tee -a stable.tmp
	docker tag $(IMAGE_NAME) $(IMAGE_NAME_LATEST) | tee -a stable.tmp
	docker tag $(IMAGE_NAME) $(IMAGE_NAME_STABLE) | tee -a stable.tmp
	docker push $(IMAGE_NAME) | tee -a stable.tmp
	docker push $(IMAGE_NAME_STABLE) | tee -a stable.tmp
	mv stable.tmp stable.log
	git add stable.log
	git push origin main

lint:
	ruff check build/main.py
	ruff format build/main.py

clean:
	if [ -f stable.log ]; then rm stable.log; fi
	if [ -f stable ]; then rm stable; fi
	if [ -f latest.log ]; then rm latest.log; fi
	if [ -f latest ]; then rm latest; fi
