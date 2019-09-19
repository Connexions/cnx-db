#!/bin/bash

pip install twine
python setup.py bdist_wheel --universal
twine check dist/*
