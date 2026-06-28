/**
 * Public, no-auth read-only share page — mounted at /share/:token (see App.tsx),
 * OUTSIDE the authenticated /app shell.
 *
 * Shows one student's upcoming schedule + remaining lesson credits from a share
 * token, with calm CoachOwl branding. Loading / invalid / expired states are all
 * handled; it never renders any app chrome and needs no login.
 */
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  fetchPublicShare,
  ShareError,
  type PublicShare,
  type ShareErrorKind,
} from './api'

// CoachOwl brand palette (matches landing/index.html).
const INK = '#0B463D'
const GREEN = '#0E5A4F'
const ORANGE = '#EE9622'
const CREAM = '#FBF8F1'
const FONT = "'Nunito Sans', system-ui, -apple-system, sans-serif"

type Status =
  | { phase: 'loading' }
  | { phase: 'ready'; data: PublicShare }
  | { phase: 'error'; kind: ShareErrorKind }

export default function PublicSharePage() {
  const { token } = useParams<{ token: string }>()
  const [status, setStatus] = useState<Status>({ phase: 'loading' })

  useEffect(() => {
    if (!token) {
      setStatus({ phase: 'error', kind: 'not_found' })
      return
    }
    const ctrl = new AbortController()
    setStatus({ phase: 'loading' })
    fetchPublicShare(token, ctrl.signal)
      .then((data) => setStatus({ phase: 'ready', data }))
      .catch((err) => {
        if (ctrl.signal.aborted) return
        const kind = err instanceof ShareError ? err.kind : 'not_found'
        setStatus({ phase: 'error', kind })
      })
    return () => ctrl.abort()
  }, [token])

  return (
    <div style={page}>
      <div style={shell}>
        <Brand />
        {status.phase === 'loading' && <Loading />}
        {status.phase === 'error' && <ErrorState kind={status.kind} />}
        {status.phase === 'ready' && <Schedule data={status.data} />}
        <p style={footer}>Powered by CoachOwl · a calm view of your schedule</p>
      </div>
    </div>
  )
}

function Brand() {
  return (
    <div style={brandRow}>
      <svg width="32" height="32" viewBox="0 0 40 40" fill="none" aria-hidden>
        <path d="M10 9 L13 3 L16 11 Z" fill={GREEN} />
        <path d="M30 9 L27 3 L24 11 Z" fill={GREEN} />
        <circle cx="20" cy="23" r="14" fill="#FFF" stroke={GREEN} strokeWidth="2.5" />
        <circle cx="14.5" cy="21" r="4" fill="#FFF" stroke={GREEN} strokeWidth="2" />
        <circle cx="25.5" cy="21" r="4" fill="#FFF" stroke={GREEN} strokeWidth="2" />
        <circle cx="14.5" cy="21" r="1.6" fill={INK} />
        <circle cx="25.5" cy="21" r="1.6" fill={INK} />
        <path d="M18.5 26 L20 28 L21.5 26 Z" fill={ORANGE} />
      </svg>
      <span style={brandName}>CoachOwl</span>
    </div>
  )
}

function Loading() {
  return (
    <div style={centerBox}>
      <span style={spinner} aria-label="Loading" role="status" />
      <p style={{ color: GREEN, marginTop: 14, fontWeight: 600 }}>
        Loading schedule…
      </p>
    </div>
  )
}

const ERROR_COPY: Record<ShareErrorKind, { title: string; body: string }> = {
  expired: {
    title: 'This link has expired',
    body: 'Ask your tutor for a fresh share link to see the latest schedule.',
  },
  not_found: {
    title: 'Link not available',
    body: "This share link is no longer valid. Your tutor can send you a new one.",
  },
  network: {
    title: "Can't load right now",
    body: 'Check your connection and try refreshing the page.',
  },
}

function ErrorState({ kind }: { kind: ShareErrorKind }) {
  const copy = ERROR_COPY[kind]
  return (
    <div style={card}>
      <div style={{ ...centerBox, padding: '20px 8px' }}>
        <div style={emoji}>🦉</div>
        <h1 style={{ ...title, marginTop: 12 }}>{copy.title}</h1>
        <p style={{ ...muted, maxWidth: 320, marginTop: 8 }}>{copy.body}</p>
      </div>
    </div>
  )
}

