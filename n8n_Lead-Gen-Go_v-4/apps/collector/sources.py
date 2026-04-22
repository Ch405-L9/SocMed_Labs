"""
Business category search templates.
Maps category names → DuckDuckGo query fragments and keywords.
"""

CATEGORY_QUERIES = {
    "primary_care": {
        "label": "Primary Care",
        "queries": [
            "primary care doctor near {zip}",
            "family medicine physician {zip}",
            "internal medicine clinic near {zip}",
        ],
        "keywords": ["family practice", "primary care", "internal medicine", "family medicine"],
    },
    "dental": {
        "label": "Dental",
        "queries": [
            "dental office near {zip}",
            "dentist {zip} GA",
            "cosmetic dentistry near {zip}",
        ],
        "keywords": ["dental", "dentist", "orthodont", "oral"],
    },
    "chiropractic": {
        "label": "Chiropractic",
        "queries": [
            "chiropractor near {zip}",
            "chiropractic clinic {zip}",
        ],
        "keywords": ["chiropractic", "chiropractor", "spinal", "adjustment"],
    },
    "urgent_care": {
        "label": "Urgent Care",
        "queries": [
            "urgent care clinic near {zip}",
            "walk-in clinic {zip}",
        ],
        "keywords": ["urgent care", "walk-in", "immediate care"],
    },
    "physical_therapy": {
        "label": "Physical Therapy",
        "queries": [
            "physical therapy near {zip}",
            "PT clinic {zip}",
        ],
        "keywords": ["physical therapy", "physical therapist", "PT", "rehab"],
    },
    "specialty": {
        "label": "Specialty",
        "queries": [
            "specialist physician near {zip}",
            "medical specialist clinic {zip}",
        ],
        "keywords": ["specialty", "specialist", "cardiology", "dermatology", "orthopedic", "gastro", "obgyn"],
    },
    "wellness": {
        "label": "Wellness",
        "queries": [
            "wellness center near {zip}",
            "holistic health clinic {zip}",
        ],
        "keywords": ["wellness", "holistic", "integrative"],
    },
    "healthcare": {
        "label": "Healthcare (All)",
        "queries": [
            "healthcare provider near {zip}",
            "medical clinic near {zip}",
            "doctor office {zip} GA",
            "independent medical practice {zip}",
        ],
        "keywords": ["clinic", "medical", "health", "doctor", "physician", "practice"],
    },
}

BOOKING_SIGNALS = [
    "book appointment", "schedule appointment", "book online", "request appointment",
    "schedule visit", "online scheduling", "book now", "make appointment",
    "zocdoc", "healthgrades", "practicefusion", "athenahealth", "eclinicalworks",
    "open.epic", "mychart", "healow", "nextmd", "patientpop",
]

CONTACT_FORM_SIGNALS = [
    "contact us", "contact form", "send us a message", "get in touch",
    '<form', 'contact-form', 'contact_form',
]

SOCIAL_DOMAINS = {
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "twitter": "twitter.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
    "yelp": "yelp.com",
    "google": "g.co",
}

SEO_QUALITY_SIGNALS = {
    "strong": ["description", "og:title", "og:description", "canonical", "structured"],
    "weak_indicators": ["no title", "untitled", "coming soon", "parked", "for sale"],
}
