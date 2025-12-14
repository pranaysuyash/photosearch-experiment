export const glass = {
  surface: 'glass-surface',
  surfaceStrong: 'glass-surface glass-surface--strong',
  button: 'btn-glass',
  buttonPrimary: 'btn-glass btn-glass--primary',
  buttonDanger: 'btn-glass btn-glass--danger',
  buttonMuted: 'btn-glass btn-glass--muted',
} as const;

export type GlassVariant = keyof typeof glass;
