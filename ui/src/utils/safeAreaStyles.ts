/**
 * Safe Area CSS Utilities
 *
 * Tailwind-like utilities for safe-area-inset padding.
 * Works across all browsers by using CSS custom properties.
 */

export const SafeAreaStyles = {
  /**
   * Padding utilities using safe areas
   * Usage: className={SafeAreaStyles.ptSafe}
   */
  ptSafe: 'pt-[calc(1rem_+_var(--safe-area-inset-top))]',
  prSafe: 'pr-[calc(1rem_+_var(--safe-area-inset-right))]',
  pbSafe: 'pb-[calc(1rem_+_var(--safe-area-inset-bottom))]',
  plSafe: 'pl-[calc(1rem_+_var(--safe-area-inset-left))]',
  pSafe:
    'pt-[max(1rem,var(--safe-area-inset-top))] pr-[max(1rem,var(--safe-area-inset-right))] pb-[max(1rem,var(--safe-area-inset-bottom))] pl-[max(1rem,var(--safe-area-inset-left))]',

  /**
   * Margin utilities
   */
  mtSafe: 'mt-[calc(1rem_+_var(--safe-area-inset-top))]',
  mrSafe: 'mr-[calc(1rem_+_var(--safe-area-inset-right))]',
  mbSafe: 'mb-[calc(1rem_+_var(--safe-area-inset-bottom))]',
  mlSafe: 'ml-[calc(1rem_+_var(--safe-area-inset-left))]',

  /**
   * Position utilities for fixed/absolute elements
   */
  topSafe: 'top-[var(--safe-area-inset-top)]',
  rightSafe: 'right-[var(--safe-area-inset-right)]',
  bottomSafe: 'bottom-[var(--safe-area-inset-bottom)]',
  leftSafe: 'left-[var(--safe-area-inset-left)]',
} as const;

/**
 * CSS class string generator for safe area utilities
 * Usage: getSafeAreaClass('pt', 'pr') -> 'pt-safe pr-safe'
 */
export function getSafeAreaClass(
  ...sides: (
    | 'p'
    | 'pt'
    | 'pr'
    | 'pb'
    | 'pl'
    | 'm'
    | 'mt'
    | 'mr'
    | 'mb'
    | 'ml'
  )[]
): string {
  return sides
    .map((side) => {
      const key = `${side}Safe` as keyof typeof SafeAreaStyles;
      return SafeAreaStyles[key] || '';
    })
    .filter(Boolean)
    .join(' ');
}
