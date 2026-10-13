# Universal Safe Area UI Integration

## Overview

This feature provides **cross-browser safe area detection** for notches, device edges, and browser chrome. It works everywhere with intelligent fallbacks:

- ✅ **Native support** (Safari macOS/iOS, Chrome Android) via CSS `env(safe-area-inset-*)`
- ✅ **Browser detection** (Firefox, Edge, desktop browsers) via viewport calculations
- ✅ **Graceful fallback** on any browser

## Technical Stack

### 1. CSS Custom Properties

```css
/* Automatically falls back to browser defaults */
--safe-area-inset-top: env(safe-area-inset-top, 0px);
--safe-area-inset-right: env(safe-area-inset-right, 0px);
--safe-area-inset-left: env(safe-area-inset-left, 0px);
--safe-area-inset-bottom: env(safe-area-inset-bottom, 0px);
```

### 2. Three-Tier Detection (`useNotch()` Hook)

Priority order:

1. **Method: `env`** — CSS environment variables (most reliable)
   - Safari macOS/iOS, Chrome Android
2. **Method: `detected`** — Browser UI detection
   - Estimates from `window.outerHeight - window.innerHeight`
   - Detects address bars, toolbars, status bars
   - Works: Firefox, Edge, Chrome, Safari
3. **Method: `fallback`** — No safe areas detected
   - Standard viewport

```tsx
const { hasNotch, topInset, method } = useNotch();
// method: 'env' | 'detected' | 'fallback'
```

### 3. Components

**NotchBar** — Renders condensed controls in safe areas

```tsx
<NotchBar show={true} compact={false}>
  <SearchInput />
  <StatusBadge />
</NotchBar>
```

**SafeAreaStyles** — Utility helpers for padding/margin

```tsx
import { getSafeAreaClass } from '../utils/safeAreaStyles';
<div className={getSafeAreaClass('pt', 'pl')}>Content</div>;
```

## Browser Support Matrix

| Browser        | Platform    | Support     | Method   |
| -------------- | ----------- | ----------- | -------- |
| Safari         | macOS 11+   | ✅ Full     | `env()`  |
| Safari         | iOS 15+     | ✅ Full     | `env()`  |
| Chrome         | Android 12+ | ✅ Full     | `env()`  |
| Chrome         | Desktop     | ✅ Good     | Detected |
| Firefox        | Desktop     | ✅ Good     | Detected |
| Edge           | Desktop     | ✅ Good     | Detected |
| Older browsers | Any         | ✅ Fallback | None     |

## Usage

### Basic: Add Notch Bar to Layout

```tsx
import { NotchBar } from './components/layout/NotchBar';

export function Layout() {
  return (
    <>
      <NotchBar show={true}>
        <LogoArea />
        <ActionButtons />
      </NotchBar>
      <main className='pt-12'>{/* content */}</main>
    </>
  );
}
```

### Advanced: Responsive Safe Area Padding

```tsx
import { getSafeAreaClass } from '../utils/safeAreaStyles';

export function ContentArea() {
  return (
    <div className={getSafeAreaClass('pt', 'pr', 'pl')}>
      Auto-respects notches on all browsers
    </div>
  );
}
```

### CSS: Direct Custom Properties

```css
.header {
  padding-top: calc(1rem + var(--safe-area-inset-top));
  padding-left: max(1rem, var(--safe-area-inset-left));
  padding-right: max(1rem, var(--safe-area-inset-right));
}
```

## Key Features

- **Universal**: Works on Safari, Chrome, Firefox, Edge, mobile, desktop
- **Intelligent**: Detects best method available for each browser
- **Zero Config**: Automatically picks up notches/safe areas
- **Progressive**: Gracefully degrades on unsupported browsers
- **Lightweight**: ~2KB hook + component, no external deps
- **Dev-Friendly**: Easy to debug detection method

## Testing

### Check Detection Method

```tsx
const { hasNotch, topInset, method } = useNotch();
console.log(`Method: ${method}, Inset: ${topInset}px`);
```

### Programmatic CSS Check

```ts
const style = getComputedStyle(document.documentElement);
const top = style.getPropertyValue('--safe-area-inset-top');
console.log(`Top inset: ${top}`);
```

### Browser DevTools

- Inspect element → Computed → filter for `--safe-area-inset-*`
- Values show actual pixel insets detected

## Implementation Files

- `ui/src/hooks/useNotch.ts` — Detection hook
- `ui/src/components/layout/NotchBar.tsx` — Notch bar component
- `ui/src/utils/safeAreaStyles.ts` — Utility helpers
- `ui/src/index.css` — CSS custom properties
- `ui/index.html` — Viewport meta tag

## Future Ideas

1. **Dynamic positioning** for left/right notches
2. **Animation config** for different detection methods
3. **A/B testing** to track safe area usage
4. **Performance mode** to reduce detection frequency
5. **Custom theming** per detection method
