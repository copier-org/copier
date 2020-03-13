#!/usr/bin/env bash
echo $STAGE "$@" >> created-with-tasks.txt
git init
rm -f delete-in-tasks.txt
