#!/bin/bash

<<notes
Reset everything.
notes

echo "[STATUS] resetting"
read -p "[QUESTION] erase everything? <y/N> " prompt
if ! [[ $prompt =~ [yY](es)* ]]; then { echo "[STATUS] bye"; exit 0; }; fi
echo "[STATUS] deleting pack/*"
rm -rf ./pack/*
touch pack/.info
echo "[STATUS] deleting env"
rm -rf ./env
if [[ -f logs/projects.txt ]]; then
  while read p; do
    echo "[STATUS] deleting ./$p"
    rm -rf ./$p
  done < logs/projects.txt
  rm logs/projects.txt
fi
echo "[STATUS] deleting logs/log-serve"
rm logs/log-serve
echo "[STATUS] deleting logs/log-*"
rm -rf logs/log-*
echo "[STATUS] delete the data manually from ./data/"
echo "[STATUS] delete the data manually from ./calc/"

