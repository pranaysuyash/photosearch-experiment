# MacBook Pro Notch UI Integration

## Overview

This feature leverages the MacBook Pro's camera notch (and other device notches) to provide a unique, space-efficient UI experience. The app now respects `safe-area-inset-*` environment variables and can render condensed controls directly in the notch area.

## Technical Implementation

### 1. **Viewport Configuration** (`ui/index.html`)

```html
<meta
  name="viewport"
  content="width=device-width, initial-scale=1.0, viewport-fit=cover"
/>
```

- `viewport-fit=cover`: Enables the browser to use the full viewport, including the notch area
- On Safari macOS, this activates `safe-area-inset-*` CSS environment variables

### 2. **CSS Safe Area Insets** (`ui/src/index.css`)

```css
--safe-area-inset-top: env(safe-area-inset-top, 0px);
--safe-area-inset-right: env(safe-area-inset-right, 0px);
--safe-area-inset-left: env(safe-area-inset-left, 0px);
--safe-area-inset-bottom: env(safe-area-inset-bottom, 0px);
```

- Exposes environment variables as CSS custom properties
- Fallback: `0px` on devices without notch

### 3. **React Hook: `useNotch`** (`ui/src/hooks/useNotch.ts`)

```tsx
const { hasNotch, topInset, rightInset, leftInset, bottomInset } = useNotch();
```

- Detects notch presence and inset sizes
- Monitors viewport resize/orientation changes
- Returns `NotchInfo` interface with inset values in pixels

### 4. **Notch Bar Component** (`ui/src/components/layout/NotchBar.tsx`)

```tsx
<NotchBar show={true}>{/* Condensed controls here */}</NotchBar>
```

- Renders in notch area on compatible devices
- Fallback bar for non-notch devices
- Framer Motion animations for smooth appearance

## Usage Example

```tsx
import { useNotch } from '../hooks/useNotch';
import { NotchBar } from './components/layout/NotchBar';

export function MyComponent() {
  const { hasNotch, topInset } = useNotch();

  return (
    <>
      <NotchBar show={hasNotch}>
        <div>Compact Search</div>
        <div>Status</div>
      </NotchBar>
      <main style={{ marginTop: topInset }}>{/* Main content */}</main>
    </>
  );
}
```

## Device Compatibility

| Device                   | Support     | Method                                     |
| ------------------------ | ----------- | ------------------------------------------ |
| **MacBook Pro (Safari)** | ✅ Full     | `safe-area-inset-*` (native)               |
| **iPhone/iPad**          | ✅ Full     | `safe-area-inset-*` (native)               |
| **Desktop (no notch)**   | ✅ Fallback | Linear bar at top                          |
| **Android Chrome**       | ⚠️ Partial  | CSS environment variables (newer versions) |
| **Firefox**              | ❌ Limited  | No `safe-area-inset` support yet           |

## Design Considerations

### Pros

- **Screen Real Estate**: Use otherwise-unused notch area
- **Native Feel**: Matches Apple's design language
- **Responsive**: Auto-adapts to notch size
- **Non-intrusive**: Compact controls, minimal chrome

### Cons

- **Limited to macOS Safari**: Primarily a macOS/iOS feature
- **Content Placement**: Must avoid center (where camera is)
- **Testing**: Difficult to test on non-notch devices

## Future Enhancements

1. **Notch-Aware Layout**

   - Detect left/right notches
   - Position secondary controls accordingly
   - Avoid overlapping content

2. **Themable Notch Bar**

   - Custom background opacity
   - Dynamic color based on ambient theme
   - Animation timing

3. **Safe Area Utilities**
   - Tailwind plugins for `safe-area-inset-*`
   - Utility classes: `pt-safe`, `pr-safe`, `pb-safe`, `pl-safe`

## Testing

### On macOS Safari

```bash
# Enable Web Inspector
# 1. Safari → Preferences → Advanced → Show Develop menu
# 2. Develop → Enter Responsive Design Mode
# 3. Set device to "MacBook Pro 14-inch"
# 4. Open browser DevTools and check computed environment variables
```

### Programmatic Check

```tsx
const topInset = parseInt(
  getComputedStyle(document.documentElement).getPropertyValue(
    '--safe-area-inset-top'
  )
);
console.log('Notch top inset:', topInset, 'px');
```

## References

- [MDN: env() - CSS Functions](https://developer.mozilla.org/en-US/docs/Web/CSS/env)
- [WebKit Blog: The Notch and Viewport-fit=cover](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [Apple Human Interface Guidelines: Notch](https://developer.apple.com/design/human-interface-guidelines/ios/visual-design/notch/)
