import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import { defineConfig, globalIgnores } from 'eslint/config';

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { 'jsx-a11y': jsxA11y },
    rules: {
      ...jsxA11y.configs.recommended.rules,
      // Static divs/spans with onClick are legacy patterns still being
      // migrated; surface them without failing CI.
      'jsx-a11y/no-static-element-interactions': 'warn',
      'jsx-a11y/no-noninteractive-element-interactions': 'warn',
      'jsx-a11y/click-events-have-key-events': 'warn',
      'jsx-a11y/mouse-events-have-key-events': 'warn',
      // Autofocus in intentionally-focused overlays (command palette,
      // search notch, modal first field) is a deliberate pattern here.
      'jsx-a11y/no-autofocus': 'off',
      // Real gap, but a real fix needs caption assets for user videos —
      // surfaced as warning until captions exist.
      'jsx-a11y/media-has-caption': 'warn',
    },
  },
  {
    // Transport boundary: every API call goes through src/api.ts (axios client,
    // apiFetch, mediaUrl) so base URL, identity, and auth are applied once.
    // Same-origin `fetch('/api/…')` only works behind the Vite dev proxy and
    // is dead inside the Tauri shell; inline host literals fork the config.
    files: ['src/**/*.{ts,tsx}'],
    ignores: ['src/api.ts', 'src/platform/**', 'src/test/**', 'src/**/*.test.*'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "CallExpression[callee.name='fetch'] > Literal.arguments:first-child[value=/^\\x2fapi\\x2f/]",
          message:
            'Use apiFetch() from src/api.ts — raw fetch("/api/…") bypasses base URL, identity, and auth.',
        },
        {
          selector:
            "CallExpression[callee.name='fetch'] > TemplateLiteral.arguments:first-child > TemplateElement:first-child[value.raw=/^\\x2fapi\\x2f/]",
          message:
            'Use apiFetch() from src/api.ts — raw fetch(`/api/…`) bypasses base URL, identity, and auth.',
        },
        {
          selector: "MemberExpression[property.name='VITE_API_URL']",
          message:
            'Read API_BASE / apiUrl() from src/api.ts instead of import.meta.env.VITE_API_URL.',
        },
        {
          selector:
            'Literal[value=/(localhost|127\\.0\\.0\\.1):8000/], TemplateElement[value.raw=/(localhost|127\\.0\\.0\\.1):8000/]',
          message:
            'No inline API host literals — use API_BASE / apiUrl() / mediaUrl from src/api.ts.',
        },
      ],
    },
  },
]);
