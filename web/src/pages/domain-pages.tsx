import { ComingSoonPage } from '@/pages/ComingSoonPage'

// Wave-2 domain placeholders. Real implementations replace these behind the
// same routes (see App.tsx). Frontend agents: build your feature here.

export function StudentsPage() {
  return (
    <ComingSoonPage
      title="Students"
      description="Your roster — names, subjects, contacts and credits."
      blurb="Smart Import and student profiles are on the way. Soon you'll add students, track their lesson credits, and keep guardian details tidy — all in one calm list."
    />
  )
}

export function CalendarPage() {
  return (
    <ComingSoonPage
      title="Calendar"
      description="Weekly and monthly views of every lesson."
      blurb="Recurring lessons, drag-to-reschedule and conflict detection are coming next. Set a weekly slot once and CoachOwl keeps everyone in sync."
    />
  )
}

export function PaymentsPage() {
  return (
    <ComingSoonPage
      title="Payments"
      description="Income, lesson packs and AUD invoices with GST."
      blurb="Record payments, sell lesson packs, and generate tidy AUD invoices with GST handled — ready when tax time comes."
    />
  )
}
