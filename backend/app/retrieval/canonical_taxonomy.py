"""
Canonical Legal Domain Taxonomy for LexAgents.
Strictly defines the 11 supported core legal domains for the Core Legal Accuracy Sprint.
Single source of truth across all modules.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class DomainDefinition:
    domain_id: int
    name: str
    subdomains: List[str]
    keywords: List[str]
    likely_source_types: List[str]
    primary_authorities: List[str]
    related_domains: List[str]
    exclusion_signals: List[str]

SUPPORTED_DOMAINS: Dict[str, DomainDefinition] = {
    "Constitutional Law": DomainDefinition(
        domain_id=1,
        name="Constitutional Law",
        subdomains=[
            "Fundamental Rights",
            "Directive Principles",
            "Fundamental Duties",
            "Constitutional Bodies",
            "Judiciary",
            "Legislature",
            "Executive",
            "Union-State Relations",
            "Elections",
            "Emergency",
            "Constitutional Amendments",
            "Schedules"
        ],
        keywords=[
            "constitution", "article", "preamble", "fundamental right", "equality", "discrimination",
            "reservation", "life and liberty", "speech and expression", "writ", "habeas corpus",
            "mandamus", "certiorari", "quo warranto", "prohibition", "basic structure", "amendment",
            "schedule", "directive principles", "dpsp", "president", "governor", "ordinance",
            "parliament", "supreme court", "high court", "judicial review", "inter-state council",
            "finance commission", "election commission", "emergency", "part iii", "संविधान", "अनुच्छेद",
            "मौलिक अधिकार", "రాజ్యాంగం", "ఆర్టికల్", "ప్రాథమిక హక్కులు"
        ],
        likely_source_types=["constitutional", "constitutional_amendment", "sc_judgment", "hc_judgment"],
        primary_authorities=["Constituent Assembly of India", "Supreme Court of India", "High Courts"],
        related_domains=["Administrative Law", "Human Rights Law", "Civil Law"],
        exclusion_signals=[
            "car", "vehicle", "traffic", "accident", "cheque bounce", "promissory note",
            "rent agreement", "lease", "tenant", "landlord", "trademark", "patent", "copyright",
            "online scam", "phishing", "director duty", "company incorporation"
        ]
    ),

    "Criminal Law": DomainDefinition(
        domain_id=2,
        name="Criminal Law",
        subdomains=[
            "Offences Against Person",
            "Offences Against Property",
            "Offences Against Women",
            "Offences Against Children",
            "Economic Offences",
            "Cyber Offences",
            "Offences Against State",
            "Abetment",
            "Conspiracy",
            "Attempt",
            "General Exceptions",
            "Punishments"
        ],
        keywords=[
            "criminal", "offence", "crime", "theft", "murder", "culpable homicide", "grievous hurt",
            "assault", "kidnapping", "abduction", "rape", "cheating", "forgery", "extortion",
            "robbery", "dacoity", "criminal breach of trust", "misappropriation", "criminal conspiracy",
            "abetment", "mens rea", "actus reus", "general exceptions", "private defence", "insanity",
            "intoxication", "accident in doing lawful act", "rash or negligent act", "section 304a",
            "ipc", "indian penal code", "bharatiya nyaya sanhita", "bns", "अपराध", "चोरी", "हत्या",
            "నేరం", "దొంగతనం", "హత్య"
        ],
        likely_source_types=["central_act", "sc_judgment", "hc_judgment"],
        primary_authorities=["Supreme Court of India", "High Courts", "Sessions Court"],
        related_domains=["Criminal Procedure", "Motor Vehicle Law", "Women & Gender Justice", "Cyber & Technology Law"],
        exclusion_signals=[
            "shareholder agreement", "board meeting", "dividend", "defective goods",
            "consumer forum", "leave and license", "easement", "maternity benefit"
        ]
    ),

    "Criminal Procedure": DomainDefinition(
        domain_id=3,
        name="Criminal Procedure",
        subdomains=[
            "FIR",
            "Arrest",
            "Bail",
            "Investigation",
            "Search and Seizure",
            "Remand",
            "Charges",
            "Trial",
            "Summons",
            "Warrants",
            "Appeals",
            "Revision",
            "Limitation"
        ],
        keywords=[
            "fir", "first information report", "arrest", "bail", "anticipatory bail", "regular bail",
            "investigation", "police custody", "judicial custody", "remand", "charge sheet", "chargesheet",
            "framing of charges", "trial", "summons", "warrant", "search warrant", "seizure",
            "cognizable", "non-cognizable", "bailable", "non-bailable", "magistrate", "crpc",
            "code of criminal procedure", "bharatiya nagarik suraksha sanhita", "bnss", "section 437",
            "section 438", "section 439", "section 167", "section 154", "जमानत", "गिरफ्तारी",
            "प्राथमिकी", "బెయిల్", "అరెస్ట్"
        ],
        likely_source_types=["central_act", "sc_judgment", "hc_judgment"],
        primary_authorities=["Supreme Court of India", "High Courts", "Magistrate Courts"],
        related_domains=["Criminal Law", "Constitutional Law"],
        exclusion_signals=[
            "merger", "debenture", "defective television", "landlord tenant dispute",
            "maternity leave", "trademark infringement"
        ]
    ),

    "Civil Law": DomainDefinition(
        domain_id=4,
        name="Civil Law",
        subdomains=[
            "Civil Procedure",
            "Torts",
            "Negligence",
            "Damages",
            "Injunctions",
            "Declaratory Relief",
            "Recovery",
            "Civil Disputes"
        ],
        keywords=[
            "civil suit", "plaint", "written statement", "tort", "torts", "negligence", "damages",
            "compensation", "injunction", "temporary injunction", "permanent injunction",
            "declaratory suit", "recovery of money", "breach of duty", "duty of care", "contributory negligence",
            "inevitable accident", "act of god", "vis major", "strict liability", "absolute liability",
            "cpc", "code of civil procedure", "specific relief act", "limitation act", "दीवानी",
            "लापरवाही", "हर्जाना", "సివిల్", "నిర్లక్ష్యం", "నష్టపరిహారం"
        ],
        likely_source_types=["central_act", "sc_judgment", "hc_judgment"],
        primary_authorities=["Supreme Court of India", "High Courts", "Civil Courts"],
        related_domains=["Motor Vehicle Law", "Property & Land Law", "Corporate & Commercial Law"],
        exclusion_signals=[
            "fir", "bail", "arrest", "chargesheet", "penal punishment", "imprisonment"
        ]
    ),

    "Motor Vehicle Law": DomainDefinition(
        domain_id=5,
        name="Motor Vehicle Law",
        subdomains=[
            "Driving Licence",
            "Registration",
            "Traffic Offences",
            "Road Safety",
            "Accidents",
            "Compensation",
            "Insurance",
            "Liability",
            "Permits"
        ],
        keywords=[
            "motor vehicle", "car", "driving", "driver", "vehicle", "automobile", "scooter", "motorcycle",
            "truck", "bus", "driving licence", "license", "registration", "rc", "traffic offence",
            "road accident", "accident", "hit and run", "collision", "pole", "electric pole", "cattle",
            "cow", "animal on road", "swerve", "dashed", "compensation", "motor accidents claims tribunal",
            "mact", "third party insurance", "no fault liability", "drunken driving", "drunk driving",
            "drunk", "un drunk", "sober", "breath analyser", "motor vehicles act", "mva", "section 185",
            "section 166", "section 163a", "motor vehicle accident", "सड़क दुर्घटना", "वाहन", "ड्राइविंग",
            "డ్రైవింగ్", "మోటార్ వాహనం", "రోడ్డు ప్రమాదం"
        ],
        likely_source_types=["central_act", "rules", "sc_judgment", "hc_judgment"],
        primary_authorities=["Motor Accidents Claims Tribunal", "Ministry of Road Transport and Highways", "Supreme Court of India"],
        related_domains=["Civil Law", "Criminal Law", "Insurance Law"],
        exclusion_signals=[
            "article 15", "article 16", "article 19", "article 21", "fundamental rights",
            "workplace sexual harassment", "posh act", "insider trading", "upsi", "sebi",
            "cheque bounce", "section 138 ni act", "lease agreement", "eviction"
        ]
    ),

    "Women & Gender Justice": DomainDefinition(
        domain_id=6,
        name="Women & Gender Justice",
        subdomains=[
            "Workplace Sexual Harassment",
            "Domestic Violence",
            "Dowry",
            "Sexual Offences",
            "Trafficking",
            "Gender Discrimination",
            "Maternity",
            "Protection Orders",
            "Statutory Relief"
        ],
        keywords=[
            "sexual harassment", "workplace sexual harassment", "posh", "posh act", "internal complaints committee",
            "icc", "local complaints committee", "vishaka", "vishaka guidelines", "domestic violence",
            "pwdva", "protection of women from domestic violence", "dowry", "dowry prohibition", "dowry-related", "section 498a",
            "cruelty by husband", "shared household", "protection order", "maintenance for wife",
            "maternity benefit", "gender discrimination", "equal remuneration", "महिला", "घरेलू हिंसा",
            "दहेज", "यौन उत्पीड़न", "మహిళా సంరక్షణ", "లైంగిక వేధింపులు", "వరకట్నం"
        ],
        likely_source_types=["central_act", "rules", "sc_judgment", "hc_judgment"],
        primary_authorities=["Internal Complaints Committee", "Protection Officers", "Magistrate Courts", "Supreme Court of India"],
        related_domains=["Labour & Employment Law", "Criminal Law", "Constitutional Law"],
        exclusion_signals=[
            "motor vehicle", "driving licence", "traffic accident", "cheque bounce",
            "commercial dispute", "trademark", "patent"
        ]
    ),

    "Consumer Law": DomainDefinition(
        domain_id=7,
        name="Consumer Law",
        subdomains=[
            "Consumer Rights",
            "Defective Goods",
            "Deficient Services",
            "Unfair Trade Practices",
            "Product Liability",
            "Consumer Complaints",
            "Consumer Commissions"
        ],
        keywords=[
            "consumer", "consumer protection", "consumer rights", "defective goods", "deficiency in service",
            "deficient service", "unfair trade practice", "restrictive trade practice", "product liability",
            "consumer complaint", "district consumer forum", "district commission", "state commission",
            "ncdrc", "national consumer disputes redressal commission", "consumer protection act", "copra",
            "refund", "replacement", "misleading advertisement", "e-commerce consumer", "उपभोक्ता",
            "दोषपूर्ण सेवा", "వినియోగదారు", "లోపభూయిష్ట సేవ"
        ],
        likely_source_types=["central_act", "rules", "regulation", "sc_judgment"],
        primary_authorities=["District Consumer Commission", "State Commission", "NCDRC", "Central Consumer Protection Authority"],
        related_domains=["Civil Law", "Corporate & Commercial Law"],
        exclusion_signals=[
            "bail", "fir", "criminal murder", "article 15", "constitutional amendment",
            "road accident collision", "workplace harassment"
        ]
    ),

    "Cyber & Technology Law": DomainDefinition(
        domain_id=8,
        name="Cyber & Technology Law",
        subdomains=[
            "Cybercrime",
            "Online Fraud",
            "Electronic Records",
            "Digital Signatures",
            "Intermediaries",
            "Cybersecurity",
            "Technology Regulation"
        ],
        keywords=[
            "cyber", "cybercrime", "information technology act", "it act", "section 66", "section 66c",
            "section 66d", "section 66e", "section 67", "section 79", "intermediary liability",
            "online fraud", "phishing", "hacking", "unauthorized access", "electronic record",
            "electronic signature", "digital signature", "data theft", "upi fraud", "online scam",
            "online financial scam", "financial scam", "scam", "digital fraud", "cyber fraud", "cyber scam",
            "cert-in", "cyber security", "identity theft", "సైబర్ క్రైమ్", "సైబర్ భద్రత", "साइबर अपराध"
        ],
        likely_source_types=["central_act", "rules", "government_circular", "sc_judgment"],
        primary_authorities=["Adjudicating Officer under IT Act", "Cyber Appellate Tribunal", "CERT-In", "High Courts"],
        related_domains=["Criminal Law", "Data Protection & Privacy Law", "Corporate & Commercial Law"],
        exclusion_signals=[
            "road accident", "electric pole collision", "cow in road", "landlord eviction",
            "maternity benefit", "constitutional amendment"
        ]
    ),

    "Property & Land Law": DomainDefinition(
        domain_id=9,
        name="Property & Land Law",
        subdomains=[
            "Ownership",
            "Sale",
            "Transfer",
            "Lease",
            "Mortgage",
            "Registration",
            "Easement",
            "Land Acquisition",
            "Tenancy",
            "Real Estate"
        ],
        keywords=[
            "property", "land", "real estate", "ownership", "title", "sale deed", "transfer of property",
            "tpa", "transfer of property act", "lease", "lease agreement", "rent", "tenant", "landlord",
            "security deposit", "eviction", "licensor", "licensee", "mortgage", "registration act",
            "stamp duty", "easement", "land acquisition", "rera", "real estate regulatory authority",
            "adverse possession", "immovable property", "किराया", "जमीन", "पट्टा", "ఆస్తి", "భూమి", "అద్దె"
        ],
        likely_source_types=["central_act", "state_act", "sc_judgment", "hc_judgment", "user_upload"],
        primary_authorities=["Rent Controller", "RERA Authority", "Civil Courts", "Supreme Court of India"],
        related_domains=["Civil Law", "Corporate & Commercial Law"],
        exclusion_signals=[
            "traffic collision", "car driver", "breath analyser", "bail application",
            "workplace sexual harassment", "insider trading"
        ]
    ),

    "Labour & Employment Law": DomainDefinition(
        domain_id=10,
        name="Labour & Employment Law",
        subdomains=[
            "Wages",
            "Employment Conditions",
            "Industrial Disputes",
            "Termination",
            "Social Security",
            "Workplace Safety",
            "Maternity",
            "Employee Benefits"
        ],
        keywords=[
            "labour", "labor", "employment", "employee", "employer", "workman", "workmen", "wages",
            "minimum wages", "payment of wages", "industrial dispute", "industrial disputes act",
            "strike", "lockout", "layoff", "retrenchment", "unlawful termination", "wrongful termination",
            "fired without notice", "severance", "provident fund", "epfo", "esic", "gratuity",
            "payment of gratuity act", "workplace safety", "factories act", "trade union", "श्रमिक",
            "रोजगार", "वेतन", "కార్మిక చట్టం", "ఉద్యోగం", "వేతనాలు"
        ],
        likely_source_types=["central_act", "rules", "sc_judgment", "hc_judgment"],
        primary_authorities=["Labour Court", "Industrial Tribunal", "Labour Commissioner", "High Courts"],
        related_domains=["Women & Gender Justice", "Civil Law", "Constitutional Law"],
        exclusion_signals=[
            "motor car accident", "electric pole collision", "cheque dishonour", "online banking hack"
        ]
    ),

    "Corporate & Commercial Law": DomainDefinition(
        domain_id=11,
        name="Corporate & Commercial Law",
        subdomains=[
            "Company Formation",
            "Directors",
            "Shareholders",
            "Corporate Governance",
            "Corporate Compliance",
            "Mergers",
            "Contracts",
            "Sale of Goods",
            "Partnership",
            "Negotiable Instruments",
            "Commercial Disputes"
        ],
        keywords=[
            "company", "companies act", "corporate", "director", "duties of directors", "board of directors",
            "shareholder", "shares", "dividend", "merger", "acquisition", "corporate governance",
            "incorporation", "mca", "roc", "registrar of companies", "nclt", "nclat", "contract",
            "indian contract act", "breach of contract", "sale of goods act", "partnership act",
            "negotiable instruments act", "ni act", "section 138", "cheque bounce", "dishonour of cheque",
            "promissory note", "bill of exchange", "commercial court", "securities", "sebi", "insider trading",
            "upsi", "कंपनी", "निदेशक", "संविदा", "चेक बाउंस", "కంపెనీ", "కాంట్రాక్ట్", "చెక్ బౌన్స్", "చెక్కు బౌన్స్", "చెక్కు"
        ],
        likely_source_types=["central_act", "regulation", "government_circular", "sc_judgment"],
        primary_authorities=["Ministry of Corporate Affairs", "NCLT", "NCLAT", "SEBI", "Commercial Courts"],
        related_domains=["Civil Law", "Consumer Law"],
        exclusion_signals=[
            "traffic collision", "cow on road", "motor driving licence", "rape", "murder",
            "domestic violence"
        ]
    )
}

def get_domain(name: str) -> Optional[DomainDefinition]:
    """Retrieve domain definition by canonical name."""
    return SUPPORTED_DOMAINS.get(name)

def get_all_domains() -> List[DomainDefinition]:
    """Retrieve all 11 supported domains."""
    return list(SUPPORTED_DOMAINS.values())
