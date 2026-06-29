# Email Deliverability Runbook (CO-N03)

Operational runbook for getting CoachOwl's transactional email into the **inbox**,
not spam. Covers SPF, DKIM, DMARC setup for the sending domain and a one-time
verification procedure that satisfies the plan AC
*"测试邮件不进垃圾箱（人工验一次）"* (CO-N03).

> **Provider:** CoachOwl sends via **Resend** by default, with **AWS SES** as an
> alternative behind the same `EmailAdapter` interface
> (`api/app/notifications/adapters/base.py`; provider choice noted in
> `CoachOwl-Execution-Plan-v0.md` §2 and CO-N02). The DNS work below is the same
> in spirit for either provider; the exact records differ and are called out.

---

## Why this matters

- Email is the **only delivery channel in the MVP** (the notifications outbox has
  a single `email` channel — see `api/app/notifications/dispatcher.py`).
- Without SPF/DKIM/DMARC authentication, mailbox providers (Gmail, Outlook,
  Yahoo) silently route transactional mail to **Junk** — class‑lesson reminders,
  low‑balance alerts and invoices never get seen.
- This is logged as a Top risk: *"邮件进垃圾箱 → MVP 唯一触达通道失效"*
  (`CoachOwl-Execution-Plan-v0.md` §1.5). Do it **early and verify once**.

---

## Quick checklist (do these in order)

- [ ] Pick the **sending domain/subdomain** (recommended: `send.<your-domain>`).
- [ ] Add the domain in the **Resend dashboard** (or SES console).
- [ ] Add the **SPF** TXT record provided by the provider.
- [ ] Add the **DKIM** CNAME/TXT records provided by the provider.
- [ ] Add a **DMARC** `_dmarc` TXT record (`p=none` to start) with a `rua` address.
- [ ] Wait for DNS propagation; click **Verify** in the dashboard.
- [ ] Run the **`dig` checks** below — all three resolve.
- [ ] Send a **test email**; confirm **SPF=pass, DKIM=pass, DMARC=pass** via
      Gmail "Show original" and/or mail-tester.com (target 10/10).
- [ ] Set `email_from` to an address **on the verified domain**.
- [ ] Begin sending at **low volume**; watch bounces/complaints and DMARC reports.
- [ ] After 1–2 weeks of clean reports, ramp DMARC to `p=quarantine`.

---

## 0. Choose the sending domain

Use a **dedicated subdomain** for application mail, e.g. `send.coachowl.com.au` or
`mail.coachowl.com.au`, rather than the root domain. Why:

- Keeps your transactional sending reputation **isolated** from the root domain
  (which may also send marketing or be used for staff Google Workspace mail).
- A reputation problem on one subdomain doesn't poison the others.
- The `From:` address then looks like
  `CoachOwl <notifications@send.coachowl.com.au>`.

DMARC alignment still works: a DMARC policy on the **organizational domain**
(`_dmarc.coachowl.com.au`) covers subdomains, and a From of
`@send.coachowl.com.au` aligns with SPF/DKIM published on that same subdomain.

> Throughout this doc, `<your-domain>` = your organizational domain (e.g.
> `coachowl.com.au`) and `<send-subdomain>` = the sending subdomain (e.g.
> `send.coachowl.com.au`). Replace **all** placeholders before publishing records.

---

## 1. DNS records to add

All records go in the DNS zone for `<your-domain>`. Tables use
**Host/Name | Type | Value | TTL**. The Host column shows the record name as most
DNS UIs expect it (relative to the zone, or `@` for the apex). **Placeholders are
marked with `<…>`** and must be filled from the provider dashboard.

### 1a. SPF (Sender Policy Framework)

SPF authorizes which servers may send mail using your domain in the bounce
(Return-Path / envelope-from) address. It's a single TXT record on the sending
(sub)domain.

**Resend** — publish SPF on the sending subdomain:

| Host / Name                | Type | Value                                  | TTL  |
| -------------------------- | ---- | -------------------------------------- | ---- |
| `send` (= `<send-subdomain>`) | TXT  | `v=spf1 include:amazonses.com ~all`    | 3600 |

