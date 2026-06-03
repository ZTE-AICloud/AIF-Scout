PROJECTNAME="nvidia_runtime"
# Binary package name for release
BINARY=azalea_nvidia_runtime
VERSION=0.5
# Make is verbose in Linux. Make it silent.
MAKEFLAGS += --silent

CACHE_DIR := cache

# Examples: support absolute and relative path
# FILES ?= file1.txt \
#          dir1 \
#          file2.txt \
#          dir2
# 拷贝固件检查包到容器中/workspace/
FILES ?= ../utils \
		./tools \
		./nccl-tests


.PHONY: help
all: help
help: Makefile
	@echo
	@echo " Choose a command run in "$(PROJECTNAME)":"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' |  sed -e 's/^/ /'
	@echo

## build: Build & Export a nvidia runtime docker image
build: copy check-duplicate-images
	@echo "  >  Creating Docker Image ..."
	@sudo docker build -t $(BINARY):$(VERSION) -f Dockerfile .
	@echo "  >  Exporting Docker Image..."
	@sudo docker save --output $(BINARY)_$(VERSION).tar $(BINARY):$(VERSION)


## check-duplicate-images: Check for duplicate images
check-duplicate-images:
	echo $(BINARY):$(VERSION)
	if [ $$(sudo docker images $(BINARY):$(VERSION) | wc -l) -gt 1 ]; then \
		echo "Error: Duplicate images found for $(BINARY):$(VERSION)"; \
		exit 1; \
	fi

create_dir:
	mkdir -p $(CACHE_DIR)


## copy: Copy file or dir to cache directory
copy: create_dir clean
	@echo "  >  Start copy files to cache dir..."
	@if [ ! -z "$(FILES)" ]; then \
		for item in $(FILES); do \
			cp -r $$item $(CACHE_DIR); \
		done \
	fi

## clean: Clean cache directory
clean:
	rm -rf $(CACHE_DIR)/*
