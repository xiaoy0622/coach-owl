// Small display helpers for the notes feature. The backend serves UTC instants;
// we render them in the org timezone (DST-correct) via Intl.

export function formatLessonTime(iso: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat('en-AU', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      hour: 'numeric',
      minute: '2-digit',
      timeZone: timezone,
    }).format(new Date(iso))
  } catch {
    return new Date(iso).toLocaleString('en-AU')
  }
}

export function formatDate(iso: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat('en-AU', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      timeZone: timezone,
    }).format(new Date(iso))
  } catch {
    return new Date(iso).toLocaleDateString('en-AU')
  }
}
