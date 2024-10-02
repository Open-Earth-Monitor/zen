#!/bin/bash
[ ! -d "docs" ] && mkdir "docs"
pip install -e .
make clean
make html
rm -fr docs/*
cp -r sphinx/_build/html/* docs/
[ ! -f "docs/.nojekyll" ] && touch "docs/.nojekyll"
git add docs
git commit -m "Documentation deployment"
