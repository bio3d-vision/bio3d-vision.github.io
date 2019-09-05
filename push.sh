#!/usr/bin

bash makeindex.sh

git add -A .

git commit -m "$1"

git push origin HEAD