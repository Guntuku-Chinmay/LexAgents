"""
Corpus Coverage Registry for LexAgents.
Maintains factual, verifiable metadata on which statutes, regulations, and provisions
are currently indexed in the repository.

Principle:
DOMAIN EXISTS ≠ ACT INDEXED ≠ PROVISION INDEXED ≠ EVIDENCE AVAILABLE ≠ ANSWER VERIFIED
"""

from typing import Dict, List, Any

# Explicit registry of actual indexed corpus sources
INDEXED_CORPUS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "Constitutional Law": {
        "status": "INDEXED",
        "primary_act": "Constitution of India, 1950",
        "indexed_provisions": [
            "Preamble",
            "Articles 1 to 395 (Fundamental Rights, DPSP, Judiciary, Union-State, Amendments)",
            "Schedules 1 to 12"
        ],
        "indexed_files": ["constitution_of_india.txt", "constitution_of_india.meta.json"],
        "landmark_cases": [
            "K.S. Puttaswamy v. Union of India (2017) [Article 21, Privacy]",
            "Maneka Gandhi v. Union of India (1978) [Article 21, Procedure Established by Law]"
        ]
    },
    "Women & Gender Justice": {
        "status": "INDEXED",
        "primary_act": "Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 (POSH Act)",
        "indexed_provisions": [
            "Section 2 (Definitions)",
            "Section 4 (Constitution of Internal Complaints Committee)",
            "Section 9 (Complaint of Sexual Harassment)",
            "Section 10 (Conciliation)",
            "Section 11 (Inquiry into Complaint)",
            "Section 12 (Action during pendency of inquiry - Interim Relief)",
            "Section 13 (Inquiry report & Compensation)",
            "Section 18 (Appeal)",
            "Section 19 (Duties of Employer & criminal complaint)"
        ],
        "indexed_files": ["posh_act_2013.txt"],
        "landmark_cases": [
            "Vishaka v. State of Rajasthan (1997) [Workplace Sexual Harassment Guidelines]"
        ]
    },
    "Corporate & Commercial Law": {
        "status": "INDEXED",
        "primary_act": "Negotiable Instruments Act, 1881 & SEBI (PIT) Regulations, 2015",
        "indexed_provisions": [
            "Negotiable Instruments Act 1881: Section 138 (Dishonour of cheque for insufficiency of funds), Section 139, Section 141",
            "SEBI (Prohibition of Insider Trading) Regulations, 2015: Regulation 2(1)(n) (UPSI), Regulation 3, Regulation 4",
            "RBI Guidelines on Digital Lending, 2022"
        ],
        "indexed_files": [
            "negotiable_instruments_act_1881.txt",
            "sebi_insider_trading_regulations_2015.txt",
            "rbi_digital_lending_guidelines_2022.txt"
        ],
        "landmark_cases": [
            "Dalmia Cement v. Galaxy Traders (2001) [Section 138 mandatory 30-day notice timeline]"
        ]
    },
    "Property & Land Law": {
        "status": "PARTIALLY_INDEXED",
        "primary_act": "Sample Lease Agreement (Contractual Tenancy Provisions)",
        "indexed_provisions": [
            "Lease Agreement Clause 4, 8, 12 (Notice, Refund of Security Deposit, Cheque Dishonour Clauses)"
        ],
        "indexed_files": ["sample_lease_agreement.txt", "lease_clause_cleaning.txt"],
        "landmark_cases": []
    },
    "Motor Vehicle Law": {
        "status": "NOT_INDEXED",
        "primary_act": "Motor Vehicles Act, 1988",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "Motor Vehicles Act, 1988 and traffic accident precedents are not currently indexed in the local statutory vector store."
    },
    "Criminal Law": {
        "status": "NOT_INDEXED",
        "primary_act": "Indian Penal Code, 1860 / Bharatiya Nyaya Sanhita, 2023",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "General substantive penal code (theft, murder, conspiracy) is not currently indexed in the local statutory vector store."
    },
    "Criminal Procedure": {
        "status": "NOT_INDEXED",
        "primary_act": "Code of Criminal Procedure, 1973 / BNSS, 2023",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "Criminal procedural statutes (bail, FIR, remand) are not currently indexed in the local statutory vector store."
    },
    "Civil Law": {
        "status": "NOT_INDEXED",
        "primary_act": "Code of Civil Procedure, 1908 / Law of Torts",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "General civil procedure codes and tort law treatises are not currently indexed in the local statutory vector store."
    },
    "Consumer Law": {
        "status": "NOT_INDEXED",
        "primary_act": "Consumer Protection Act, 2019",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "Consumer Protection Act, 2019 provisions are not currently indexed in the local statutory vector store."
    },
    "Cyber & Technology Law": {
        "status": "NOT_INDEXED",
        "primary_act": "Information Technology Act, 2000",
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": "Information Technology Act, 2000 provisions are not currently indexed in the local statutory vector store."
    },
    "Labour & Employment Law": {
        "status": "PARTIALLY_INDEXED",
        "primary_act": "POSH Act 2013 (Workplace conditions)",
        "indexed_provisions": ["POSH Act Section 4, 9, 12, 19"],
        "indexed_files": ["posh_act_2013.txt"],
        "landmark_cases": ["Vishaka v. State of Rajasthan (1997)"],
        "coverage_gap_note": "General Industrial Disputes Act, Factories Act, and Minimum Wages Act are not currently indexed."
    }
}

def get_coverage(domain_name: str) -> Dict[str, Any]:
    """Retrieve indexed coverage status for a legal domain."""
    return INDEXED_CORPUS_REGISTRY.get(domain_name, {
        "status": "NOT_INDEXED",
        "primary_act": None,
        "indexed_provisions": [],
        "indexed_files": [],
        "landmark_cases": [],
        "coverage_gap_note": f"Domain '{domain_name}' has no indexed authoritative files in local repository."
    })

def is_domain_indexed(domain_name: str) -> bool:
    """Check if domain has authoritative primary provisions in the local corpus."""
    cov = get_coverage(domain_name)
    return cov["status"] in ("INDEXED", "PARTIALLY_INDEXED")
