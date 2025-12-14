# Glass Design System

This directory contains the centralized design tokens for the application's glassmorphism style.

## Usage

Import the `glass` object from `./glass.ts` and use the properties in your `className` definitions.

```typescript
import { glass } from 'ui/src/design/glass';

function MyComponent() {
  return (
    <div className={`${glass.surface} p-4 rounded-xl`}>
      <h1 className="text-xl">Title</h1>
      <button className={glass.buttonPrimary}>Action</button>
    </div>
  );
}
```

## Tokens

- **`glass.surface`**: Standard glass background. Used for cards, panels, and floating elements.
- **`glass.surfaceStrong`**: darker/more opaque glass. Used for dropdowns, modals, or active states.
- **`glass.button`**: Standard glass button.
- **`glass.buttonPrimary`**: Primary action button with glass effect.
- **`glass.buttonDanger`**: Destructive action button.
- **`glass.buttonMuted`**: Subtle/Ghost button.
