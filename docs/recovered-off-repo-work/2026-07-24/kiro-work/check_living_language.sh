#!/bin/sh
# Living language pre-commit helper
#
# Intent: flag "AI ..." phrasing ONLY when it appears in user-visible UI copy.
# We deliberately do NOT scan:
# - identifiers / variable names
# - API paths (e.g. /ai/insights)
# - comments
# - console/logger strings
# - server internals or docs
#
# Heuristic approach (fast, no AST):
# - Only scan staged files under ui/src with .tsx/.ts
# - Only scan JSX text nodes and common UI-facing props/fields (title/label/etc)

STAGED_FILES=$(git diff --cached --name-only -- 'ui/src' | grep -E "\.(tsx|ts)$" || true)
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

  # Drop obvious comments and log strings (not user-facing UI copy)
  ADDED=$(printf "%s\n" "$ADDED" | \
    grep -v -E '^[[:space:]]*//' | \
    grep -v -E '^[[:space:]]*/\*' | \
    grep -v -E '^[[:space:]]*\*' | \
    grep -v -E 'console\.(log|debug|info|warn|error)\s*\(' | \
    grep -v -E '\b(logger|logging)\b' \
    || true)
  if [ -z "$ADDED" ]; then
    continue
  fi

  # Match set: "AI", "AI-powered", "AI driven", "AI analysis", "AI detected", etc.
  # (We keep it broad, but only apply it to user-visible locations.)
  AI_RE='\\bAI(?:[- ]?(?:powered|driven|assisted|generated|detected|analysis))?\\b'

  # 1) JSX text nodes (between > and <)
  echo "$ADDED" | AI_RE="$AI_RE" perl -0777 -ne '
    my $ai = qr/$ENV{AI_RE}/i;
    exit((/>[^<]*$ai[^<]*</s) ? 0 : 1);
  ' >/dev/null 2>&1 && FOUND=1

  # 2) Common UI-facing JSX props and object fields
  #    Examples: title="...", aria-label='...', placeholder=`...`
  #              { label: "...", description: "..." }
  echo "$ADDED" | AI_RE="$AI_RE" perl -0777 -ne '
    my $ai = qr/$ENV{AI_RE}/i;
    my $keys = qr/(?:title|label|description|subtitle|placeholder|alt|aria-label|ariaLabel|tooltip|helperText|helpText|message|text)/i;
    exit((/\b$keys\b\s*(?:=|:)\s*(?:"[^"\n]*$ai[^"\n]*"|'"'"'[^'"'"'\n]*$ai[^'"'"'\n]*'"'"'|`[^`\n]*$ai[^`\n]*`)/s) ? 0 : 1);
  ' >/dev/null 2>&1 && FOUND=1

done

if [ "$FOUND" -eq 1 ]; then
  echo "❌ Found 'AI ...' terminology in user-visible UI copy. Please use living language instead (e.g., 'We detected', 'We found', 'Smart suggestions')."
  echo "Run .kiro/scripts/check_living_language.sh --fix or update strings to living-language variants."
  exit 1
fi

exit 0
