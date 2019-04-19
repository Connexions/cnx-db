STATEDIR = $(PWD)/.state
BINDIR = $(STATEDIR)/env/bin

# Short descriptions for commands (var format _SHORT_DESC_<cmd>)
_SHORT_DESC_BUILD := "Build the db for dev and/or deployment"
_SHORT_DESC_DOCS := "Build docs"
_SHORT_DESC_LINT := "Run linting tools on the codebase"
_SHORT_DESC_PYENV := "Set up the python environment"
_SHORT_DESC_SERVE := "Serve the db"
_SHORT_DESC_TEST := "Run the tests"

default : help
	@echo "You must specify a command"
	@exit 1

# ###
#  Helpers
# ###

_REQUIREMENTS_FILES = requirements/main.txt requirements/docs.txt requirements/test.txt
VENV_EXTRA_ARGS =

$(STATEDIR)/env/pyvenv.cfg : $(_REQUIREMENTS_FILES)
ifeq ($(PYTHON_VERSION),2)
	@echo "Using Python 2.7 ..."
	rm -rf $(STATEDIR)/env
	virtualenv -p $$(which python2.7) $(VENV_EXTRA_ARGS) $(STATEDIR)/env
	# Mark this as having been built
	touch $(STATEDIR)/env/pyvenv.cfg
else
	@echo "Using Python 3..."
	# Create our Python 3 virtual environment
	rm -rf $(STATEDIR)/env
	python3 -m venv $(VENV_EXTRA_ARGS) $(STATEDIR)/env
endif
	# Upgrade tooling requirements
	$(BINDIR)/python -m pip install --upgrade pip wheel tox setuptools

	# Install requirements
	$(BINDIR)/python -m pip install $(foreach req,$(_REQUIREMENTS_FILES),-r $(req))
	# Install the package
	$(BINDIR)/python -m pip install -e .


$(STATEDIR)/lint-env/pyvenv.cfg : requirements/lint.txt
ifeq ($(PYTHON_VERSION),2)
	@echo "Using Python 2.7 ..."
	rm -rf $(STATEDIR)/lint-env
	virtualenv -p $$(which python2.7) $(VENV_EXTRA_ARGS) $(STATEDIR)/lint-env
	# Mark this as having been built
	touch $(STATEDIR)/lint-env/pyvenv.cfg
else
	@echo "Using Python 3..."
	# Create our Python 3 virtual environment
	rm -rf $(STATEDIR)/lint-env
	python3 -m venv $(VENV_EXTRA_ARGS) $(STATEDIR)/lint-env
endif
	# Upgrade tooling requirements
	$(STATEDIR)/lint-env/bin/python -m pip install --upgrade pip wheel tox setuptools

	# Install requirements
	$(STATEDIR)/lint-env/bin/python -m pip install -r requirements/lint.txt


$(STATEDIR)/docker-build: Dockerfile requirements/main.txt requirements/deploy.txt
	# Build our docker container(s) for this project.
	docker-compose build

	# Mark the state so we don't rebuild this needlessly.
	mkdir -p $(STATEDIR)
	touch $(STATEDIR)/docker-build

# /Helpers

# ###
#  Help
# ###

help :
	@echo ""
	@echo "Usage: make <cmd> [<VAR>=<val>, ...]"
	@echo ""
	@echo "Where <cmd> can be:"  # alphbetical please
	@echo "  * docs -- ${_SHORT_DESC_DOCS}"
	@echo "  * help -- this info"
	@echo "  * help-<cmd> -- for more info"
	@echo "  * lint -- ${_SHORT_DESC_LINT}"
	@echo "  * pyenv -- ${_SHORT_DESC_PYENV}"
	@echo "  * test -- ${_SHORT_DESC_TEST}"
	@echo "  * version -- Print the version"
	@echo ""
	@echo "Where <VAR> can be:"  # alphbetical please
	@echo ""

# /Help

# ###
#  Pyenv
# ###

# Specify the major python version: 2 or 3 (default)
PYTHON_VERSION = 3

help-pyenv :
	@echo "${_SHORT_DESC_PYENV}"
	@echo "Usage: make pyenv"
	@echo ""
	@echo "Where <VAR> could be:"  # alphbetical please
	@echo "  * PYTHON_VERSION -- major version of python to use: 2 or 3 (default: '$(PYTHON_VERSION)')"
	@echo "  * VENV_EXTRA_ARGS -- extra arguments to give venv (default: '$(VENV_EXTRA_ARGS)')"

pyenv : $(STATEDIR)/env/pyvenv.cfg

# /Pyenv

# ###
#  Test
# ###

TEST =
TEST_EXTRA_ARGS =

help-test :
	@echo "${_SHORT_DESC_TEST}"
	@echo "Usage: make test [<arguments-to-pytest> ...]"
	@echo ""

test : $(STATEDIR)/env/pyvenv.cfg
	$(BINDIR)/tox -- $(filter-out $@, $(MAKECMDGOALS))

# /Test

# ###
#  Version
# ###

version help-version : .git
	@$(BINDIR)/python setup.py --version 2> /dev/null

# /Version

# ###
#  Docs
# ###

help-docs :
	@echo "${_SHORT_DESC_DOCS}"
	@echo "Usage: make docs"

docs : $(STATEDIR)/env/pyvenv.cfg
	$(MAKE) -C docs/ doctest SPHINXOPTS="-W" SPHINXBUILD="$(BINDIR)/sphinx-build"
	$(MAKE) -C docs/ html SPHINXOPTS="-W" SPHINXBUILD="$(BINDIR)/sphinx-build"

# /Docs

# ###
#  Lint
# ###

help-lint :
	@echo "${_SHORT_DESC_LINT}"
	@echo "Usage: make lint"

lint : $(STATEDIR)/lint-env/pyvenv.cfg setup.cfg
	$(STATEDIR)/lint-env/bin/python -m flake8 .
	@echo '====  ====  ====  ====  ====  ====  ====  ====  ====  ===='
	$(STATEDIR)/lint-env/bin/python bin/doc8 README.rst docs/

# /Lint

.PHONY: docs

# ###
#  Build
# ###

help-build :
	@echo "${_SHORT_DESC_BUILD}"
	@echo "Usage: make build"

build:
	# This is duplicate of $(STATEDIR)/docker-build to force the build.

	# Build our docker container(s) for this project.
	docker-compose build

	# Mark the state so we don't rebuild this needlessly.
	mkdir -p $(STATEDIR)
	touch $(STATEDIR)/docker-build

# /Build


# ###
#  Serve
# ###

help-serve :
	@echo "${_SHORT_DESC_SERVE}"
	@echo "Usage: make serve"

serve: $(STATEDIR)/docker-build
	docker-compose up

# /Serve

# ###
#  Catch-all to avoid errors when passing args to make test
# ###

%:
	@:
# /Catch-all
