// Compatibility re-export for components that import from '../api'.
//
// Many components live under ui/src/components/** and are two levels deep from ui/src.
// Importing '../api' would therefore resolve to ui/src/components/api, not ui/src/api.
// Keeping this file avoids churn and makes those imports resolve correctly.
export * from '../api';
export { api } from '../api';
