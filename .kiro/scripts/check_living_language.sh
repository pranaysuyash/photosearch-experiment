#!/bin/sh
# Living language pre-commit helper
# Scans staged .tsx/.ts/.md/.mdx files and only flags occurrences of
# `AI powered`, `AI detected`, or `AI analysis` when they appear inside
# string literals (", ', `) or JSX text nodes (between > and <).
# This avoids matching code identifiers, API paths, or variable names.

STAGED_FILES=$(git diff --cached --name-only | grep -E "\.(tsx|ts|md|mdx)$" || true)
if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

FOUND=0

for f in $STAGED_FILES; do
  # Collect added lines (strip leading '+')
  ADDED=$(git diff --cached -U0 -- "$f" | sed -n 's/^+//p')
  if [ -z "$ADDED" ]; then
    continue
  fi

  # Check for matches inside quoted string literals (single/double/backtick)
  echo "$ADDED" | perl -0777 -ne '
    if (/(?:"|`|'"'"')(?:.*?\bAI(?:[- ]?(?:powered|detected|analysis))\b.*?)(?:"|`|'"'"')/is) { print "STR_MATCH\n"; }
  ' >/dev/null 2>&1 && FOUND=1

  # Check for matches inside JSX text nodes (between > and <)
  echo "$ADDED" | perl -0777 -ne '
    if (/>[^<]*\bAI(?:[- ]?(?:powered|detected|analysis))\b[^<]*</is) { print "JSX_MATCH\n"; }
  ' >/dev/null 2>&1 && FOUND=1

done

if [ "$FOUND" -eq 1 ]; then
  echo "❌ Found AI terminology in user-visible strings. Please use living language instead (e.g., 'We detected', 'We found')."
  echo "Run .kiro/scripts/check_living_language.sh --fix or update strings to living-language variants."
  exit 1
fi

exit 0
