#!/bin/sh
for i in `ps -ef| awk '$3 == '$1' { print $2 }'`
do
echo killing $i
kill -9 $i
done
