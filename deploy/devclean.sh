#!/bin/bash

<<notes
Reset the development server.
notes

source env/bin/activate
rm dev/data/db.sqlite3
rm -rf dev/data
rm -rf dev/calc
mkdir dev/data
mkdir dev/data/sources
python dev/manage.py migrate
git clone https://github.com/bradleyrp/automacs dev/data/docs
git clone https://github.com/bradleyrp/omnicalc dev/calc
mkdir dev/calc/calcs/specs
touch dev/calc/calcs/specs/meta.yaml
make -C dev/calc config defaults
make -C dev/data/docs docs
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin','','admin');print;quit()" | python ./dev/manage.py shell
deactivate
