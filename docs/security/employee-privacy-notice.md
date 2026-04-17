# Employee privacy notice — Ant Observation Agent

> **Purpose of this document.** This is a template. Customer legal/HR teams
> MUST adapt it to their jurisdiction before distributing. It is written in
> plain language on purpose; please do not rewrite it into legalese when you
> localise.
>
> Referenced from:
> - GDPR Art. 13 (information to data subjects)
> - BDSG §26 (employee data)
> - Business Plan v4.5 §11A.5 (privacy-by-design for observation layer)

## 1. What this is

Your employer has deployed the **Ant Observation Agent** on your work
computer and/or inside your work browser. This notice explains — in plain
language — what the agent sees, what it does *not* see, what happens to the
data, and what rights you have.

If anything below is unclear, your works council (Betriebsrat /
Ondernemingsraad / equivalent) and your employer's Data Protection Officer
(contact below) can answer questions.

## 2. What the agent records

The agent records **metadata about your work**, not your work itself.
Specifically:

| Category | Example of what is captured |
| --- | --- |
| Application switches | "You switched from *Outlook* to *SAP*." |
| Window focus | "You had *Excel* in the foreground for 12 minutes." |
| File open/save events | "You opened a file named `invoice_Q1.xlsx`." (The *name* only, never the file contents.) |
| Browser navigation | "You visited `salesforce.com/opportunities/:id`." (The *path template*, with customer IDs redacted.) |
| Form-submission field names | "You submitted a form called `new_lead` with fields named `company`, `email`, `region`." (The *field names* only, never the values you typed.) |

## 3. What the agent NEVER records

The following are forbidden **by the agent's design** — not by policy alone.
Attempting to capture any of these causes the server to reject the event and
raise an alert to the security team:

- **Keystrokes.** The agent does not keylog.
- **Clipboard contents.**
- **Form field values** of any kind — including passwords, emails, free-text
  messages, comments, or anything you type into a form.
- **Screen contents.** No screenshots, screen recordings, or OCR.
- **Camera or microphone input.**
- **Cookies, authentication tokens, or session identifiers.**
- **File contents.** The agent sees *that* a file was opened and its
  filename, not what is inside it.
- **Personal activity.** If your employer permits personal use of the
  device, the agent should be paused. See §6.

## 4. Why your employer is doing this

The legal basis differs per jurisdiction and your employer must state it
explicitly in their local addendum to this notice. Common bases:

- **Works agreement / Betriebsvereinbarung / Instemmingsverzoek.**
  Your works council has agreed to a specific scope with the employer.
- **Legitimate interest (GDPR Art. 6(1)(f))** in understanding how work
  flows through shared systems, so that repetitive steps can be automated.
- **Contractual necessity (Art. 6(1)(b))** for specific regulated roles.

The specific purpose is: **to identify repetitive multi-step workflows that
three or more employees perform, so that they can be proposed for
automation.** Data is used for no other purpose. In particular:

- It is **not used for individual performance reviews.**
- It is **not used for disciplinary measures.**
- It is **not shared with your manager** at individual-actor granularity.
- Automated proposals are only generated when **three or more employees**
  perform a similar pattern — patterns unique to one or two people are
  discarded.

## 5. Retention

| Data type | Retention |
| --- | --- |
| Raw observation events | 90 days, then automatically deleted |
| Aggregated patterns (k≥3 employees) | 365 days |
| Audit log of proposal approvals | As required by the applicable Betriebsvereinbarung (typically 3 years) |

Retention is enforced by scheduled database jobs and is visible in the
`data-retention-policy.md` document.

## 6. How to pause observation

You can pause observation at any time:

- **Desktop agent:** click the Ant icon in your system tray → *Pause*.
- **Browser extension:** click the Ant icon next to the URL bar → *Pause*.

Pausing is local to your machine and takes effect immediately. Your employer
will see *that* observation is paused (from the heartbeat disappearing) but
not *why*.

Some organisations may restrict pausing for specific roles; if so, that
restriction is in your local addendum.

## 7. Your rights (GDPR Chapter III)

You have the right to:

- **Access** the observation data associated with your `actor_id`. Request
  via the DPO contact below; you will receive a JSON export within 30 days.
- **Rectify** inaccurate data.
- **Erase** your observation data ("right to be forgotten"), subject to
  legal holds.
- **Restrict** or **object to** processing.
- **Port** your data to another system in a machine-readable format.
- **Complain** to your national supervisory authority (for Germany: BfDI or
  the relevant Landesdatenschutzbeauftragte; for the Netherlands:
  Autoriteit Persoonsgegevens).

No AI-only decision about you will be taken based on this data (GDPR
Art. 22).

## 8. Who to contact

- **Data Protection Officer:** _[customer to fill in]_
- **Works council:** _[customer to fill in]_
- **Ant Automations (processor) DPO contact:** dpo@antautomations.example

---

*Document owner:* Legal & Compliance.
*Version:* template v1.0 — Ant Automations Business Plan v4.5.
*Review cadence:* annually, or when the observation scope is amended.
