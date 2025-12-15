# Living Application Language Guidelines

## Purpose
Maintain consistent "living app" language throughout the codebase to create a more natural, human-centered user experience.

## Language Replacements

### User-Facing Strings (CRITICAL - Never revert these)

#### Search & Analysis
- ❌ "AI detected" → ✅ "We detected" / "We found"
- ❌ "AI identified" → ✅ "We identified" / "We discovered"
- ❌ "AI-powered content understanding" → ✅ "We understand your content visually"
- ❌ "Combined metadata + AI analysis" → ✅ "We combined file details with visual understanding"
- ❌ "AI processing" → ✅ "We're analyzing" / "Processing"
- ❌ "AI model" → ✅ "Our analysis engine" / "Our understanding system"

#### Comments & Internal Documentation
- ❌ "AI-detected concepts" → ✅ "We identify visual concepts"
- ❌ "AI model analysis" → ✅ "Our analysis engine processing"

## Protected Files
These files contain living language and should be carefully reviewed before any bulk changes:

### Frontend Components
- `ui/src/components/search/MatchExplanation.tsx` (Lines 297-299)
- `ui/src/components/search/EnhancedSearchUI.tsx`
- `ui/src/components/search/IntentRecognition.tsx`

### Backend Files
- `server/main.py` (Line 963 and similar comments)

## Prevention Strategy

### Before Making Changes
1. **Search for AI terminology**: `git grep -i "AI.*detected\|AI.*powered\|AI.*analysis" -- "*.tsx" "*.ts" "*.py"`
2. **Check protected files**: Review the files listed above
3. **Verify living language**: Ensure user-facing strings use "we" language

### During Code Reviews
1. **Flag AI terminology**: Any PR introducing "AI detected", "AI powered", etc. in user-facing strings
2. **Require justification**: Technical documentation may use AI terminology, but UI strings should not
3. **Test user experience**: Ensure the language feels natural and human-centered

### Git Hooks (Recommended)
Create a pre-commit hook to catch AI terminology in user-facing files:

```bash
#!/bin/sh
# Check for AI terminology in user-facing files
if git diff --cached --name-only | grep -E "\.(tsx|ts)$" | xargs git diff --cached | grep -i "AI.*detected\|AI.*powered\|AI.*analysis"; then
    echo "❌ Found AI terminology in user-facing code. Please use living language instead."
    echo "See .kiro/steering/living-language.md for guidelines"
    exit 1
fi
```

## Root Cause Analysis

The terminology was likely overwritten due to:
1. **Bulk refactoring**: Large commits that touched many files simultaneously
2. **Missing documentation**: No clear guidelines on which strings to preserve
3. **No protection mechanism**: No automated checks to prevent regression

## Implementation Status
- ✅ `ui/src/components/search/MatchExplanation.tsx` - Fixed (Dec 15, 2025)
- ✅ `server/main.py` - Fixed (Dec 15, 2025)
- ✅ `ui/src/pages/About.tsx` - Fixed (Dec 15, 2025)
- ✅ `ui/src/components/search/EnhancedSearchUI.tsx` - Variable names updated (Dec 15, 2025)
- ✅ **Git Hook**: Pre-commit hook installed to prevent future regressions
- ✅ **Documentation**: Living language guidelines established