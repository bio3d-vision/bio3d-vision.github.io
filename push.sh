#!/usr/bin

pandoc platelet-description.md -o platelet-description.html

bash makeindex.sh

git add -A .

git commit -m "$1"

git push origin HEAD