> Resend sends through Amazon SES infrastructure, so the SPF include is
> `amazonses.com`. **Verify the exact `include:` value shown in the Resend
> dashboard** for your domain — Resend displays the precise SPF record to copy,
> and it may differ by region/account.

**AWS SES (direct) variant** — SES uses its own MAIL FROM subdomain. If you
configure a custom MAIL FROM (recommended for alignment), SES asks you to publish:

| Host / Name                  | Type | Value                              | TTL  |
| ---------------------------- | ---- | ---------------------------------- | ---- |
| `<mail-from-subdomain>`      | TXT  | `v=spf1 include:amazonses.com ~all`| 3600 |
| `<mail-from-subdomain>`      | MX   | `10 feedback-smtp.<region>.amazonses.com` | 3600 |

(`<region>` e.g. `ap-southeast-2` for Sydney. **Confirm the exact MX/region in the
SES console.**)

**SPF rules that bite people:**

- **One SPF record per domain name only.** Two separate `v=spf1 …` TXT records on
  the same name = a permanent SPF error and you fail SPF. If the name already has
  an SPF record (e.g. for Google Workspace), **merge the includes into one
  record**, don't add a second.
- **The 10 DNS-lookup limit.** Each `include:`, `a`, `mx`, `ptr`, `exists`
  mechanism costs a DNS lookup; **more than 10 total → `permerror` → SPF fails.**
  Keep the record lean; don't chain many includes. One `include:amazonses.com`
  is well within budget.
- **Use `~all` (softfail) initially**, not `-all` (hardfail). Move to `-all` only
  after you're confident every legitimate sender for that name is covered.
- SPF alone is **not** enough — it breaks on forwarding. DKIM + DMARC are what
  actually keep you out of spam.

### 1b. DKIM (DomainKeys Identified Mail)

DKIM cryptographically signs each message; the receiver verifies the signature
against a public key published in your DNS. This survives forwarding and is the
strongest of the three signals.

**You do not invent these values.** When you add the domain in the **Resend
dashboard**, Resend generates the DKIM key(s) and shows you the exact records to
add — typically **three CNAME records** (Resend/SES-style rotating keys) or a
single TXT public key. Add them verbatim:

| Host / Name                                   | Type  | Value                                              | TTL  |
| --------------------------------------------- | ----- | -------------------------------------------------- | ---- |
| `<resend-dkim-token-1>._domainkey`            | CNAME | `<resend-dkim-token-1>.dkim.amazonses.com`         | 3600 |
| `<resend-dkim-token-2>._domainkey`            | CNAME | `<resend-dkim-token-2>.dkim.amazonses.com`         | 3600 |
| `<resend-dkim-token-3>._domainkey`            | CNAME | `<resend-dkim-token-3>.dkim.amazonses.com`         | 3600 |

> The `<resend-dkim-token-N>` strings are **placeholders** — copy the real tokens
> from the Resend dashboard. **Verify the exact host names and targets in the
> dashboard**; some Resend setups instead give a single
> `resend._domainkey` **TXT** record containing `p=<base64 public key>`. Use
> whatever the dashboard shows.

**AWS SES (direct) variant:** SES "Easy DKIM" generates **three CNAME records**
of the form `<token>._domainkey.<your-domain> → <token>.dkim.amazonses.com`.
Add all three; SES verifies and signs automatically.

**Key rotation:** the provider rotates DKIM keys periodically. With the
CNAME-based setup (Resend/SES Easy DKIM), rotation is **automatic** — the CNAME
points at the provider, who swaps the underlying key; you do nothing. If you ever
publish a **raw TXT public key**, you own rotation: generate a new selector,
publish it, switch sending to it, then remove the old selector after the old key's
last mail has cleared. Never delete a selector that recent mail may still be
verified against.

### 1c. DMARC (Domain-based Message Authentication, Reporting & Conformance)

DMARC tells receivers what to do when a message **fails both** SPF and DKIM
alignment, and gives you reporting. One TXT record at `_dmarc.<your-domain>`
(the **organizational** domain — it covers subdomains).

**Starter record (safe, report-only):**

