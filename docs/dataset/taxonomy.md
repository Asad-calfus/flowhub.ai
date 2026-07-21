# Taxonomy — Phase 1

Controlled vocabulary used across the dataset, with definitions, boundaries, and ambiguous
cases. This taxonomy is what the future classifier will be evaluated against — it is not
input data.

## Feedback Type

### Bug report
- **Definition**: The customer describes something that is broken relative to documented or
  expected behavior.
- **Use when**: There's a concrete malfunction — a crash, wrong data, a feature not working
  as designed.
- **Don't use when**: The product works as designed but the customer dislikes the design
  (that's a Usability issue) or wants new capability (Feature request).
- **Example**: "App crashes every single time I try to open a task that has a file attached."
- **Ambiguous case**: `FB-0008` — a password reset email arrived very late (functionally a
  bug) but the customer's tone and framing ("kind of annoying but got in eventually") reads
  almost like a mild usability complaint. Labeled as Usability issue in this dataset since the
  customer didn't treat it as broken, just slow and inconvenient.

### Feature request
- **Definition**: The customer asks for capability that does not currently exist.
- **Use when**: The ask is for something new — a setting, an integration, a view.
- **Don't use when**: The capability exists but is hard to find or use (Usability issue), or
  the customer is reporting broken existing behavior (Bug report).
- **Example**: "Please, please add a dark mode option for the dashboard."
- **Ambiguous case**: `FB-0066` vs. `FB-0063` — both mention "export," but one requests Excel
  formatting (Feature request) and the other reports the existing CSV export silently
  truncating (Usability issue tied to a known bug). Identical surface wording, different
  underlying intent.

### Usability issue
- **Definition**: The feature exists and technically works, but is confusing, inconsistent,
  or unnecessarily effortful.
- **Use when**: Navigation, discoverability, terminology, or workflow friction is the
  complaint — nothing is factually broken.
- **Don't use when**: The behavior is objectively wrong (Bug report) or absent entirely
  (Feature request).
- **Example**: "Creating a new task takes way too many clicks — modal, then a second modal for
  assignee, then a third for due date."
- **Ambiguous case**: `FB-0063` (export truncation) — arguably a bug (data is silently lost),
  but framed here as a usability issue because the core complaint is the lack of any warning,
  not the row limit itself.

### Performance issue
- **Definition**: The feature works correctly but is too slow, laggy, or resource-heavy.
- **Use when**: Load times, sync delays, or responsiveness are the complaint, with no
  incorrect output.
- **Don't use when**: Something fails outright (Bug report) rather than being merely slow.
- **Example**: "Dashboard performance has degraded noticeably over the past month... 8-12
  seconds consistently."
- **Ambiguous case**: `FB-0014` — notification delivery is described as "sometimes instant,
  sometimes an hour later," which blurs the line between a performance issue (inconsistent
  latency) and a bug (notifications not firing at all). Labeled Performance issue since
  delivery does eventually happen.

### Service complaint
- **Definition**: The complaint is about the company's process, support, billing practices, or
  communication — not about the product's functionality per se.
- **Use when**: Support responsiveness, billing fairness, or policy changes are the subject.
- **Don't use when**: The complaint is purely about a technical defect (Bug report) or general
  friction with the product itself (Usability issue).
- **Example**: "Called support about an urgent issue and waited 6 days for a first response."
- **Ambiguous case**: `FB-0062` — complains that a known bug (duplicate calendar events) is
  still unresolved a month after reporting it. This could be tagged as a Bug report (it's
  about the bug) or a Service complaint (it's about the lack of follow-through). Labeled
  Service complaint because the customer's focus is the unresolved handling, not describing
  the bug itself.

### Praise
- **Definition**: Unprompted positive feedback about something that works well.
- **Use when**: The customer is complimenting a feature, fix, or support interaction.
- **Don't use when**: Positive framing is mixed with a real complaint (Mixed sentiment on a
  Bug report/Usability issue instead).
- **Example**: "Been using FlowHub for almost a year now and honestly it's the best PM tool
  we've tried."
- **Ambiguous case**: `FB-0010` — opens with praise for a redesign, then reports a bug. Labeled
  Bug report (the actionable content), with sentiment set to Mixed rather than Positive.

### Question
- **Definition**: The customer is asking for information, not reporting a problem or
  requesting new functionality.
- **Use when**: "How do I...", "Does this support...", "What's the difference between...".
- **Don't use when**: The question is rhetorical and really means "this is broken" (Bug
  report) — read the intent, not just the punctuation.
