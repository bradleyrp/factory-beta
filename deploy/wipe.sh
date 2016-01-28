#!/bin/bash

<<notes
Reset everything.
Duplicates reset with no confirmation.
notes

#---no enter because -n flag below
read -p "[QUESTION] \"reconnect\" starts entirely from scratch. continue? " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then echo "\n[STATUS] reconnecting"
else exit 1; fi

echo "[STATUS] automatically resetting"
echo "[STATUS] deleting pack/*"
rm -rf ./pack/*
echo "[STATUS] deleting env"
rm -rf ./env
if [[ -f logs/projects.txt ]]; then
  while read p; do
    echo "[STATUS] deleting ./site/$p"
    rm -rf ./site/$p
  done < logs/projects.txt
  rm logs/projects.txt
fi
echo "[STATUS] deleting logs/log-serve"
rm -rf logs/log-server
echo "[STATUS] deleting logs/log-*"
rm -rf logs/log-*
echo "[STATUS] deleting write/*"
rm -rf write/*
echo "[STATUS] deleting ./data/*"
rm -rf ./data/*
touch ./data/.info
echo "[STATUS] deleting ./calc/*"
rm -rf ./calc/*
