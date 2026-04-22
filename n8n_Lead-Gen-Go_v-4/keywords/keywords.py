#!/usr/bin/env python3
import csv
import time
from datetime import datetime
from pathlib import Path
from serpapi import GoogleSearch

# ── Web-Ops ICP Classification
# Maps Google Maps business `type` strings → (vertical, compliance_urgency).
# Ordered by specificity: more specific matches should appear earlier.
# compliance_urgency reflects regulatory exposure (ADA, HIPAA, PCI, etc.)
# that makes web-ops services urgent and budget-justified.
_WEBOPS_ICP_MAP = [
    ("legal",               "high",        [
        "law", "attorney", "legal", "notary", "paralegal", "litigat",
    ]),
    ("healthcare",          "high",        [
        "clinic", "medical", "dental", "dentist", "doctor", "physician",
        "chiropract", "physical therapy", "urgent care", "pharmacy",
        "optometrist", "ophthalmol", "dermatol", "cardiol", "orthop",
        "pediatric", "obgyn", "psychiatr", "psycholog", "therapist",
        "wellness", "health", "hospital", "nursing", "med spa",
    ]),
    ("financial",           "high",        [
        "accountant", "accounting", "cpa", "bookkeeping", "financial",
        "insurance", "mortgage", "bank", "credit union", "wealth", "advisor",
    ]),
    ("ecommerce_retail",    "medium_high", [
        "retail", "store", "shop", "boutique", "jewel", "clothing",
        "furniture", "electronics", "apparel", "outlet",
    ]),
    ("real_estate",         "medium",      [
        "real estate", "realtor", "realty", "property management",
        "broker", "apartment", "leasing", "commercial real",
    ]),
    ("home_services",       "medium",      [
        "hvac", "plumb", "roof", "landscap", "electrician", "contractor",
        "pest control", "cleaning", "maid", "pool", "garage", "flooring",
        "painting", "remodel", "home repair", "handyman", "restoration",
    ]),
    ("hospitality_food",    "medium",      [
        "restaurant", "cafe", "coffee", "bar ", "hotel", "motel",
        "catering", "bakery", "food", "pizza", "diner", "bistro", "lounge",
    ]),
    ("professional_services", "medium",   [
        "consulting", "consultant", "marketing agency", "staffing",
        "recruitment", "it service", "tech support", "software",
    ]),
    ("education",           "medium",      [
        "school", "academy", "tutoring", "learning center", "college",
        "university", "training", "daycare", "childcare", "preschool",
    ]),
]

def _classify_webops_icp(type_str: str) -> tuple:
    """
    Map a Google Maps business type string to (webops_icp_type, compliance_urgency).
    Falls back to ("general", "low") when no vertical matches.
    """
    t = (type_str or "").lower()
    for vertical, urgency, keywords in _WEBOPS_ICP_MAP:
        if any(kw in t for kw in keywords):
            return vertical, urgency
    return "general", "low"

