#!/bin/bash

<<notes
Script to nuke and re-clone omnicalc during calculation development.
notes

rm -rf dev/calc
git clone /home/ryb/worker/analysis/omnicalc-joe dev/calc
mkdir dev/calc/calcs/specs
touch dev/calc/calcs/specs/meta.yaml
make -C dev/calc config defaults

