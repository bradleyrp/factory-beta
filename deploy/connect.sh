#!/bin/bash

read -p "[QUESTION] \"reconnect\" starts entirely from scratch...are you sure? " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then echo "[STATUS] reconnecting"
else; exit 1; fi
