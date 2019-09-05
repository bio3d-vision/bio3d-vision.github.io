#!/bin/bash

echo "---
layout: page
title: 'bio3d-vision'
use-site-title: false
---
" > indexhead.html

echo "---
layout: page
title: 'platelet-em'
use-site-title: false
---
" > descripthead.html

pandoc platelet-description.md -o description.html

pandoc README.md -o README.html

cat indexhead.html README.html > index.html

cat descripthead.html description.html > platelet-description.html

rm indexhead.html

rm descripthead.html

rm README.html

rm description.html