| Host / Name                | Type | Value                                                                                          | TTL  |
| -------------------------- | ---- | ---------------------------------------------------------------------------------------------- | ---- |
| `_dmarc`                   | TXT  | `v=DMARC1; p=none; rua=mailto:dmarc-reports@<your-domain>; ruf=mailto:dmarc-reports@<your-domain>; fo=1; adkim=s; aspf=s` | 3600 |

Tag meanings:

- `p=none` — **monitor only**, take no action. Start here so you can see reports
  without risking legitimate mail being junked.
- `rua=mailto:…` — where **aggregate** (daily XML) reports are sent. Use a real,
  monitored mailbox (or a DMARC-report service). **Required to learn anything.**
- `ruf=mailto:…` — optional **forensic/failure** reports (many receivers don't
  send these; fine to omit).
- `fo=1` — request a failure report whenever **any** mechanism fails.
- `adkim=s`, `aspf=s` — **strict** alignment. Start strict only if your From and
  signing domains match exactly; if you hit alignment trouble, relax to
  `adkim=r; aspf=r` (relaxed, the default), which allows subdomain alignment.

**Alignment — the concept that makes DMARC pass:** DMARC requires that SPF **or**
DKIM not only *pass*, but **align** with the domain in the visible `From:` header.

- **DKIM alignment:** the `d=` domain in the DKIM signature matches (or is a
  parent of, under relaxed) the From domain.
- **SPF alignment:** the Return-Path (envelope-from) domain matches the From
  domain.
- So if you send `From: notifications@send.coachowl.com.au`, you need DKIM signed
  by `send.coachowl.com.au` (or `coachowl.com.au` under relaxed) **and/or** the
  envelope-from on the same domain. Using your provider's shared/sandbox domain in
  the From (e.g. `onboarding@resend.dev`) will **never align** — always send from
  your **verified own domain**.

**Ramp plan:** run `p=none` for **1–2 weeks**, read the aggregate reports, confirm
100% of your legitimate mail passes with alignment, then tighten:

```
p=none   →   p=quarantine; pct=25   →   p=quarantine   →   p=reject
```

(`pct=` lets you apply the policy to a fraction first.) `p=reject` is the end goal
and is what Gmail/Yahoo expect of established senders.

---

## 2. Provider setup steps

### Resend (default)

1. Log in to the **Resend dashboard** → **Domains** → **Add Domain**.
2. Enter the **sending subdomain** (e.g. `send.coachowl.com.au`). Pick the region
   closest to your users (e.g. an AP region for AU).
3. Resend shows the exact **SPF (TXT)** and **DKIM (CNAME/TXT)** records — copy
   each into your DNS provider's zone for `<your-domain>` (§1a, §1b).
4. Add your **DMARC** record separately at `_dmarc.<your-domain>` (§1c) — Resend
   may surface a recommended DMARC entry too.
5. Wait for DNS propagation (minutes to a few hours), then click **Verify** in
   Resend. Status should go **Verified**.
6. Create an **API key** (Resend → API Keys). Store it as the app's Resend secret
   (server-only env; see "App config" below).
7. Set the app's **From address** to an address on the verified domain, e.g.
   `CoachOwl <notifications@send.coachowl.com.au>`.
8. Send a test (§3) before relying on it.

### AWS SES (alternative, same adapter)

1. SES console → **Verified identities** → **Create identity** → **Domain**;
   enter `<send-subdomain>`.
2. Enable **Easy DKIM** (RSA 2048) — SES generates the **3 DKIM CNAMEs**; add them.
3. Configure a **custom MAIL FROM** subdomain for SPF alignment; add the **TXT +
   MX** records SES shows (§1a SES variant).
4. Add the **DMARC** record (§1c).
5. Wait for SES to mark the identity **Verified** and DKIM **Successful**.
6. **Request production access** (move out of the SES sandbox) before sending to
   arbitrary recipients — in sandbox you can only send to verified addresses.
7. Point the `EmailAdapter` at the SES adapter; set the same From address.

> The application talks to **one** `EmailAdapter`; switching Resend↔SES is a
> config/adapter swap with no business-logic change
> (`api/app/notifications/adapters/registry.py`).

### App config (where the From address & provider keys live)

