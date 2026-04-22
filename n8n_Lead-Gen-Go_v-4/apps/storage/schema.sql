CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    website TEXT,
    category TEXT,
    geo_area TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrichment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    website_status TEXT,              -- reachable / error / timeout / blocked / dns_failed
    http_code INTEGER,
    is_https INTEGER DEFAULT 0,
    booking_present INTEGER DEFAULT 0,
    contact_form INTEGER DEFAULT 0,
    seo_title TEXT,
    seo_description TEXT,
    has_seo INTEGER DEFAULT 0,
    social_links TEXT,                -- JSON array
    social_count INTEGER DEFAULT 0,
    page_summary TEXT,
    phone_numbers TEXT,               -- JSON array of extracted phone numbers
    primary_phone TEXT,               -- Best/first phone number found
    email_addresses TEXT,             -- JSON array of MX-verified emails
    primary_email TEXT,               -- Best/first verified email found
    mx_verified INTEGER DEFAULT 0,    -- 1 if at least one email domain passed MX check
    pagespeed_performance INTEGER,    -- 0-100 mobile performance score (null if not fetched)
    pagespeed_seo INTEGER,            -- 0-100 SEO score from PageSpeed API
    pagespeed_accessibility INTEGER,  -- 0-100 accessibility score from PageSpeed API
    last_crawled TEXT,                -- ISO timestamp of most recent crawl
    content_hash TEXT,                -- 16-char sha256 of page HTML at crawl time
    gbp_rating REAL,                  -- Google Business Profile average star rating
    gbp_review_count INTEGER,         -- Number of Google reviews (null if not found)
    gbp_photo_count INTEGER,          -- Number of GBP photos (null if not detectable)
    gbp_verified INTEGER DEFAULT 0,   -- 1 if GBP is claimed and has reviews
    gbp_unclaimed INTEGER DEFAULT 0,  -- 1 if GBP appears unclaimed (no reviews/rating found)
    enriched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    icp_score INTEGER,
    risk_level TEXT,
    reasoning TEXT,               -- JSON blob
    ollama_summary TEXT,
    model_used TEXT,
    prompt_version TEXT,              -- Template version used for LLM prompts (e.g. scoring_v1)
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS human_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    action TEXT,                  -- approve / modify / reject / skip
    override_score INTEGER,
    notes TEXT,
    human_verified INTEGER DEFAULT 0,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    channel TEXT NOT NULL,        -- email / phone / walk_in / linkedin / other
    contacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contact_person TEXT,          -- Name or role of person contacted
    notes TEXT,
    response TEXT DEFAULT 'no_response',  -- no_response / interested / not_interested / scheduled / bounced
    follow_up_date TEXT,          -- ISO date string YYYY-MM-DD, null if no follow-up planned
    logged_by TEXT DEFAULT 'user'
);

CREATE VIEW IF NOT EXISTS leads_full AS
SELECT
    l.id,
    l.business_name,
    l.website,
    l.category,
    l.geo_area,
    l.address,
    l.phone,
    l.email,
    e.website_status,
    e.is_https,
    e.booking_present,
    e.has_seo,
    e.social_count,
    e.primary_phone,
    e.primary_email,
    e.mx_verified,
    e.pagespeed_performance,
    e.pagespeed_seo,
    e.pagespeed_accessibility,
    e.last_crawled,
    e.content_hash,
    e.gbp_rating,
    e.gbp_review_count,
    e.gbp_verified,
    e.gbp_unclaimed,
    s.icp_score,
    s.risk_level,
    s.reasoning,
    s.ollama_summary,
    r.action       AS human_action,
    COALESCE(r.override_score, s.icp_score) AS final_score,
    r.human_verified,
    r.notes        AS human_notes
FROM leads l
LEFT JOIN enrichment e ON e.lead_id = l.id
LEFT JOIN scores s     ON s.lead_id = l.id
LEFT JOIN human_reviews r ON r.lead_id = l.id;

CREATE VIEW IF NOT EXISTS outreach_summary AS
SELECT
    l.id            AS lead_id,
    l.business_name,
    l.website,
    l.category,
    l.address,
    COALESCE(r.override_score, s.icp_score) AS final_score,
    s.risk_level,
    e.primary_phone,
    e.primary_email,
    COUNT(o.id)     AS contact_attempts,
    MAX(o.contacted_at) AS last_contacted,
    MAX(o.follow_up_date) AS next_follow_up,
    MAX(o.response) AS last_response,
    r.human_verified
FROM leads l
LEFT JOIN enrichment e    ON e.lead_id = l.id
LEFT JOIN scores s        ON s.lead_id = l.id
LEFT JOIN human_reviews r ON r.lead_id = l.id
LEFT JOIN outreach_log o  ON o.lead_id = l.id
GROUP BY l.id;
