# Data Dictionary — Phase 1

## `data/processed/feedback_dataset.csv` (and `data/raw/synthetic_feedback.csv`)

| Field | Type | Required | Allowed values | Example | Kind |
|---|---|---|---|---|---|
| `feedback_id` | string | Required | Unique, format `FB-####` | `FB-0001` | Generated metadata |
| `feedback_text` | string | Required | Free text | "App crashes every single time I try to open a task that has a file attached." | Input |
| `source` | string | Required | Support ticket, Survey, App review, Chat, Email, Community post | `Support ticket` | Input |
| `created_at` | datetime | Required | `YYYY-MM-DD HH:MM:SS` | `2026-05-09 09:14:00` | Input |
| `customer_id` | string | Required | Format `CUST-####`, may repeat across records for the same customer | `CUST-1001` | Input |
| `customer_tier` | string | Required | Free, Pro, Enterprise | `Pro` | Input |
| `product_module` | string | Required | One of the 8 modules in `product_modules.csv` | `Authentication` | Input |
| `product_version` | string | Optional | One of the 6 releases in `product_releases.csv`, or blank | `v2.4.0` | Input |
| `rating` | integer | Optional | 1-5, or blank | `4` | Input |
| `language` | string | Required | ISO-style code: `en`, `es`, `fr`, `de`, `pt` | `en` | Input |
| `feedback_type` | string | Required | Bug report, Feature request, Usability issue, Performance issue, Service complaint, Praise, Question, Other | `Bug report` | Evaluation label |
| `category` | string | Required | Technical Issue, Product Feedback, Support Experience, Positive Feedback, Inquiry, Other (roll-up of `feedback_type`, see mapping below) | `Technical Issue` | Evaluation label |
| `sentiment` | string | Required | Positive, Neutral, Negative, Mixed | `Negative` | Evaluation label |
| `urgency` | string | Required | Low, Medium, High | `High` | Evaluation label |
| `theme_hint` | string | Optional | One of 8 recurring theme names, or blank if the record doesn't belong to a major theme | `Login failures after an update` | Evaluation label |
| `related_context_id` | string | Optional | A `bug_id` (`BUG-###`) or `request_id` (`FR-###`), or blank if the feedback is a new issue with no known match | `BUG-001` | Evaluation label |
| `is_gold_label` | boolean | Required | `True`, `False` | `True` | Evaluation label |
| `label_source` | string | Required | Synthetic, Manually verified | `Manually verified` | Evaluation label |

**`category` mapping** (derived from `feedback_type`, not independently labeled):

| feedback_type | category |
|---|---|
| Bug report, Performance issue | Technical Issue |
| Feature request, Usability issue | Product Feedback |
| Service complaint | Support Experience |
| Praise | Positive Feedback |
| Question | Inquiry |
| Other | Other |

## `data/evaluation/gold_feedback.csv`

Same columns as `feedback_dataset.csv`, restricted to the 30 gold-labeled rows, plus one
additional column:

| Field | Type | Required | Allowed values | Example | Kind |
|---|---|---|---|---|---|
| `gold_notes` | string | Required | Free text | "Angry, detailed Enterprise report; release-related (v2.4.0 regression)." | Evaluation label (reviewer rationale, evaluation file only) |

## `data/context/product_modules.csv`

| Field | Type | Required | Allowed values | Example |
|---|---|---|---|---|
| `module_id` | string | Required | Unique, format `MOD-##` | `MOD-01` |
| `module_name` | string | Required | Unique | `Authentication` |
| `description` | string | Required | Free text | "Handles user sign-up, login, SSO, password management, and session security." |
| `owning_team` | string | Required | Free text | `Platform Team` |

## `data/context/known_bugs.csv`

| Field | Type | Required | Allowed values | Example |
|---|---|---|---|---|
| `bug_id` | string | Required | Unique, format `BUG-###` | `BUG-001` |
| `title` | string | Required | Free text | "SSO session expires within minutes of login" |
| `description` | string | Required | Free text | Full description of the defect |
| `product_module` | string | Required | One of the 8 module names | `Authentication` |
| `affected_versions` | string | Required | Comma-separated release versions | `v2.4.0, v2.5.0` |
| `status` | string | Required | Open, In progress, Fixed, Monitoring | `Open` |
| `priority` | string | Required | Low, Medium, High, Critical | `High` |
| `created_at` | date | Required | `YYYY-MM-DD` | `2026-05-03` |

## `data/context/feature_requests.csv`

| Field | Type | Required | Allowed values | Example |
|---|---|---|---|---|
| `request_id` | string | Required | Unique, format `FR-###` | `FR-001` |
| `title` | string | Required | Free text | "Dark mode for the web dashboard" |
| `description` | string | Required | Free text | Full description of the request |
| `product_module` | string | Required | One of the 8 module names | `Dashboard` |
| `status` | string | Required | Under review, Planned, In progress, Released, Rejected | `Planned` |
| `request_count` | integer | Required | Positive integer | `284` |
| `roadmap_status` | string | Required | Free text (e.g. quarter, "Backlog", "Not planned", "Shipped in vX.X.X") | `Q3 2026` |

## `data/context/product_releases.csv`

| Field | Type | Required | Allowed values | Example |
|---|---|---|---|---|
| `version` | string | Required | Unique, format `vX.X.X` | `v2.4.0` |
| `release_date` | date | Required | `YYYY-MM-DD` | `2026-04-27` |
| `main_changes` | string | Required | Free text | "Added Okta SSO login and calendar view for Task Management" |
| `affected_modules` | string | Required | Comma-separated module names | `Authentication, Task Management` |
| `known_limitations` | string | Required | Free text | "SSO session refresh behavior not fully validated across all timezones" |

## Input vs. label summary

**Input fields** (safe to pass to a future classifier as-is): `feedback_text`, `source`,
`created_at`, `customer_id`, `customer_tier`, `product_module`, `product_version`, `rating`,
`language`.

**Generated metadata** (identifiers/bookkeeping, not a signal to learn from): `feedback_id`.

**Evaluation labels** (used only to score model output, never passed in as input):
`feedback_type`, `category`, `sentiment`, `urgency`, `theme_hint`, `related_context_id`,
`is_gold_label`, `label_source`, `gold_notes`.