Application settings are defined in **`api/app/core/config.py`** (pydantic-settings,
loaded from env / `.env`, case-insensitive).

> **Note (accuracy):** as of this writing `config.py` defines core/DB/JWT/Redis/AI
> settings but **does not yet define `email_from` or a Resend/SES API-key
> setting** — the MVP registers only the `ConsoleEmailAdapter`
> (`api/app/notifications/adapters/registry.py`, lines 39–42), which logs instead
> of sending. When the Resend/SES adapter lands (CO-N02), add settings such as
> `email_from` and `resend_api_key` to `Settings` in `config.py` and keep the API
> key in a server-only secret (never commit it; keep `.env` out of git). Set
> `email_from` to an address on the **verified** sending domain so DMARC aligns.

---

## 3. Verification procedure (do this once, before relying on it)

This is the human verification the AC requires. Confirm **all three** pass.

### 3a. Confirm the DNS records resolve (`dig`)

```bash
# SPF — expect a single v=spf1 … record on the sending subdomain
dig +short TXT send.coachowl.com.au

# DKIM — expect the CNAME(s) to resolve to the provider (…dkim.amazonses.com)
dig +short CNAME <resend-dkim-token-1>._domainkey.coachowl.com.au
#   …or, for a TXT-style key:
dig +short TXT resend._domainkey.coachowl.com.au

# DMARC — expect v=DMARC1; p=…
dig +short TXT _dmarc.coachowl.com.au
```

What "good" looks like:

- SPF: exactly one string starting `v=spf1` … ending `~all` (or `-all`).
- DKIM: the CNAME target resolves (no `NXDOMAIN`), or the TXT shows `v=DKIM1;
  k=rsa; p=<key>`.
- DMARC: one string starting `v=DMARC1; p=none; rua=mailto:…`.

> Replace the example host names with your real domain and the real DKIM token(s).

### 3b. Send a real test message and read the auth results

1. From the app (or the **Resend dashboard "Send test"**, or SES `send-email`),
   send a message **from the verified domain** to:
   - your **Gmail** account, **and**
   - **mail-tester.com** (it gives you a unique throwaway address and a score).

