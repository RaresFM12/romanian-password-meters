#!/bin/zsh
set -e
cd "$(dirname $0)"
# zxcvbn cores with a fixed reference year and the D variants
YEAR=${1:-2026}
for d in 10000 1000 100 10; do
  dir="vendor/core-D$d"
  rm -rf "$dir"; mkdir -p "$dir"
  cp -R node_modules/@zxcvbn-ts/core/dist/ "$dir/"
  for f in "$dir/data/const.mjs" "$dir/data/const.cjs"; do
    sed -i '' "s/MIN_GUESSES_BEFORE_GROWING_SEQUENCE = 10000/MIN_GUESSES_BEFORE_GROWING_SEQUENCE = $d/" "$f"
    sed -i '' "s/REFERENCE_YEAR = new Date().getFullYear()/REFERENCE_YEAR = $YEAR/" "$f"
    grep -q "MIN_GUESSES_BEFORE_GROWING_SEQUENCE = $d;" "$f" || { echo "D patch failed in $f"; exit 1; }
    grep -q "REFERENCE_YEAR = $YEAR;" "$f" || { echo "year patch failed in $f"; exit 1; }
  done
  echo "built $dir (D=$d, year $YEAR)"
done
rm -rf vendor/zxcvbn-orig
cp -R node_modules/zxcvbn vendor/zxcvbn-orig
sed -i '' "s/REFERENCE_YEAR: new Date().getFullYear()/REFERENCE_YEAR: $YEAR/" vendor/zxcvbn-orig/lib/scoring.js
grep -q "REFERENCE_YEAR: $YEAR," vendor/zxcvbn-orig/lib/scoring.js || { echo "year patch failed (zxcvbn 4.4.2)"; exit 1; }
echo "built vendor/zxcvbn-orig (year $YEAR)"