function Schedule({ data }: { data: PublicShare }) {
  const { studentName, timezone, creditBalance, upcomingLessons } = data
  return (
    <div style={card}>
      <p style={eyebrow}>Schedule for</p>
      <h1 style={title}>{studentName}</h1>

      <div style={balancePill}>
        <span style={{ fontSize: 26, fontWeight: 900, color: GREEN }}>
          {creditBalance}
        </span>
        <span style={{ fontWeight: 700, color: INK }}>
          lesson {creditBalance === 1 ? 'credit' : 'credits'} remaining
        </span>
      </div>

      <h2 style={sectionTitle}>Upcoming lessons</h2>
      {upcomingLessons.length === 0 ? (
        <p style={{ ...muted, marginTop: 4 }}>No upcoming lessons scheduled.</p>
      ) : (
        <ul style={list}>
          {upcomingLessons.map((lesson, i) => (
            <li key={`${lesson.startsAt}-${i}`} style={lessonRow}>
              <div style={dateChip}>
                <span style={dateDay}>{fmtDay(lesson.startsAt, timezone)}</span>
                <span style={dateMonth}>
                  {fmtMonth(lesson.startsAt, timezone)}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={lessonTime}>
                  {fmtWeekday(lesson.startsAt, timezone)} ·{' '}
                  {fmtTime(lesson.startsAt, timezone)}
                  <span style={muted2}> · {lesson.durationMin} min</span>
                </div>
                {lesson.location && (
                  <div style={lessonMeta}>📍 {lesson.location}</div>
                )}
                {lesson.meetingUrl && (
                  <a
                    href={lesson.meetingUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={meetingLink}
                  >
                    Join online ↗
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <p style={tzNote}>Times shown in {timezone.replace(/_/g, ' ')}.</p>
    </div>
  )
}

// --- timezone-aware formatting (render UTC in the org's zone) ---------------
function parts(iso: string, tz: string, opts: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('en-AU', { timeZone: tz, ...opts }).format(
    new Date(iso),
  )
}
const fmtDay = (iso: string, tz: string) => parts(iso, tz, { day: 'numeric' })
const fmtMonth = (iso: string, tz: string) =>
  parts(iso, tz, { month: 'short' }).toUpperCase()
const fmtWeekday = (iso: string, tz: string) =>
  parts(iso, tz, { weekday: 'long' })
const fmtTime = (iso: string, tz: string) =>
  parts(iso, tz, { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase()

// --- inline styles (self-contained; no app chrome / shared ui kit) ----------
const page: React.CSSProperties = {
  minHeight: '100vh',
  background: CREAM,
  fontFamily: FONT,
  color: INK,
  padding: '32px 16px',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'flex-start',
}
const shell: React.CSSProperties = { width: '100%', maxWidth: 480 }
const brandRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  justifyContent: 'center',
  marginBottom: 20,
}
const brandName: React.CSSProperties = {
  fontFamily: "'Nunito', system-ui, sans-serif",
  fontWeight: 900,
  fontSize: 22,
  color: GREEN,
  letterSpacing: '-0.01em',
}
const card: React.CSSProperties = {
  background: '#FFFFFF',
  borderRadius: 20,
  border: '1px solid rgba(14,90,79,0.10)',
  boxShadow: '0 12px 40px rgba(11,70,61,0.08)',
  padding: 24,
}
const eyebrow: React.CSSProperties = {
  margin: 0,
  fontSize: 13,
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'rgba(14,90,79,0.7)',
}
const title: React.CSSProperties = {
  fontFamily: "'Nunito', system-ui, sans-serif",
  margin: '2px 0 0',
  fontSize: 28,
  fontWeight: 900,
  color: INK,
}
const balancePill: React.CSSProperties = {
  marginTop: 16,
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  background: '#F4FAF8',
  border: '1px solid rgba(14,90,79,0.14)',
  borderRadius: 14,
  padding: '12px 16px',
}
const sectionTitle: React.CSSProperties = {
  fontFamily: "'Nunito', system-ui, sans-serif",
  fontSize: 17,
  fontWeight: 800,
  color: INK,
  margin: '24px 0 10px',
}
const list: React.CSSProperties = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}
const lessonRow: React.CSSProperties = {
  display: 'flex',
  gap: 14,
  alignItems: 'center',
  padding: '12px 14px',
  borderRadius: 14,
  border: '1px solid rgba(14,90,79,0.10)',
  background: '#FFFFFF',
}
const dateChip: React.CSSProperties = {
  flexShrink: 0,
  width: 52,
  height: 52,
  borderRadius: 12,
  background: '#FBEBD2',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  lineHeight: 1,
}
const dateDay: React.CSSProperties = { fontSize: 20, fontWeight: 900, color: INK }
const dateMonth: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 800,
  color: ORANGE,
  marginTop: 3,
  letterSpacing: '0.04em',
}
const lessonTime: React.CSSProperties = {
  fontWeight: 700,
  color: INK,
  fontSize: 15,
}
const muted2: React.CSSProperties = { fontWeight: 600, color: 'rgba(11,70,61,0.55)' }
const lessonMeta: React.CSSProperties = {
  marginTop: 4,
  fontSize: 13,
  color: 'rgba(11,70,61,0.7)',
}
const meetingLink: React.CSSProperties = {
  display: 'inline-block',
  marginTop: 5,
  fontSize: 13,
  fontWeight: 700,
  color: GREEN,
  textDecoration: 'none',
}
const muted: React.CSSProperties = {
  color: 'rgba(11,70,61,0.7)',
  fontSize: 15,
  lineHeight: 1.5,
}
const tzNote: React.CSSProperties = {
  marginTop: 18,
  fontSize: 12.5,
  color: 'rgba(11,70,61,0.55)',
}
const centerBox: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
  padding: '32px 0',
}
const emoji: React.CSSProperties = { fontSize: 44 }
const footer: React.CSSProperties = {
  textAlign: 'center',
  marginTop: 20,
  fontSize: 12.5,
  color: 'rgba(11,70,61,0.5)',
}
const spinner: React.CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: '50%',
  border: `3px solid rgba(14,90,79,0.18)`,
  borderTopColor: GREEN,
  display: 'inline-block',
  animation: 'co-share-spin 0.8s linear infinite',
}

// Keyframes for the spinner (injected once; no global stylesheet dependency).
if (
  typeof document !== 'undefined' &&
  !document.getElementById('co-share-spin-kf')
) {
  const style = document.createElement('style')
  style.id = 'co-share-spin-kf'
  style.textContent =
    '@keyframes co-share-spin{to{transform:rotate(360deg)}}'
  document.head.appendChild(style)
}
