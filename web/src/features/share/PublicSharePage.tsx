/**
 * Public, no-auth read-only share page — mounted at /share/:token (see App.tsx),
 * OUTSIDE the authenticated /app shell.
 *
 * Wave 3 (share agent) owns this folder. Replace this stub with the real page:
 * fetch the public schedule + credit balance for the share token (no login),
 * handle expired/revoked tokens gracefully, and never leak other students' data.
 */
export default function PublicSharePage() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FBF8F1',
        color: '#0B463D',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <p style={{ fontWeight: 700 }}>Shared schedule — coming soon.</p>
    </div>
  )
}
