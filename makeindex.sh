#!/bin/bash

echo "---
layout: page
title: 'bio3d-vision'
use-site-title: false
---
" > indexhead.html

pandoc README.md -o README.html

cat indexhead.html README.html > index.html

rm indexhead.html

rm README.html
