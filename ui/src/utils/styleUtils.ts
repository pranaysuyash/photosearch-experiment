export function percentToClass(prefix: string, value: number, step = 10) {
  const clamped = Math.max(0, Math.min(100, Math.round(value * 100)));
  const rounded = Math.round(clamped / step) * step;
  return `${prefix}-${rounded}`;
}