- **Example**: "Is there a public API? Want to pull task data into our internal reporting
  tool."
- **Ambiguous case**: `FB-0006` — "Is anyone else having trouble staying logged in...?" reads
  as a question but describes the same defect as several Bug report records in the same
  theme. Labeled Question because the customer is explicitly asking rather than asserting.

### Other
- **Definition**: Doesn't fit cleanly into any category above — too vague, off-topic, or
  low-content to classify confidently.
- **Use when**: The message is a general comment, a one-off aside, or too ambiguous to force
  into another type.
- **Don't use when**: A more specific type is a reasonable fit — Other should be a small
  minority of the dataset, not a catch-all.
- **Example**: "make it better please. thanks"
- **Ambiguous case**: `FB-0150` — a vague "the platform could use a refresh" comment that
  gestures at Usability issue and Feature request without committing to either.

## Product Module

Modules follow `data/context/product_modules.csv` exactly (Authentication, Dashboard, Task
Management, Notifications, Billing, Integrations, Reports, Mobile App).

- **Use when**: Feedback clearly names or describes functionality owned by that module (e.g.
  login/SSO → Authentication; invoices/charges → Billing).
- **Don't use when**: Feedback is genuinely cross-cutting (e.g. "everything feels slow") — pick
  the module most central to the complaint, and treat vague/general feedback as Dashboard
  (the main workspace surface) by convention.
- **Ambiguous case**: A complaint about notification settings resetting could be tagged
  Notifications (the setting itself) or Authentication (it happens around login/logout).
  This dataset tags it Notifications, since the setting that misbehaves lives there.

## Sentiment

### Positive
- **Definition**: The customer expresses satisfaction or approval with no meaningful
  complaint attached.
- **Example**: "5 stars, does exactly what we need without unnecessary bloat."
- **Ambiguous case**: Feature request wording that sounds enthusiastic ("Voting for dark mode
  too — small thing but it would make a big difference") is still fundamentally a request for
  something missing; labeled Positive here because the tone carries no frustration, but a
  stricter definition might call this Neutral.

### Neutral
- **Definition**: Factual, even-toned feedback — no strong emotional charge either way.
- **Example**: "Can I rename my workspace after creating it, or is that locked in permanently?"
- **Ambiguous case**: Many feature requests are Neutral by default (a plain ask), which can
  make Neutral feel like an default/catch-all bucket — reviewers should still check for
  frustration cues (exclamation points, "please fix," repeated complaints) before defaulting.

### Negative
- **Definition**: Frustration, anger, disappointment, or dissatisfaction is clearly present.
- **Example**: "Absolutely furious. I was locked out of my account for TWO DAYS..."
- **Ambiguous case**: Terse messages like "logged out again??" carry negative sentiment
  through punctuation and repetition rather than explicit words — don't require an angry
  vocabulary to label Negative.

### Mixed
- **Definition**: Genuinely both positive and negative content in the same message, not just
  mild negativity.
- **Example**: "quick note - login page redesign looks a lot cleaner after the update, nice
  work. still logs me out kinda fast tho lol"
- **Ambiguous case**: Distinguishing Mixed from Neutral-with-a-complaint is subjective; the
  bar used here is that Mixed requires an explicit positive statement (praise, thanks,
  compliment), not just a non-angry tone.

## Urgency

### Low
- **Definition**: No material impact on the customer's ability to work; cosmetic or
  minor-inconvenience issues.
- **Example**: "The 'default view' setting doesn't actually stick between sessions."
- **Ambiguous case**: Feature requests are almost always Low urgency by convention, even when
  phrased emphatically ("Dark mode when?"), since nothing is broken.

### Medium
- **Definition**: A real problem with a workaround available, or affecting a single user's
  workflow without blocking the whole team.
- **Example**: "Task priority flags reset to default whenever I bulk-move tasks between
  projects."
- **Ambiguous case**: Billing complaints are tagged Medium by default (real money, real
  annoyance, but rarely an active outage) unless the customer explicitly frames it as
  blocking (e.g. threatening to churn).

### High
- **Definition**: Blocking, affecting many users, financially significant, or explicitly
  described as urgent/escalated by the customer.
- **Example**: "This is blocking our entire engineering team from using FlowHub during a
  sprint deadline this week."
- **Ambiguous case**: A single Free-tier user being logged out is arguably lower stakes than
  an Enterprise team being locked out — this dataset weighs both the technical severity and
  the business impact (tier, team size implied) when assigning High vs. Medium to the same
  underlying bug.
