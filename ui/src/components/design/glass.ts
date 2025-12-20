// Compatibility re-export for components that import from '../design/glass'.
//
// Components under ui/src/components/** commonly use ../design/glass assuming they are
// one directory below ui/src. In practice they are usually two levels below.
// This shim keeps those imports working without weakening TypeScript settings.
export * from '../../design/glass';
export { glass } from '../../design/glass';
