-include .env
PROJECTNAME=$(shell basename "$(PWD)")
# Binary package name for release
VERSION=v1

IMAGE_TAG:=azalea_app:${VERSION}

# Make is verbose in Linux. Make it silent.
MAKEFLAGS += --silent


.PHONY: help
all: help
help: Makefile
	@echo
	@echo " Choose a command run in "$(PROJECTNAME)":"
	@echo
	@sed -n 's/^##//p' $< | column -t -s ':' |  sed -e 's/^/ /'
	@echo

## imagebuild: Build Docker Image
imagebuild:
	@echo "  >  Creating Docker Image ..."
	@sudo docker build -t $(IMAGE_TAG) .
