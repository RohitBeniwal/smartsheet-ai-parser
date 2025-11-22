"""
Configuration for Excel parser - patterns and keywords for flexible field detection
"""

# Field mapping patterns - maps standard field names to possible variations
FIELD_PATTERNS = {
    "order_number": [
        # Original patterns
        "io number", "io", "job", "order", "order #", "order number", 
        "po", "po number", "purchase order",
        # Extended patterns
        "work order", "ref number", "reference", "order id", "order no",
        "order code", "job number", "job #", "order ref", "po#",
        "purchase order number", "order no.", "job id", "work order #"
    ],
    "style": [
        # Original patterns
        "style", "style code", "style number", "style no", "article", 
        "article code", "item", "item code",
        # Extended patterns
        "product", "product code", "sku", "design", "design code",
        "model", "model number", "style #", "article #", "item #",
        "product number", "style id", "design number", "model code"
    ],
    "fabric": [
        # Original patterns
        "fabric", "fabric spec", "material", "fabric type", "composition",
        # Extended patterns
        "fabric specification", "fabric content", "material type",
        "fabric composition", "textile", "cloth", "material spec",
        "fabric description", "fabric details", "material composition"
    ],
    "color": [
        # Original patterns
        "color", "colour", "color way", "colorway", "shade",
        # Extended patterns
        "color code", "colour code", "color name", "colour name",
        "color description", "shade code", "color variant", "hue",
        "color id", "colour way", "tint", "tone"
    ],
    "quantity": [
        # Original patterns
        "quantity", "qty", "order qty", "total qty", "order quantity",
        # Extended patterns
        "amount", "volume", "count", "total", "order amount",
        "qty ordered", "order volume", "pieces", "units", "total units",
        "qty required", "required quantity", "qty needed", "pcs"
    ],
    "shipping_date": [
        # Original patterns
        "shipping", "shipping date", "handover", "handover date", 
        "delivery", "delivery date", "ship date",
        # Extended patterns
        "ship by", "delivery deadline", "due date", "target date",
        "expected delivery", "shipment date", "dispatch date",
        "send date", "shipping deadline", "delivery target"
    ],
}

# Milestone keywords - used to identify milestone columns
MILESTONE_KEYWORDS = [
    "fabric", "cutting", "sewing", "finishing", "embroidery", "printing",
    "washing", "packing", "shipping", "vap", "feeding", "size set",
    "knitting", "dyeing", "inspection"
]

# Sub-field patterns for milestones
MILESTONE_SUBFIELDS = {
    "required_weight": ["reqd wt", "required weight", "fabric reqd", "req wt"],
    "plan_date": ["plan date", "planned date", "target date", "schedule"],
    "quantity": ["qty", "quantity", "plan qty"],
    "supplier": ["supplier", "vendor", "source"],
    "plan": ["plan", "target", "scheduled"]
}

# Header detection keywords - used to identify header rows
HEADER_KEYWORDS = [
    "order", "style", "fabric", "color", "quantity", "date", 
    "number", "code", "shipping", "plan", "supplier", "job"
]

# Date format patterns for parsing
DATE_FORMATS = [
    "%d-%m-%y", "%d/%m/%y", "%d.%m.%y", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%m-%d-%y", "%m/%d/%y", "%m.%d.%y", "%m-%d-%Y", "%m/%d/%Y", "%m.%d.%Y",
    "%d.%m.%Y", "%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y",
    "%d-%m-%y", "%d/%m/%Y", "%Y/%m/%d"
]

# Maximum rows to check for headers
MAX_HEADER_SEARCH_ROWS = 10

# Minimum non-empty cells for a row to be considered a header
MIN_HEADER_CELLS = 4
