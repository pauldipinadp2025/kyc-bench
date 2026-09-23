# Synthetic Bank KYC Policy (v0.1)

This is an invented policy written for KYC-Bench. It is not any real bank's policy
and it is not legal advice. Every case is graded against these rules, so ground
truth never depends on interpreting a real regulation.

| ID | Rule |
|----|------|
| P-1.1 | Identity must be verified with at least one valid, unexpired government photo ID. |
| P-1.2 | Address must be confirmed by a document dated within the last 3 months. |
| P-2.1 | Every customer and every beneficial owner must be screened against the sanctions and PEP lists. |
| P-2.2 | A name match may only be cleared as a false positive if at least two independent identifiers (for example date of birth, nationality, ID number) differ from the listed person. |
| P-3.1 | A beneficial owner is any natural person who owns or controls 25% or more of the customer, directly or indirectly. Indirect ownership is calculated by multiplying percentages along each ownership chain and adding the chains. |
| P-3.2 | If any part of the ownership chain uses a nominee arrangement or an undisclosed principal, Enhanced Due Diligence (EDD) is required. |
| P-4.1 | If a beneficial owner is a Politically Exposed Person (PEP), EDD and senior management approval are required. |
| P-4.2 | A confirmed sanctions match means the application must be rejected. |
| P-5.1 | Risk rating is Low, Medium or High. Any EDD trigger means High. A clean individual with no adverse flags is Low. |

## Decisions available to the reviewer

- `approve`: onboard the customer normally
- `edd`: hold and escalate for Enhanced Due Diligence
- `reject`: decline the application
- `file_str`: decline and file a suspicious transaction report