2. **Gmail → open the message → ⋮ → "Show original".** You want:

   ```
   SPF:   PASS  with domain send.coachowl.com.au
   DKIM:  PASS  with domain send.coachowl.com.au   (header.d=)
   DMARC: PASS
   ```

   A passing result shows **SPF=pass, DKIM=pass, DMARC=pass**, and the DKIM
   `header.d=` / SPF domain **matches your From domain** (that's alignment).

3. **mail-tester.com:** open the score page. Aim for **10/10**; it explicitly
   lists SPF, DKIM and DMARC as passing and flags anything missing (e.g. no
   reverse DNS, content/spam-assassin issues).

4. Confirm the message landed in the **Inbox**, not Spam/Junk, on a fresh test
   account. This is the manual "不进垃圾箱" check the AC calls for. Record the date,
   From address, and screenshots of the passing headers.

---

## 4. Warm-up & monitoring

- **Warm up gradually.** A brand-new domain/IP with no history should start at
  **low volume** and increase over days/weeks. Transactional volume for an MVP is
  naturally low, which is ideal — don't blast a large list on day one.
- **Watch bounce and complaint rates.** Keep **bounces < ~2%** and **spam
  complaints < ~0.1%** (the Gmail/Yahoo threshold). High bounces = poor list
  hygiene and tank your reputation. Use the Resend dashboard / SES
  reputation metrics and (for SES) configure SNS bounce/complaint notifications.
- **Read DMARC aggregate reports** (the `rua` mailbox). They reveal who is sending
  as your domain and whether your mail aligns. Use a DMARC report viewer if raw
  XML is painful. Only ramp `p=none → quarantine → reject` once reports are clean.
- **Suppress hard bounces and complaints** — never keep mailing an address that
  bounced or complained.

---

## 5. Gmail / Yahoo bulk-sender requirements (2024+, current for 2026)

Gmail and Yahoo enforce sender requirements. The **strict bulk-sender rules**
(5,000+ messages/day to their users) require: SPF **and** DKIM, a **DMARC** record
(`p=none` minimum), domain alignment, **one-click list-unsubscribe**
(RFC 8058) on marketing mail, and spam complaint rate **< 0.3%** (target < 0.1%).

**Transactional vs bulk for CoachOwl:**

- CoachOwl's mail (lesson reminders, low-balance alerts, invoices) is
  **transactional** and triggered by user activity, not bulk marketing — so the
  one-click-unsubscribe mandate for *bulk* senders does not apply to genuine
  transactional messages.
- **However**, set up **SPF + DKIM + DMARC + alignment regardless** — those are
  expected of *every* sender now, and are exactly what this runbook configures.
- If CoachOwl ever sends **marketing/newsletter** mail, that stream **must** add
  **List-Unsubscribe** with one-click (RFC 8058) and honor opt-outs. Keep
  marketing on a **separate subdomain** from transactional so a complaint on
  marketing doesn't hurt reminder deliverability.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| **SPF=softfail / `~all` applied** | Sending server not in the SPF record, or SPF on the wrong name | Ensure the `include:` matches what the provider shows; publish SPF on the exact sending (sub)domain; confirm only **one** SPF record on that name. |
| **SPF `permerror`** | More than **10 DNS lookups**, or two SPF records | Flatten/merge includes to stay ≤10; delete the duplicate `v=spf1` record (one per name). |
| **DKIM=fail / "body hash did not verify"** | Message body altered in transit (a mailing-list footer, a gateway, or "minor" reformatting), or wrong/typo'd key published | Re-copy the DKIM records exactly from the dashboard; don't let intermediaries modify the body; re-verify in the provider; re-test. |
| **DKIM=none** | DKIM record not published/propagated, or sending before verification | Confirm CNAME/TXT resolves (`dig`), wait for propagation, click **Verify** in the dashboard before sending. |
| **DMARC=fail despite SPF/DKIM pass** | **Alignment** failure — passing domain ≠ From domain (e.g. From is your domain but DKIM `d=` is the provider's shared domain, or envelope-from is the provider's) | Send **from your verified domain**; ensure DKIM signs with your domain and/or the Return-Path is on your domain; if you legitimately use a subdomain, relax to `adkim=r; aspf=r`. |
| **DMARC=none / no policy** | No `_dmarc` TXT record, or on the wrong name | Publish the `_dmarc.<your-domain>` TXT at the **organizational** domain. |
| **Mail still lands in Spam though all three pass** | Content/reputation, not auth: spammy wording, link shorteners, image-only body, no reverse DNS, cold domain | Improve content, send plain-text alongside HTML, warm up volume, check mail-tester's content score, ensure provider PTR/reverse-DNS is set (provider-managed). |
| **Resend/SES shows "Not verified"** | DNS not propagated or record typo | Re-check each record with `dig`; some providers require the CNAME **not** be proxied (e.g. Cloudflare: set DNS-only / grey cloud). |
| **Cloudflare: CNAME flattening / proxy breaks DKIM** | Orange-cloud proxy or apex flattening rewrites the record | Set DKIM/verification CNAMEs to **DNS only** (grey cloud); don't proxy auth records. |

---

## References (in-repo)

- `CoachOwl-Execution-Plan-v0.md` — §1.5 risk *邮件进垃圾箱*; §2 provider choice
  (Resend default, SES alternative); CO-N02 / CO-N03 task ACs (lines ~270–275).
- `api/app/notifications/adapters/base.py` — `EmailAdapter` interface (Resend/SES
  drop in behind it).
- `api/app/notifications/adapters/registry.py` — only `ConsoleEmailAdapter`
  registered in the MVP (lines 39–42).
- `api/app/notifications/dispatcher.py` — single `email` channel outbox.
- `api/app/core/config.py` — application settings; add `email_from` / provider
  API-key settings here when the real adapter ships.

> **Provider-version-specific note:** Resend's dashboard wording, the exact SPF
> `include:`, and whether DKIM is delivered as CNAMEs or a TXT key can change.
> Treat the dashboard as source of truth and **verify there** when in doubt.
> The DKIM tokens in this doc (`<resend-dkim-token-N>`) are **placeholders the
> operator fills in from the Resend dashboard** — they are not real keys.