def load_api_key() -> str:
    for fn in (".env", ".env-local"):
        path = Path(fn)
        if not path.exists():
            continue
        with path.open() as f:
            for line in f:
                if line.startswith("SERPAPI_KEY="):
                    return line.split("=", 1)[1].strip()
                if line.startswith("SERP_API_KEY="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("SERPAPI_KEY or SERP_API_KEY not found in .env or .env-local")

# ── T0: Pain & Dissatisfaction — businesses actively looking to switch vendors.
# These are the highest-intent signals: the prospect already knows they have a
# problem and is searching for someone new. Source: keywords.atl.north.json
T0_KEYWORDS = [
    "web development agency not delivering results [CITY]",
    "unhappy with web developer [CITY]",
    "switch web development agency [CITY]",
    "digital agency [CITY] not delivering",
    "poor website maintenance service [CITY]",
    "need a new web developer [CITY]",
    "seo retainer not worth it [CITY]",
    "website developer not meeting expectations [CITY]",
    "web maintenance contract issues [CITY]",
    "switch seo agency [CITY]",
]

TIER1_KEYWORDS = [
    "website speed optimization services [CITY]",
    "why website not converting leads [CITY]",
    "ADA website compliance audit [CITY]",
    "B2B website form abandonment fix",
    "HIPAA compliance website audit [CITY]",
    "website penetration testing [CITY]",
    "why website not ranking Google [CITY]",
    "WCAG 2.2 accessibility requirements [CITY]",
    "low conversion rate audit [CITY]",
    "Core Web Vitals optimization [CITY]",
]
TIER2_KEYWORDS = [
    "PCI DSS security audit [CITY]",
    "SEO audit improve rankings [CITY]",
    "mobile website conversion rate [CITY]",
    "technical debt modernization consulting",
    "SOC 2 compliance website services",
    "website trust signals audit",
    "responsive design mobile optimization [CITY]",
    "conversion killers analysis [CITY]",
    "my website is slow losing customers",
    "70% form abandonment rate solution",
]
TIER3_KEYWORDS = [
    "website monitoring retainer services [CITY]",
    "GDPR compliance website audit",
    "website health checkup retainer [CITY]",
    "continuous vulnerability scanning",
    "competitor ranking higher Google",
    "ADA lawsuit risk compliance check",
    "Section 508 compliance services [CITY]",
    "website navigation UX audit [CITY]",
    "SEO strategy B2B [CITY]",
    "website performance consulting [CITY]",
]

KEYWORD_TIERS = {
    "T0": T0_KEYWORDS,
    "T1": TIER1_KEYWORDS,
    "T2": TIER2_KEYWORDS,
    "T3": TIER3_KEYWORDS,
}

# ── Outreach templates keyed by keyword_base (city-stripped, lowercased).
# Maps each keyword to a ready-to-use cold email structure.
# Swap [COMPANY] with the lead's actual name at send time.
OUTREACH_TEMPLATES = {
    # T0 — switching pain / vendor dissatisfaction
    "web development agency not delivering results": {
        "email_subject": "Tired of an agency that overpromises and underdelivers?",
        "email_opening": "A lot of businesses in [CITY] are stuck in a retainer with an agency that hasn't moved the needle.",
        "value_prop": "We do a free site audit before any engagement so you see exactly what we'd fix — no guesswork.",
        "cta": "Want a candid second opinion on what's holding [COMPANY]'s site back?",
        "urgency_angle": "Every month with the wrong agency is revenue left on the table.",
    },
    "unhappy with web developer": {
        "email_subject": "[COMPANY]'s site deserves better than 'we're working on it'",
        "email_opening": "If your current developer has been vague on timelines and light on results, you're not alone.",
        "value_prop": "Transparent scope, fixed deliverables, and a free performance audit before you commit.",
        "cta": "Open to a 15-minute call to see what a fresh set of eyes finds on your current site?",
        "urgency_angle": "A slow or broken site loses you leads 24/7 while you wait for fixes.",
    },
    "switch web development agency": {
        "email_subject": "Making a web agency switch? Here's how to do it right",
        "email_opening": "Switching agencies mid-project is painful — but staying with one that isn't performing costs more.",
        "value_prop": "We specialize in clean handoffs: audit your current site, identify what's working, and build from there.",
        "cta": "Should I send over a 'switching guide' checklist plus a free audit of [COMPANY]'s current site?",
        "urgency_angle": "The right time to switch is before your next campaign, not after.",
    },
    "digital agency not delivering": {
        "email_subject": "Is your agency showing you the right numbers — or just the good ones?",
        "email_opening": "Vanity metrics look great in reports but don't pay the bills.",
        "value_prop": "We audit your current setup and show you exactly which metrics connect to revenue — and which ones don't.",
        "cta": "Want a plain-English breakdown of whether [COMPANY]'s current digital spend is actually working?",
        "urgency_angle": "Budget allocated to the wrong channels compounds every month.",
    },
    "poor website maintenance service": {
        "email_subject": "[COMPANY]'s site maintenance shouldn't be a guessing game",
        "email_opening": "Inconsistent updates, mystery downtime, no changelog — poor maintenance creates technical debt fast.",
        "value_prop": "We offer clear monthly maintenance retainers: documented updates, uptime monitoring, and monthly health reports.",
        "cta": "Can I send you a quick side-by-side of what proactive vs. reactive maintenance actually costs a business like yours?",
        "urgency_angle": "Security patches and performance updates can't wait — and every day they do is a liability.",
    },
    "need a new web developer": {
        "email_subject": "Finding the right web developer for [COMPANY] — what to look for",
        "email_opening": "Most businesses find a developer through referrals and hope for the best. There's a better process.",
        "value_prop": "We start every engagement with a free technical audit so you know exactly what the work scope is before signing anything.",
        "cta": "Open to seeing what a proper web audit reveals about [COMPANY]'s current site before we talk scope?",
        "urgency_angle": "The faster you find the right fit, the sooner your site starts working for you.",
    },
    "seo retainer not worth it": {
        "email_subject": "Is [COMPANY]'s SEO retainer actually moving rankings?",
        "email_opening": "If your SEO agency can't show you exactly which pages improved and why, that's a red flag.",
        "value_prop": "Free technical SEO audit: we show you what Google actually sees on your site, no agency spin.",
        "cta": "Want a candid look at where [COMPANY] actually ranks vs. competitors — before spending another month on retainer?",
        "urgency_angle": "25% decline in organic search traffic predicted in 2025 — weak SEO compounds the impact.",
    },
    "website developer not meeting expectations": {
        "email_subject": "What does 'done' actually mean for [COMPANY]'s website?",
        "email_opening": "Vague deliverables are how projects drag on for months without real progress.",
        "value_prop": "We scope every project with measurable outcomes: load time, Core Web Vitals, conversion benchmarks — not just 'pages built'.",
        "cta": "Can I walk you through how we define done and show a free audit of your current site's gaps?",
        "urgency_angle": "Every week a site underperforms is a direct hit to pipeline.",
    },
    "web maintenance contract issues": {
        "email_subject": "Your website maintenance contract should protect you — not trap you",
        "email_opening": "Opaque contracts, surprise fees, and no clear exit terms are common — and avoidable.",
        "value_prop": "Month-to-month maintenance plans, fully documented, with a free site health audit to kick things off.",
        "cta": "Should I send over a breakdown of what a fair maintenance contract looks like for a site like [COMPANY]'s?",
        "urgency_angle": "A site without an active maintenance contract is an unmonitored liability.",
    },
    "switch seo agency": {
        "email_subject": "Before you sign with a new SEO agency — run this check on [COMPANY]'s site",
        "email_opening": "Most businesses switching SEO agencies inherit the same technical debt the last one left behind.",
        "value_prop": "Free technical SEO + Core Web Vitals audit before any engagement — so you know exactly what you're starting with.",
        "cta": "Want that free baseline audit for [COMPANY] before you commit to a new agency?",
        "urgency_angle": "Starting a new SEO engagement without a technical audit is like painting over rust.",
    },
    # T1 — immediate pain, high conversion
    "website speed optimization services": {
        "email_subject": "[COMPANY] is losing clicks to a 3-second wait",
        "email_opening": "Ran a quick check on your site — mobile users hit a 3+ second wait before anything useful loads.",
        "value_prop": "Specialized in squeezing sub-2s load times for small teams without redesigning everything.",
        "cta": "Worth a 15-minute call to walk through a free Core Web Vitals + Lighthouse report for your site?",
        "urgency_angle": "1s vs 5s load time = 5x conversion lift for B2B sites.",
    },
    "why website not converting leads": {
        "email_subject": "Leads leaking from [COMPANY]'s website",
        "email_opening": "Your site gets visitors, but your pages behave like a read-only brochure instead of a lead machine.",
        "value_prop": "Free conversion teardown: forms, CTAs, page speed, and trust signals — all in one report.",
        "cta": "Can I send you a 1-page summary of the top 3 fixes for your current funnel?",
        "urgency_angle": "Not a traffic problem. A conversion problem — and every day it goes unfixed costs you pipeline.",
    },
    "ADA website compliance audit": {
        "email_subject": "Quick ADA risk check for [COMPANY]",
        "email_opening": "ADA website lawsuits jumped this year, and most small businesses don't realize they're exposed until a letter arrives.",
        "value_prop": "Free automated ADA/WCAG scan plus a human-readable summary that shows risk in plain English.",
        "cta": "Want me to send over an ADA risk snapshot for your current site?",
        "urgency_angle": "2,014 ADA website lawsuits filed H1 2025 — up 37% YoY. Only 4% of sites are currently compliant.",
    },
    "B2B website form abandonment fix": {
        "email_subject": "Your forms are quietly killing deals",
        "email_opening": "Your form asks more from prospects than they get back — so they quit halfway.",
        "value_prop": "The pre-audit flags friction points; you get a simple before/after form layout you can implement in a day.",
        "cta": "Want a quick walkthrough of your form with suggested changes?",
        "urgency_angle": "70% average form abandonment rate. One optimization: 0.96% → 8.1% conversion.",
    },
    "HIPAA compliance website audit": {
        "email_subject": "HIPAA 2025: is [COMPANY]'s site aligned?",
        "email_opening": "New guidance expects encryption, MFA, and regular testing — many clinic sites fall short quietly.",
        "value_prop": "Pre-audit checks your public-facing site against the new expectations and highlights what to fix first.",
        "cta": "Open to a free public-surface HIPAA risk pass on your site?",
        "urgency_angle": "Healthcare market $3.6B → $9.9B. New 2025 HIPAA regs are mandatory — not optional.",
    },
    "website penetration testing": {
        "email_subject": "Has [COMPANY]'s website ever been tested like an attacker?",
        "email_opening": "Brochures get tested; websites don't — until something breaks.",
        "value_prop": "Surface-level pen-test-style scan combined with performance and compliance issues in one short report.",
        "cta": "Want a high-level red/yellow/green risk map for your public site?",
        "urgency_angle": "New HIPAA: pen testing required every 12mo, vulnerability scans every 6mo.",
    },
    "why website not ranking Google": {
        "email_subject": "[COMPANY] is invisible for local buyers",
        "email_opening": "When searching for your service in [CITY], your competitors appear first — your site rarely shows.",
        "value_prop": "Free technical audit for crawl, speed, and basic on-page issues. No content spam.",
        "cta": "Should I send a short 'what Google sees vs. what you think it sees' breakdown?",
        "urgency_angle": "Gartner: 25% decline in organic search traffic predicted. Urgency to rank is climbing fast.",
    },
    "WCAG 2.2 accessibility requirements": {
        "email_subject": "WCAG 2.2 just raised the bar — is [COMPANY]'s site ready?",
        "email_opening": "WCAG 2.2 introduced new criteria many sites still fail, and legal risk follows non-compliance.",
        "value_prop": "Free WCAG 2.2 gap scan — you get a pass/fail by criterion so you know exactly what to fix.",
        "cta": "Want the free WCAG 2.2 compliance snapshot for [COMPANY]'s site?",
        "urgency_angle": "Only 4% of sites are ADA-compliant. Lawsuit risk is not theoretical.",
    },
    "low conversion rate audit": {
        "email_subject": "[COMPANY]'s traffic deserves better conversion",
        "email_opening": "Getting visitors but not leads means your site is working against you — not for you.",
        "value_prop": "Audit covers mobile UX, form friction, CTA placement, and trust signals — one actionable report.",
        "cta": "Can I send a free conversion audit for [COMPANY]'s top landing page?",
        "urgency_angle": "Mobile UX lags desktop by 40-60%. CRO is critical for any site with real mobile traffic.",
    },
    "Core Web Vitals optimization": {
        "email_subject": "[COMPANY] is failing Core Web Vitals",
        "email_opening": "Largest Contentful Paint and interaction scores on your site are in the 'needs improvement' zone on mobile.",
        "value_prop": "Free CWV report plus a prioritized, dev-friendly fix list based on your stack.",
        "cta": "Can I send your CWV snapshot with 3 quick-win fixes?",
        "urgency_angle": "Core Web Vitals are a direct Google ranking factor. Failing = lower rank + lower revenue.",
    },
    # T2 — strategic ongoing
    "PCI DSS security audit": {
        "email_subject": "PCI risk on [COMPANY]'s checkout?",
        "email_opening": "Payment pages that look fine to users can still violate modern PCI expectations.",
        "value_prop": "Quick PCI-aware front-end audit with clear next steps — no jargon.",
        "cta": "Want a short traffic + transaction risk overview of your checkout?",
        "urgency_angle": "PCI non-compliance fines range from $5K–$100K/month. Front-end exposure is the most common gap.",
    },
    "SEO audit improve rankings": {
        "email_subject": "[COMPANY]'s competitors are taking your search traffic",
        "email_opening": "Technical SEO issues — not content — are usually why a site loses ground to competitors.",
        "value_prop": "Free technical SEO audit: crawlability, site speed, structured data, and local signals.",
        "cta": "Should I run the technical audit on [COMPANY]'s site and send the findings?",
        "urgency_angle": "Competitors already ranking = compounding traffic loss every month you wait.",
    },
    "mobile website conversion rate": {
        "email_subject": "[COMPANY]'s mobile site is working against you",
        "email_opening": "Most of your traffic is mobile, but your pages behave like they were built for desktop-only.",
        "value_prop": "Audit looks at mobile speed, layout shifts, and form UX — you get a specific mobile-only fix plan.",
        "cta": "Worth a quick review if it lifts mobile conversions even a few percent?",
        "urgency_angle": "75% of web traffic is mobile. Mobile conversion lags desktop by 40% on unoptimized sites.",
    },
    "technical debt modernization consulting": {
        "email_subject": "Is [COMPANY]'s tech stack quietly costing you?",
        "email_opening": "Legacy systems and accumulated technical debt drain developer time and slow every feature.",
        "value_prop": "Technical debt audit: we quantify what it's costing you and prioritize what to address first.",
        "cta": "Open to a free 'debt map' call for [COMPANY]'s current stack?",
        "urgency_angle": "44% of companies waste 25%+ of dev time on legacy systems — that's direct revenue leakage.",
    },
    "SOC 2 compliance website services": {
        "email_subject": "SOC 2 requirement blocking [COMPANY]'s enterprise sales?",
        "email_opening": "Procurement teams at enterprise clients now require SOC 2 — and your website is part of the audit surface.",
        "value_prop": "Free web-surface SOC 2 readiness scan: we flag what needs to change before your next enterprise deal.",
        "cta": "Want the free SOC 2 web-surface checklist run against [COMPANY]'s public site?",
        "urgency_angle": "SOC 2 is now a procurement mandate for most SaaS/B2B vendor approvals.",
    },
    "website trust signals audit": {
        "email_subject": "Missing trust signals are costing [COMPANY] conversions",
        "email_opening": "Visitors decide whether to trust you within seconds — and missing social proof is an instant conversion killer.",
        "value_prop": "Trust signals audit: testimonials, security badges, review counts, certifications — what's missing and where.",
        "cta": "Can I send a free trust signal gap report for [COMPANY]'s homepage and key landing pages?",
        "urgency_angle": "Missing social proof = 27% average conversion drop. That's measurable, fixable revenue.",
    },
    "responsive design mobile optimization": {
        "email_subject": "53% of [COMPANY]'s mobile visitors are bouncing",
        "email_opening": "If your site loads in more than 3 seconds on mobile, over half your visitors leave before seeing anything.",
        "value_prop": "Mobile performance audit: load time, layout shifts, touch target sizing, and form usability.",
        "cta": "Want a free mobile audit that shows exactly where [COMPANY]'s site loses people?",
        "urgency_angle": "53% bounce rate if load time exceeds 3s. Mobile-first is no longer optional.",
    },
    "conversion killers analysis": {
        "email_subject": "3 conversion killers we typically find on sites like [COMPANY]'s",
        "email_opening": "Vague CTAs, cluttered navigation, and weak forms are the silent revenue leak most sites have.",
        "value_prop": "Free conversion killers scan: we identify your top 3 friction points with actionable fixes.",
        "cta": "Should I run [COMPANY]'s site through the scan and send back the top 3?",
        "urgency_angle": "Every friction point on the path to conversion is a lead that walked out the door.",
    },
    "my website is slow losing customers": {
        "email_subject": "[COMPANY]'s site speed is losing you customers right now",
        "email_opening": "If customers are telling you your site is slow, they're the small fraction who bother to say so — most just leave.",
        "value_prop": "Free speed audit: Lighthouse + Core Web Vitals + a prioritized fix list your developer can act on today.",
        "cta": "Worth 15 minutes to walk through exactly what's slowing [COMPANY]'s site down?",
        "urgency_angle": "Every 1-second delay in load time reduces conversions by 7% for B2B sites.",
    },
    "70% form abandonment rate solution": {
        "email_subject": "Solving the 70% form abandonment problem for [COMPANY]",
        "email_opening": "The industry average for form abandonment is 70% — but it's highly fixable with the right changes.",
        "value_prop": "Form friction audit: we identify every step where prospects drop off and show you what to change.",
        "cta": "Can I send a free form audit for [COMPANY]'s main lead capture or contact form?",
        "urgency_angle": "Fixing form friction is one of the fastest ROI moves in digital — one client went from 0.96% to 8.1%.",
    },
    # T3 — recurring revenue / retainer intent
    "website monitoring retainer services": {
        "email_subject": "Is anyone watching [COMPANY]'s site 24/7?",
        "email_opening": "Most sites go down, slow down, or break silently — and the business finds out from a frustrated customer.",
        "value_prop": "Monthly monitoring retainer: uptime, Core Web Vitals drift, security patches, and a monthly health report.",
        "cta": "Want to see what an active monitoring retainer would cover for [COMPANY]?",
        "urgency_angle": "Every minute of downtime is a missed lead. Reactive is always more expensive than proactive.",
    },
    "GDPR compliance website audit": {
        "email_subject": "GDPR exposure on [COMPANY]'s site — do you know your risk?",
        "email_opening": "If you have European visitors or customers, GDPR applies — and most US sites have silent violations.",
        "value_prop": "Free GDPR web-surface audit: consent mechanisms, data flows, and cookie compliance.",
        "cta": "Want the free GDPR risk snapshot for [COMPANY]'s current site?",
        "urgency_angle": "GDPR fines can reach 4% of global annual revenue. International FinTech/healthcare is highest risk.",
    },
    "website health checkup retainer": {
        "email_subject": "Does [COMPANY]'s site have a regular checkup?",
        "email_opening": "Websites drift — performance degrades, plugins get outdated, and compliance gaps widen quietly.",
        "value_prop": "Monthly health retainer: performance benchmarks, security checks, and compliance monitoring in one report.",
        "cta": "Should I send a sample monthly health report so you can see what proactive monitoring looks like?",
        "urgency_angle": "Set-it-and-forget-it is how sites end up with 3-year-old plugins and a HIPAA gap.",
    },
    "continuous vulnerability scanning": {
        "email_subject": "When was [COMPANY]'s site last scanned for vulnerabilities?",
        "email_opening": "Compliance frameworks are requiring ongoing scanning — not just annual audits.",
        "value_prop": "Continuous vulnerability scanning service: automated weekly scans + human triage on findings.",
        "cta": "Want a free initial vulnerability scan of [COMPANY]'s public-facing site?",
        "urgency_angle": "New HIPAA: vulnerability scans required every 6mo minimum. Multi-state compliance = perpetual obligation.",
    },
    "competitor ranking higher Google": {
        "email_subject": "[COMPANY]'s competitor is outranking you — here's why",
        "email_opening": "When a competitor outranks you, it's almost always a technical or authority gap — not a content gap.",
        "value_prop": "Free competitor gap audit: we show exactly what they have that you don't and what to fix first.",
        "cta": "Should I run a free competitor ranking comparison for [COMPANY]?",
        "urgency_angle": "Every day a competitor outranks you is compounding traffic and lead loss.",
    },
    "ADA lawsuit risk compliance check": {
        "email_subject": "Quick ADA lawsuit risk check for [COMPANY]",
        "email_opening": "ADA website lawsuits increased 37% in H1 2025 — most targets are small businesses who didn't know they were exposed.",
        "value_prop": "Free ADA lawsuit risk scan: we flag the specific violations most commonly cited in demand letters.",
        "cta": "Want the free ADA risk snapshot before a letter shows up?",
        "urgency_angle": "2,014 ADA lawsuits H1 2025. Most targets had no idea they were at risk until the demand letter arrived.",
    },
    "Section 508 compliance services": {
        "email_subject": "Section 508 compliance on [COMPANY]'s site — are you covered?",
        "email_opening": "Government contractors and federally funded organizations face mandatory Section 508 requirements.",
        "value_prop": "Free Section 508 compliance scan with a prioritized remediation checklist.",
        "cta": "Want the free 508 compliance scan for [COMPANY]'s site?",
        "urgency_angle": "Section 508 is a procurement mandate for government contracting — non-compliance disqualifies bids.",
    },
    "website navigation UX audit": {
        "email_subject": "Is [COMPANY]'s site navigation costing you leads?",
        "email_opening": "Confusing navigation is invisible to the owner but obvious to every new visitor — and it kills conversions.",
        "value_prop": "Navigation UX audit: path analysis, friction mapping, and a clear before/after recommendation.",
        "cta": "Can I send a free navigation audit for [COMPANY]'s top-traffic pages?",
        "urgency_angle": "Friction in navigation = conversion loss. Every extra click on the path to contact reduces conversion rate.",
    },
    "SEO strategy B2B": {
        "email_subject": "[COMPANY]'s B2B SEO strategy needs a 2025 update",
        "email_opening": "B2B search in 2025 is intent-driven, not volume-based — and most older SEO strategies miss this shift.",
        "value_prop": "Free B2B SEO audit: intent mapping, technical gaps, and a prioritized quick-win list.",
        "cta": "Should I send the free B2B SEO gap analysis for [COMPANY]?",
        "urgency_angle": "Gartner predicts 25% decline in search traffic by 2026. Strategy needs to shift now.",
    },
    "website performance consulting": {
        "email_subject": "Is [COMPANY]'s website working as hard as you are?",
        "email_opening": "A slow, broken, or non-converting site is a silent drain on every marketing dollar you spend.",
        "value_prop": "Performance consulting starts with a free full-stack audit: speed, SEO, conversion, compliance.",
        "cta": "Worth a 15-minute call to walk through what a performance audit would reveal for [COMPANY]?",
        "urgency_angle": "Web performance is compounding: fix it once and every ad, email, and SEO campaign performs better.",
    },
}

# ── A blank template used when a keyword_base has no mapped entry.
_EMPTY_TEMPLATE = {
    "email_subject": "",
    "email_opening": "",
    "value_prop": "",
    "cta": "",
    "urgency_angle": "",
}

def _get_outreach(keyword_base: str) -> dict:
    """Case-insensitive lookup; returns empty template on miss rather than crashing."""
    key = keyword_base.lower().strip()
    for k, v in OUTREACH_TEMPLATES.items():
        if k.lower() == key:
            return v
    # Fuzzy fallback: match on first significant token
    first_word = key.split()[0] if key else ""
    for k, v in OUTREACH_TEMPLATES.items():
        if k.lower().startswith(first_word) and first_word:
            return v
    return _EMPTY_TEMPLATE


REGIONS = {
    "atl_core": ["Buckhead", "Midtown Atlanta", "Virginia-Highland", "Peachtree Corners"],
    "atl_metro": ["Alpharetta", "Roswell", "Cumming", "Decatur", "Marietta", "Kennesaw"],
    "ga_state": ["Savannah", "Athens", "Augusta", "Macon"],
    "se_region": ["Charlotte NC", "Charleston SC", "Nashville TN", "Miami FL", "Dallas TX"],
}

ACTIVE_TIERS = ["T0", "T1", "T2", "T3"]
ACTIVE_REGIONS = ["atl_core", "atl_metro"]
MAX_KEYWORDS_PER_TIER = None
RESULTS_PER_QUERY = 15
PAUSE_BETWEEN_QUERIES = 1.5
MAX_SEARCHES_TOTAL = 20  # hard cap for this variant

def build_searches():
    searches = []
    for tier_id in ACTIVE_TIERS:
        kw_list = KEYWORD_TIERS[tier_id]
        if MAX_KEYWORDS_PER_TIER is not None:
            kw_list = kw_list[:MAX_KEYWORDS_PER_TIER]
        for kw in kw_list:
            has_city = "[CITY]" in kw
            for region_id in ACTIVE_REGIONS:
                if region_id == "us_wide":
                    continue
                for city in REGIONS.get(region_id, []):
                    if has_city:
                        query = kw.replace("[CITY]", city)
                        keyword_base = kw.replace("[CITY]", "").strip()
                    else:
                        query = f"{kw} {city}"
                        keyword_base = kw.strip()
                    searches.append({
                        "tier": tier_id,
                        "keyword_base": keyword_base,
                        "query": query,
                        "city": city,
                        "region_group": region_id,
                        "location": city,
                    })
    return searches

def fetch_places(api_key: str, query: str, location: str, limit: int = RESULTS_PER_QUERY):
    params = {
        "api_key": api_key,
        "engine": "google_maps",
        "type": "search",
        "q": query,
        "location": location,
        "hl": "en",
        "num": limit,
        "z": "10",
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    if "error" in results:
        print(f"[!] SerpAPI error for '{query}' @ '{location}': {results['error']}")
        return []
    local = results.get("local_results", [])
    if not local:
        print(f"[!] No local_results for '{query}' @ '{location}'. Keys: {list(results.keys())}")
    return local

def normalize_result(biz: dict, meta: dict) -> dict:
    lead = {
        "name": biz.get("title", "").strip(),
        "phone": biz.get("phone", "").strip(),
        "website": biz.get("website", "").strip(),
        "address": biz.get("address", "").strip(),
        "rating": biz.get("rating", ""),
        "reviews": biz.get("reviews", ""),
        "type": ", ".join(biz.get("type", [])) if isinstance(biz.get("type"), list) else biz.get("type", ""),
        "hours": biz.get("hours", ""),
        "keyword_base": meta["keyword_base"],
        "full_query": meta["query"],
        "city": meta["city"],
        "region_group": meta["region_group"],
        "tier": meta["tier"],
    }

    # ── Quality score (presence-based)
    score = 0
    if lead["website"]:
        score += 50
    if lead["phone"]:
        score += 30
    if lead["address"]:
        score += 10
    if lead["rating"]:
        score += 10
    lead["quality_score"] = score

    if score >= 90:
        lead["need_level"] = "prime_for_optimization"
    elif score >= 70:
        lead["need_level"] = "strong_candidate"
    elif score >= 40:
        lead["need_level"] = "high_need"
    else:
        lead["need_level"] = "critical_need"

    # ── Web-Ops ICP classification
    webops_icp_type, compliance_urgency = _classify_webops_icp(lead["type"])
    lead["webops_icp_type"] = webops_icp_type
    lead["compliance_urgency"] = compliance_urgency

    # ── Outreach columns — pre-loaded per keyword, swap [COMPANY] at send time
    outreach = _get_outreach(meta["keyword_base"])
    lead["email_subject"] = outreach["email_subject"]
    lead["email_opening"] = outreach["email_opening"]
    lead["value_prop"] = outreach["value_prop"]
    lead["cta"] = outreach["cta"]
    lead["urgency_angle"] = outreach["urgency_angle"]

    return lead

def main():
    api_key = load_api_key()
    searches = build_searches()
    print(f"[*] Built {len(searches)} keyword+city combos")
    all_leads = []
    for idx, s in enumerate(searches, 1):
        if MAX_SEARCHES_TOTAL is not None and idx > MAX_SEARCHES_TOTAL:
            print(f"\n[*] Reached MAX_SEARCHES_TOTAL={MAX_SEARCHES_TOTAL}, stopping early.")
            break
        print(f"[{idx}/{len(searches)}] {s['tier']} | {s['region_group']} | {s['city']} -> '{s['query']}'")
        results = fetch_places(api_key, s["query"], s["location"])
        for biz in results:
            all_leads.append(normalize_result(biz, s))
        if idx < len(searches):
            time.sleep(PAUSE_BETWEEN_QUERIES)

    print(f"\n[*] Total raw leads pulled: {len(all_leads)}")
    seen = set()
    unique_leads = []
    for lead in all_leads:
        key = (lead["name"].lower().strip(), lead["website"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_leads.append(lead)
    print(f"[*] Unique leads after de-dupe: {len(unique_leads)}")
    if not unique_leads:
        print("[!] No leads found.")
        return

    unique_leads.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "discovery"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now().strftime("%b-%d").lower()
    out_path = out_dir / f"{date_tag}_disc-leads.csv"
    fieldnames = [
        "name", "phone", "website", "address", "rating", "reviews",
        "type", "hours",
        "keyword_base", "full_query", "city", "region_group", "tier",
        "quality_score", "need_level",
        # ICP classification
        "webops_icp_type", "compliance_urgency",
        # outreach columns
        "email_subject", "email_opening", "value_prop", "cta", "urgency_angle",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_leads)

    by_need = {}
    for lead in unique_leads:
        lvl = lead["need_level"]
        by_need[lvl] = by_need.get(lvl, 0) + 1

    # T0 hot-switch count for quick visibility
    t0_count = sum(1 for l in unique_leads if l["tier"] == "T0")

    print("=" * 70)
    print("DISCOVERY COMPLETE (20-search variant)")
    print(f"   Output: {out_path}")
    print(f"   T0 hot-switch leads: {t0_count}")
    print("Need level breakdown:")
    for lvl, cnt in sorted(by_need.items(), key=lambda x: x[0]):
        pct = (cnt / len(unique_leads)) * 100
        print(f"  {lvl:22} {cnt:4d} ({pct:5.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()
