# privacy_and_data_use

## Data Collected by BADGR Technologies

| Data Type | How Collected | Purpose |
|-----------|-------------|---------|
| Name + contact info | Web contact form, intake call | Client communication |
| Website URL | Intake form, discovery call | Scan and fix delivery |
| Site analytics access | Client grants read-only GA4 access | Performance benchmarking |
| Lighthouse scan data | Public tool, no login required | Technical audit |
| Third-party script list | DevTools / source scan | Compliance review |
| Email opens/clicks | Standard email tracking | Follow-up cadence |

---

## What BADGR Does NOT Collect

- Protected Health Information (PHI) from client patients
- Login credentials (clients grant access via their own admin accounts)
- Financial account data
- Social Security numbers or government IDs

---

## HIPAA-Aware Handling Principles

BADGR operates in the healthcare-adjacent space (medical/dental practice clients). We follow these principles even though BADGR itself is not a covered entity:

1. **No PHI in deliverables** — client reports reference site structure, not patient data
2. **No PHI in AI prompts** — client URLs and anonymized site descriptions only; no patient records fed to any model
3. **Scoped access only** — request read-only GA4 or GSC access; do not request CRM or EHR access
4. **Secure storage** — client files stored in encrypted local folder structure; no unsecured cloud sync
5. **Retention** — client files retained for 2 years post-engagement, then deleted unless client requests otherwise

---

## Third-Party Tools That Touch Client Data

| Tool | Data Shared | Notes |
|------|------------|-------|
| Google Lighthouse | Public URL only | No login, no data stored |
| Google PageSpeed Insights | Public URL only | No login |
| axe DevTools | Page DOM (local browser) | No data sent to third party |
| Google Analytics 4 | Read-only access to client's GA4 | Access revoked post-engagement |
| Stripe | Payment info only | PCI-compliant; BADGR never sees full card numbers |

---

## Privacy Policy Snippet (for website use)

> "BADGR Technologies LLC collects contact information submitted through this website to respond to inquiries and deliver services. We do not sell, share, or rent personal information to third parties. Website analytics are collected via Google Analytics 4. For questions, contact adgrant1@badgrtech.com. BADGR Technologies LLC, 8735 Dunwoody Place STE. #7223, Atlanta, GA 30350."
