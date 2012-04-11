#!/bin/bash
clear
rm -rf __pycache__
rm -rf tests/__pycache__
rm -rf docs/build

rm -rf build
rm -rf dist
rm -rf *.egg-info

find . -name "*.pyc" -exec rm -rf {} \;
find . -name ".DS_Store" -exec rm -rf {} \;
python setup.py sdist upload
