/**
 * Tiny class-name combiner. Filters falsy values and joins with a space —
 * enough for conditional Tailwind classes without pulling in a dependency.
 */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
