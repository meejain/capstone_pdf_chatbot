"""
Generates a synthetic enterprise document set for the fictional company "Veridian Systems Inc."
(policies, manuals, reports). Every document contains concrete, checkable facts so that the
chatbot can be demonstrated and evaluated with ground-truth questions.

Run:  python scripts/generate_synthetic_pdfs.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "pdfs" / "company"
COMPANY = "Veridian Systems Inc."
BRAND = colors.HexColor("#0B5CAD")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], textColor=BRAND, fontSize=22, leading=26)
SUB = ParagraphStyle("SUB", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.grey, fontSize=11)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=BRAND, spaceBefore=10)
BODY = ParagraphStyle("BODY", parent=styles["BodyText"], fontSize=10.5, leading=15)


def T(rows):
    return ("table", rows)


def B(items):
    return ("bullets", items)


# --------------------------------------------------------------------------------------------
# Document content.  Each doc: file, title, code, owner, effective, sections[(heading, blocks)]
# --------------------------------------------------------------------------------------------
DOCS = [
    dict(file="VS-HR-001_Employee_Leave_Policy.pdf", title="Employee Leave Policy", code="VS-HR-001",
         owner="People Operations", effective="1 January 2026", sections=[
        ("1. Purpose", ["This policy defines the types of paid and unpaid leave available to all full-time and part-time employees of Veridian Systems Inc. It applies to every office location, including Bengaluru, Austin, Dublin and Singapore."]),
        ("2. Annual (Earned) Leave", ["Full-time employees accrue 24 days of paid annual leave per calendar year, credited at 2 days per completed month of service. Part-time employees accrue leave on a pro-rata basis.",
            "A maximum of 10 unused annual-leave days may be carried forward into the next calendar year. Carried-forward days must be used by 31 March, after which they lapse. Employees may encash up to 5 days of unused leave once per year at their basic daily rate.",
            "Leave of more than 5 consecutive working days must be requested at least 14 calendar days in advance through the Workday portal."]),
        ("3. Sick Leave", ["Employees receive 12 days of paid sick leave per year. Sick leave does not carry forward. A medical certificate is required for any sick-leave absence longer than 3 consecutive working days."]),
        ("4. Parental Leave", ["Birthing parents are entitled to 26 weeks of fully paid parental leave. Non-birthing parents (including adoptive parents) are entitled to 12 weeks of fully paid parental leave, which may be taken in up to two blocks within 12 months of the child's arrival.",
            "Employees returning from parental leave may opt for a phased return: 60% working hours on full pay for the first 4 weeks."]),
        ("5. Other Leave Types", [T([["Leave type", "Entitlement", "Notes"],
                                     ["Bereavement", "5 days", "Immediate family; 2 days for extended family"],
                                     ["Marriage", "3 days", "Once during employment"],
                                     ["Volunteering", "2 days / year", "Registered non-profits only"],
                                     ["Jury / civic duty", "As required", "Proof of summons needed"],
                                     ["Sabbatical", "Up to 3 months unpaid", "After 5 years of service"],
                                     ["Public holidays", "11 days", "Location-specific calendar"]])]),
        ("6. Approval and Escalation", ["All leave is approved by the employee's direct manager. Disputes are escalated to the HR Business Partner, whose decision is final. Questions about this policy should be emailed to leave@veridian.example."]),
    ]),
    dict(file="VS-HR-002_Remote_and_Hybrid_Work_Policy.pdf", title="Remote and Hybrid Work Policy", code="VS-HR-002",
         owner="People Operations", effective="1 March 2025", sections=[
        ("1. Overview", ["Veridian Systems operates a hybrid-first model. The default arrangement for office-eligible roles is a minimum of 2 in-office days per week, with Tuesday designated as the company-wide 'anchor day' when all teams are expected on site."]),
        ("2. Eligibility", ["Employees who have completed their 90-day probation period may apply for a fully remote arrangement. Fully remote requests require approval from both the department head and the HR Business Partner and are reviewed every 12 months."]),
        ("3. Core Hours", ["Regardless of location, employees must be available for collaboration during core hours of 10:00 to 15:00 in their local time zone."]),
        ("4. Home Office Stipend", ["Hybrid employees receive a one-time home-office setup stipend of USD 600 (or local equivalent). Fully remote employees receive USD 1,000 for setup plus a monthly internet and utilities allowance of USD 50.",
            "Company laptops, monitors and headsets remain the property of Veridian Systems and must be returned within 10 working days of separation."]),
        ("5. Working from Abroad", ["Employees may work from a country other than their country of employment for a maximum of 30 calendar days in any rolling 12-month period, subject to prior approval by Legal and Payroll to avoid tax and immigration issues."]),
        ("6. Security Requirements", [B(["Always connect through the corporate VPN (GlobalProtect).",
                                         "Never work on confidential data in public spaces without a privacy screen.",
                                         "Lock your screen when stepping away; auto-lock is enforced after 5 minutes.",
                                         "Report lost devices to the IT Service Desk within 1 hour."])]),
    ]),
    dict(file="VS-FIN-003_Travel_and_Expense_Policy.pdf", title="Travel and Expense Reimbursement Policy", code="VS-FIN-003",
         owner="Finance", effective="1 April 2025", sections=[
        ("1. Scope", ["This policy governs business travel and the reimbursement of out-of-pocket business expenses for all employees and contractors traveling on behalf of Veridian Systems."]),
        ("2. Air Travel", ["Economy class is mandatory for flights shorter than 6 hours. Premium economy is permitted for flights between 6 and 10 hours, and business class is permitted only for flights longer than 10 hours or with VP approval. Flights must be booked at least 14 days in advance through the corporate travel portal (Navan)."]),
        ("3. Hotels and Per Diem", [T([["City tier", "Max hotel / night", "Meal per diem / day"],
                                       ["Tier 1 (New York, London, Singapore)", "USD 300", "USD 90"],
                                       ["Tier 2 (Austin, Dublin, Bengaluru)", "USD 200", "USD 65"],
                                       ["Tier 3 (all other cities)", "USD 150", "USD 50"]]),
                                    "Alcohol is not reimbursable unless part of an approved client entertainment event."]),
        ("4. Ground Transport", ["Ride-hailing and taxis are reimbursable. Personal car use is reimbursed at USD 0.67 per mile (INR 12 per km in India). Car rentals require a compact or mid-size class unless traveling with 3 or more colleagues."]),
        ("5. Submitting Claims", ["Expense claims must be submitted in Concur within 30 days of the expense date. Itemised receipts are required for any single expense above USD 25. Claims older than 90 days will not be reimbursed. Approved claims are paid in the next payroll cycle."]),
        ("6. Approval Limits", [T([["Claim amount", "Approver"],
                                   ["Up to USD 1,000", "Direct manager"],
                                   ["USD 1,001 - 5,000", "Department head"],
                                   ["Above USD 5,000", "CFO"]])]),
    ]),
    dict(file="VS-LGL-004_Code_of_Business_Conduct.pdf", title="Code of Business Conduct", code="VS-LGL-004",
         owner="Legal and Compliance", effective="1 January 2025", sections=[
        ("1. Our Values", ["Veridian's four values are Integrity First, Customer Obsession, Build Boldly and One Team. Every employee, contractor and board member is expected to act according to this Code."]),
        ("2. Gifts and Hospitality", ["Employees may accept gifts or hospitality with a value up to USD 100 per giver per year. Anything above USD 100 must be declared in the Gifts Register within 5 working days and approved by Compliance. Cash or cash equivalents (gift cards) may never be accepted."]),
        ("3. Conflicts of Interest", ["Employees must disclose any outside employment, board membership or financial interest of more than 1% in a supplier, customer or competitor. Disclosures are made annually in the Compliance portal and whenever circumstances change."]),
        ("4. Anti-Bribery", ["Veridian has zero tolerance for bribery and facilitation payments in every country, consistent with the US FCPA and the UK Bribery Act."]),
        ("5. Speak-Up Hotline", ["Concerns can be raised confidentially and anonymously through the Speak-Up Hotline, operated by an independent third party and available 24x7 in 14 languages at speakup.veridian.example or by phone. Retaliation against anyone raising a concern in good faith is a dismissible offence."]),
        ("6. Training", ["All employees must complete Code of Conduct training within 30 days of joining and annually thereafter by 31 October."]),
    ]),
    dict(file="VS-IT-005_Information_Security_Policy.pdf", title="Information Security Policy", code="VS-IT-005",
         owner="Chief Information Security Officer", effective="15 February 2025", sections=[
        ("1. Purpose", ["This policy protects the confidentiality, integrity and availability of Veridian's information assets. It is aligned to ISO/IEC 27001:2022 and the NIST Cybersecurity Framework 2.0."]),
        ("2. Data Classification", [T([["Class", "Examples", "Handling"],
                                       ["Public", "Marketing site, press releases", "No restrictions"],
                                       ["Internal", "Org charts, wikis", "Employees only"],
                                       ["Confidential", "Customer contracts, source code", "Need-to-know, encrypted at rest"],
                                       ["Restricted", "Payment data, health data, keys", "Named access, encrypted, logged"]])]),
        ("3. Passwords and Authentication", ["Passwords must be at least 14 characters long. Multi-factor authentication (MFA) is mandatory for all systems; hardware security keys (FIDO2) are required for administrators. Passwords are not force-rotated unless a compromise is suspected."]),
        ("4. Access Reviews", ["Managers review their team's access rights every quarter. Access for leavers is revoked within 4 hours of separation."]),
        ("5. Patching", ["Critical vulnerabilities (CVSS 9.0 or above) must be patched within 72 hours; high vulnerabilities within 14 days; medium within 30 days."]),
        ("6. Security Awareness", ["Phishing simulations are run monthly. Employees who fail two simulations in a quarter are enrolled in mandatory refresher training. Suspicious emails should be reported with the 'Report Phish' button in Outlook."]),
    ]),
    dict(file="VS-LGL-006_Data_Privacy_and_Retention_Policy.pdf", title="Data Privacy and Retention Policy", code="VS-LGL-006",
         owner="Data Protection Officer", effective="1 June 2025", sections=[
        ("1. Principles", ["Veridian processes personal data lawfully, fairly and transparently in line with GDPR, the India DPDP Act 2023 and the CCPA. Personal data is collected only for specified purposes and minimised."]),
        ("2. Data Subject Requests", ["Requests for access, correction or deletion of personal data must be fulfilled within 30 days. Requests are logged in the Privacy Request Tracker and routed to the Data Protection Officer (dpo@veridian.example)."]),
        ("3. Breach Notification", ["Any suspected personal-data breach must be reported to the Security Operations Centre immediately. Where required, the relevant regulator is notified within 72 hours of Veridian becoming aware of the breach."]),
        ("4. Retention Schedule", [T([["Record type", "Retention period"],
                                     ["Customer contracts", "7 years after contract end"],
                                     ["Financial and tax records", "8 years"],
                                     ["Employee personnel files", "6 years after separation"],
                                     ["Job applicant data (unsuccessful)", "12 months"],
                                     ["CCTV footage", "30 days"],
                                     ["Application logs", "13 months"]])]),
        ("5. International Transfers", ["Transfers of personal data outside the EEA rely on the EU Standard Contractual Clauses and a documented transfer impact assessment."]),
    ]),
    dict(file="VS-HR-007_Employee_Onboarding_Handbook.pdf", title="Employee Onboarding Handbook", code="VS-HR-007",
         owner="People Operations", effective="1 January 2026", sections=[
        ("Welcome to Veridian", ["Veridian Systems Inc. was founded in 2012 in Austin, Texas by Maya Raghunathan and Daniel Okafor. Today we employ approximately 4,800 people across 4 global hubs and serve more than 3,200 enterprise customers with our cloud data platform, Veridian Cloud."]),
        ("Your First Week", [B(["Day 1: Laptop pickup, IT setup and security briefing (09:30, Reception).",
                                "Day 2: Meet your onboarding buddy and complete Workday profile.",
                                "Day 3: Product deep-dive session with the Solutions team.",
                                "Day 4: Code of Conduct and Information Security e-learning.",
                                "Day 5: 1:1 with your manager to agree your 30-60-90 day plan."])]),
        ("Probation", ["All new employees serve a 90-day probation period. A formal probation review takes place in week 12."]),
        ("Key Tools", [T([["Need", "Tool"], ["HR, leave, payroll", "Workday"], ["Expenses", "Concur"], ["Travel", "Navan"],
                          ["Chat", "Slack"], ["IT tickets", "ServiceNow (help.veridian.example)"], ["Code", "GitHub Enterprise"]])]),
        ("Getting Help", ["The IT Service Desk is available 24x7 at extension 4357 (HELP). For HR questions, contact your HR Business Partner or ask 'Vera', the internal HR assistant in Slack."]),
    ]),
    dict(file="VS-HR-008_Performance_Review_and_Promotion_Guidelines.pdf", title="Performance Review and Promotion Guidelines", code="VS-HR-008",
         owner="People Operations", effective="1 January 2026", sections=[
        ("1. Review Cycle", ["Veridian runs two review cycles per year: a mid-year check-in in July and an annual review in January. Annual reviews determine merit increases, bonuses and promotions."]),
        ("2. Rating Scale", [T([["Rating", "Label", "Typical distribution"],
                               ["5", "Exceptional", "~10%"], ["4", "Exceeds expectations", "~25%"],
                               ["3", "Meets expectations", "~55%"], ["2", "Partially meets", "~8%"], ["1", "Does not meet", "~2%"]])]),
        ("3. Promotion Eligibility", ["To be considered for promotion an employee must have at least 12 months in their current level and a rating of 4 or above in the most recent annual review. Promotions are calibrated by a cross-functional committee and become effective on 1 April."]),
        ("4. Bonus", ["The annual bonus target is 10% of base salary for individual contributors and 15% to 25% for managers, multiplied by a company performance factor (0 to 1.5) and an individual factor based on rating."]),
        ("5. Performance Improvement Plans", ["Employees rated 1 are placed on a 60-day Performance Improvement Plan (PIP) with clear, measurable goals and bi-weekly check-ins."]),
    ]),
    dict(file="VS-HR-009_Employee_Benefits_Guide_2026.pdf", title="Employee Benefits Guide 2026", code="VS-HR-009",
         owner="Total Rewards", effective="1 January 2026", sections=[
        ("Health Insurance", ["Veridian pays 90% of medical premiums for employees and 75% for dependants. In India, group medical cover is INR 10 lakh per family per year, including parents or parents-in-law."]),
        ("Retirement", ["US employees: 401(k) match of 100% on the first 4% of salary plus 50% on the next 2%. India employees: statutory Provident Fund plus a voluntary NPS contribution option."]),
        ("Wellbeing", [B(["Wellness allowance of USD 75 per month for gym, yoga or mental-health apps.",
                          "Free, confidential Employee Assistance Programme (EAP) with 8 counselling sessions per year.",
                          "Company-wide 'Recharge Fridays': the last Friday of each quarter is a paid day off."])]),
        ("Learning", ["Each employee has an annual learning budget of USD 1,500 for courses, certifications and conferences. Tuition support of up to USD 5,000 per year is available for degree programs, with a 12-month retention clause."]),
        ("Equity", ["Eligible employees receive Restricted Stock Units (RSUs) that vest over 4 years with a 1-year cliff (25% after year one, then quarterly)."]),
    ]),
    dict(file="VS-IT-010_Incident_Response_Runbook.pdf", title="Security Incident Response Runbook", code="VS-IT-010",
         owner="Security Operations Centre", effective="1 May 2025", sections=[
        ("1. Severity Levels", [T([["Severity", "Definition", "Response time", "Update cadence"],
                                   ["SEV-1", "Active breach or full outage of Veridian Cloud", "15 minutes", "Every 30 min"],
                                   ["SEV-2", "Partial outage or contained intrusion", "1 hour", "Every 2 hours"],
                                   ["SEV-3", "Minor issue, no customer impact", "1 business day", "Daily"],
                                   ["SEV-4", "Informational / false positive", "3 business days", "On closure"]])]),
        ("2. Response Phases", ["The runbook follows six phases: Preparation, Detection & Analysis, Containment, Eradication, Recovery and Post-Incident Review, based on NIST SP 800-61."]),
        ("3. Roles", [B(["Incident Commander (IC): owns decisions and communications.",
                         "Technical Lead: coordinates investigation and remediation.",
                         "Communications Lead: drafts internal, customer and regulator updates.",
                         "Scribe: maintains the timeline in the incident channel."])]),
        ("4. Post-Incident Review", ["A blameless post-incident review is mandatory for every SEV-1 and SEV-2 incident and must be published within 5 business days of resolution."]),
        ("5. Contacts", ["The SOC is staffed 24x7. Page the on-call IC through PagerDuty service 'VS-SEC-IC' or call the SOC hotline at extension 7111."]),
    ]),
    dict(file="VS-FIN-011_Procurement_and_Vendor_Management_Policy.pdf", title="Procurement and Vendor Management Policy", code="VS-FIN-011",
         owner="Procurement", effective="1 July 2025", sections=[
        ("1. Purchase Thresholds", [T([["Purchase value", "Requirement"],
                                       ["Up to USD 10,000", "1 quote, manager approval"],
                                       ["USD 10,001 - 100,000", "3 competitive quotes, department head approval"],
                                       ["Above USD 100,000", "Formal RFP, Procurement Committee and CFO approval"]])]),
        ("2. Vendor Onboarding", ["New vendors must pass a security and privacy risk assessment before receiving any Confidential or Restricted data. Vendors handling Restricted data must hold SOC 2 Type II or ISO 27001 certification."]),
        ("3. Payment Terms", ["Standard payment terms are Net 45 days from invoice receipt. Small and diverse suppliers are paid on Net 15 terms."]),
        ("4. Sustainability", ["Veridian targets 50% of procurement spend with suppliers that have science-based emission targets by 2028."]),
    ]),
    dict(file="VS-OPS-012_Workplace_Health_and_Safety_Manual.pdf", title="Workplace Health and Safety Manual", code="VS-OPS-012",
         owner="Workplace Operations", effective="1 January 2025", sections=[
        ("1. Emergency Procedures", ["On hearing the fire alarm, leave by the nearest marked exit, do not use lifts and proceed to the assembly point. In the Bengaluru office the assembly point is the north parking lot (Gate 2); in Austin it is the plaza on Congress Avenue."]),
        ("2. First Aid", ["Each floor has at least two trained first-aiders, listed on the floor notice board. Automated External Defibrillators (AEDs) are located next to every lift lobby."]),
        ("3. Incident Reporting", ["All injuries, near-misses and hazards must be reported in the EHS portal within 24 hours."]),
        ("4. Ergonomics", ["Employees can request an ergonomic assessment at any time. Sit-stand desks are standard in all offices since 2024."]),
        ("5. Fire Drills", ["Fire evacuation drills are conducted twice a year in every office."]),
    ]),
    dict(file="VS-IT-013_Generative_AI_Acceptable_Use_Policy.pdf", title="Generative AI Acceptable Use Policy", code="VS-IT-013",
         owner="AI Governance Council", effective="1 September 2025", sections=[
        ("1. Approved Tools", ["Approved generative AI tools are Veridian Copilot (internal, based on a locally hosted Gemma 3 model), GitHub Copilot Enterprise and Microsoft 365 Copilot. Use of any other public AI tool with company data is prohibited."]),
        ("2. Data Rules", ["Restricted data (payment data, health data, credentials) must never be entered into any AI tool. Confidential data may only be used with approved tools."]),
        ("3. Human Review", ["AI-generated output must be reviewed by a human before it is shared with customers, published, or merged into production code. Employees remain accountable for the work they submit."]),
        ("4. Governance", ["New AI use cases with customer impact must be registered with the AI Governance Council, which follows the NIST AI Risk Management Framework (AI RMF 1.0) functions: Govern, Map, Measure and Manage."]),
        ("5. Training", ["All employees must complete the 'Responsible AI at Veridian' course (45 minutes) before using approved AI tools."]),
    ]),
    dict(file="AeroBrew_X1_Smart_Coffee_Machine_User_Manual.pdf", title="AeroBrew X1 Smart Coffee Machine - User Manual", code="AB-X1-UM-v2.1",
         owner="Veridian Home Devices", effective="Model year 2025", sections=[
        ("Specifications", [T([["Item", "Value"], ["Water tank", "1.8 litres"], ["Bean hopper", "250 g"], ["Pump pressure", "15 bar"],
                               ["Power", "1450 W, 220-240 V"], ["Grinder", "Conical steel burr, 12 settings"], ["Connectivity", "Wi-Fi 2.4 GHz, AeroBrew app"]])]),
        ("Getting Started", ["Rinse the water tank, fill it with fresh cold water up to the MAX line and fill the bean hopper. Press and hold the power button for 2 seconds. The machine heats up in about 40 seconds and performs an automatic rinse."]),
        ("Descaling", ["Descale the machine every 3 months, or when the orange descaling light turns on. Use only AeroBrew descaling solution: mix 100 ml of solution with 500 ml of water, place a 1-litre container under the spout, then hold the CLEAN and STEAM buttons together for 5 seconds. The cycle takes approximately 25 minutes."]),
        ("Error Codes", [T([["Code", "Meaning", "Solution"], ["E01", "Water tank empty", "Refill the water tank"],
                           ["E02", "Bean hopper empty", "Refill beans"], ["E03", "Brewing unit not inserted", "Re-insert and lock the brewing unit"],
                           ["E05", "Grinder blocked", "Switch off, clean the burr with the supplied brush"], ["E07", "Overheating", "Switch off and wait 30 minutes"]])]),
        ("Warranty", ["The AeroBrew X1 is covered by a 2-year limited warranty from the date of purchase. Using non-AeroBrew descaling products voids the warranty for the heating element."]),
    ]),
    dict(file="SkyNote_Pro_11_Tablet_Quick_Start_Guide.pdf", title="SkyNote Pro 11 Tablet - Quick Start and Troubleshooting Guide", code="SN-P11-QSG",
         owner="Veridian Devices", effective="Rev. C, 2025", sections=[
        ("In the Box", [B(["SkyNote Pro 11 tablet", "SkyPen stylus (magnetic)", "45 W USB-C fast charger", "USB-C cable (1 m)"])]),
        ("Key Specifications", [T([["Feature", "Value"], ["Display", "11-inch 2.8K OLED, 120 Hz"], ["Battery", "8,600 mAh, up to 14 hours video"],
                                   ["Charging", "0 to 100% in about 95 minutes with 45 W charger"], ["Storage", "256 GB / 512 GB"], ["Weight", "490 g"]])]),
        ("Pairing the SkyPen", ["Attach the SkyPen to the magnetic strip on the long edge of the tablet. A pairing prompt appears within 3 seconds; tap Connect. The pen charges while attached and lasts about 10 hours."]),
        ("Troubleshooting", [B(["Tablet will not turn on: charge for at least 30 minutes, then hold Power + Volume Down for 12 seconds to force a restart.",
                                "Screen unresponsive: remove any screen protector thicker than 0.3 mm.",
                                "Factory reset: Settings > System > Reset > Erase all data. Back up your notes first."])]),
        ("Warranty and Support", ["The tablet carries a 1-year limited warranty, extendable to 3 years with SkyCare+. Support: support.skynote.example or call 1-800-555-0119."]),
    ]),
    dict(file="SolarGrid_5kW_Hybrid_Inverter_Installation_Manual.pdf", title="SolarGrid 5kW Hybrid Inverter - Installation Manual", code="SG-5KH-IM",
         owner="Veridian Energy", effective="Version 1.4", sections=[
        ("Safety Warnings", ["Installation must be performed by a licensed electrician. Disconnect both AC and DC sources and wait at least 5 minutes before opening the enclosure, as capacitors may hold dangerous voltage."]),
        ("Technical Data", [T([["Parameter", "Value"], ["Rated AC output", "5,000 W"], ["Max PV input power", "6,500 W"],
                               ["MPPT voltage range", "120 - 500 V DC"], ["Number of MPPT trackers", "2"], ["Battery voltage", "48 V (LiFePO4 recommended)"],
                               ["Peak efficiency", "97.6%"], ["Ingress protection", "IP65"], ["Operating temperature", "-25 to +60 C"]])]),
        ("Mounting", ["Mount the inverter vertically on a solid wall, out of direct sunlight, with at least 30 cm clearance above and below and 20 cm on each side. The unit weighs 22 kg."]),
        ("Commissioning", ["After wiring, switch on the battery breaker first, then the DC isolator, and finally the AC breaker. Configure the grid code through the SolarGrid app within 10 minutes of power-up."]),
        ("Warranty", ["The standard warranty is 10 years, provided the unit is registered within 90 days of installation."]),
    ]),
    dict(file="Veridian_Cloud_API_Developer_Guide_v3.pdf", title="Veridian Cloud API - Developer Guide v3", code="VC-API-v3",
         owner="Developer Relations", effective="Release 3.2 (2025)", sections=[
        ("Authentication", ["All requests use OAuth 2.0 client-credentials. Obtain a token from https://auth.veridian.example/oauth/token; access tokens expire after 60 minutes. Send the token in the 'Authorization: Bearer <token>' header."]),
        ("Base URL and Versioning", ["The base URL is https://api.veridian.example/v3. Breaking changes are only introduced in a new major version, and previous major versions are supported for 18 months after a new release."]),
        ("Rate Limits", [T([["Plan", "Requests per minute", "Burst"], ["Free", "60", "10"], ["Team", "600", "100"], ["Enterprise", "6,000", "1,000"]]),
                         "Exceeding the limit returns HTTP 429 with a 'Retry-After' header. Clients should use exponential back-off."]),
        ("Core Endpoints", [T([["Method", "Endpoint", "Purpose"], ["GET", "/datasets", "List datasets"], ["POST", "/datasets", "Create a dataset"],
                               ["POST", "/datasets/{id}/query", "Run a SQL query"], ["GET", "/jobs/{id}", "Check job status"], ["DELETE", "/datasets/{id}", "Delete a dataset"]])]),
        ("Pagination and Errors", ["List endpoints use cursor pagination with a default page size of 50 and a maximum of 500. Errors follow RFC 7807 problem-details JSON."]),
        ("Webhooks", ["Webhooks are signed with HMAC-SHA256 using the header 'X-Veridian-Signature'. Failed deliveries are retried up to 8 times over 24 hours."]),
    ]),
    dict(file="Veridian_QBR_Q1_FY2026.pdf", title="Quarterly Business Review - Q1 FY2026", code="QBR-Q1-FY26",
         owner="Office of the CFO", effective="Quarter ended 31 March 2026", sections=[
        ("Executive Summary", ["Q1 FY2026 revenue was USD 412 million, up 18% year over year, driven by Veridian Cloud consumption growth. Operating margin was 21.5%. We added 140 net new enterprise customers."]),
        ("Financial Highlights", [T([["Metric", "Q1 FY2026", "Q1 FY2025", "YoY"], ["Revenue", "USD 412M", "USD 349M", "+18%"],
                                     ["Cloud revenue", "USD 296M", "USD 231M", "+28%"], ["Gross margin", "74.2%", "72.9%", "+1.3 pts"],
                                     ["Operating margin", "21.5%", "19.8%", "+1.7 pts"], ["Free cash flow", "USD 88M", "USD 70M", "+26%"]])]),
        ("Customers", ["Net revenue retention was 121%. Customers spending more than USD 1 million annually grew to 214. Largest new logo: a top-5 European bank."]),
        ("Risks", ["Key risks: GPU capacity constraints for AI workloads, currency headwinds from a strong US dollar, and longer sales cycles in the public sector."]),
    ]),
    dict(file="Veridian_QBR_Q2_FY2026.pdf", title="Quarterly Business Review - Q2 FY2026", code="QBR-Q2-FY26",
         owner="Office of the CFO", effective="Quarter ended 30 June 2026", sections=[
        ("Executive Summary", ["Q2 FY2026 revenue was USD 438 million, up 20% year over year and 6% sequentially. Operating margin improved to 22.8%. The launch of Veridian AI Studio contributed USD 19 million in new bookings."]),
        ("Financial Highlights", [T([["Metric", "Q2 FY2026", "Q2 FY2025", "YoY"], ["Revenue", "USD 438M", "USD 365M", "+20%"],
                                     ["Cloud revenue", "USD 321M", "USD 246M", "+30%"], ["Gross margin", "74.8%", "73.1%", "+1.7 pts"],
                                     ["Operating margin", "22.8%", "20.1%", "+2.7 pts"], ["Free cash flow", "USD 97M", "USD 74M", "+31%"]])]),
        ("Customers and Headcount", ["Net revenue retention was 123%. Customers above USD 1 million grew to 229. Headcount ended the quarter at 4,860."]),
        ("Outlook", ["Guidance for Q3 FY2026 revenue is USD 455 to 462 million. The company raised full-year FY2026 guidance to USD 1.78 billion."]),
    ]),
    dict(file="Veridian_Customer_Satisfaction_Survey_2025.pdf", title="Customer Satisfaction Survey Report 2025", code="CX-SURVEY-2025",
         owner="Customer Experience", effective="Survey fielded Oct-Nov 2025", sections=[
        ("Methodology", ["The survey was sent to 9,400 users across 1,150 customer accounts; 2,318 responses were received (24.7% response rate)."]),
        ("Headline Results", [T([["Measure", "2025", "2024"], ["Net Promoter Score (NPS)", "+47", "+41"], ["CSAT (support)", "4.5 / 5", "4.3 / 5"],
                                 ["Customer Effort Score", "5.8 / 7", "5.5 / 7"]])]),
        ("What Customers Value Most", [B(["Query performance and reliability (cited by 61%).", "Quality of technical support (48%).", "Ease of integration via APIs (39%)."])]),
        ("Top Improvement Requests", [B(["More transparent pricing and cost controls (44%).", "Better documentation for advanced features (33%).", "Faster onboarding for new users (27%)."])]),
        ("Actions", ["In response, Veridian will launch a Cost Explorer dashboard in Q1 FY2026 and a redesigned documentation portal in Q2 FY2026."]),
    ]),
    dict(file="Veridian_Product_Roadmap_2026.pdf", title="Product Roadmap 2026 (Internal)", code="PRD-RM-2026",
         owner="Product Management", effective="Approved December 2025", sections=[
        ("Strategic Themes", ["The 2026 roadmap focuses on three themes: AI-native analytics, cost transparency, and enterprise trust (security and compliance)."]),
        ("Quarterly Plan", [T([["Quarter", "Key deliverables"], ["Q1 2026", "Cost Explorer dashboard; SOC 2 Type II renewal"],
                               ["Q2 2026", "Veridian AI Studio GA; new documentation portal"], ["Q3 2026", "Natural-language-to-SQL assistant; EU sovereign region (Frankfurt)"],
                               ["Q4 2026", "Agentic data pipelines (beta); FedRAMP Moderate authorization"]])]),
        ("Veridian AI Studio", ["AI Studio lets customers build retrieval-augmented generation (RAG) applications on their own data, with built-in vector search, prompt management and evaluation dashboards."]),
        ("Deprecations", ["API v2 will be retired on 30 September 2026. Customers must migrate to API v3 before that date."]),
    ]),
    dict(file="VS-OPS-022_Business_Continuity_and_Disaster_Recovery_Plan.pdf", title="Business Continuity and Disaster Recovery Plan", code="VS-OPS-022",
         owner="Resilience Office", effective="1 August 2025", sections=[
        ("Objectives", ["For tier-1 services (Veridian Cloud control plane and query engine) the Recovery Time Objective (RTO) is 1 hour and the Recovery Point Objective (RPO) is 5 minutes. For tier-2 internal systems the RTO is 8 hours and the RPO is 24 hours."]),
        ("Architecture", ["Tier-1 services run active-active across two cloud regions per geography. Backups are encrypted, immutable and stored in a third region for 35 days."]),
        ("Testing", ["Full disaster-recovery failover tests are performed twice a year, and tabletop exercises are run every quarter with the executive crisis team."]),
        ("Crisis Team", ["The crisis management team is chaired by the Chief Operating Officer and includes the CISO, CTO, General Counsel and Head of Communications."]),
    ]),
    dict(file="Veridian_Support_SLA_and_Escalation_Guide.pdf", title="Customer Support SLA and Escalation Guide", code="CS-SLA-2026",
         owner="Customer Support", effective="1 January 2026", sections=[
        ("Support Plans", [T([["Plan", "Hours", "Channels", "Uptime SLA"], ["Standard", "Business hours", "Portal, email", "99.5%"],
                             ["Premium", "24x7", "Portal, email, phone", "99.9%"], ["Mission Critical", "24x7 + named TAM", "All + Slack Connect", "99.95%"]])]),
        ("Initial Response Targets", [T([["Priority", "Standard", "Premium", "Mission Critical"], ["P1 - Critical", "4 hours", "1 hour", "15 minutes"],
                                         ["P2 - High", "8 hours", "4 hours", "1 hour"], ["P3 - Normal", "2 business days", "1 business day", "4 hours"]])]),
        ("Service Credits", ["If monthly uptime falls below the SLA, customers receive service credits: 10% of the monthly fee for each 0.1% below target, capped at 50%. Credits must be claimed within 30 days."]),
        ("Escalation Path", [B(["Level 1: Support Engineer", "Level 2: Support Manager (after 2x the response target)", "Level 3: Director of Support", "Level 4: VP Customer Success"])]),
    ]),
]


def on_page(canvas, doc, meta):
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, A4[1] - 1.2 * cm, A4[0], 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(1.5 * cm, A4[1] - 0.8 * cm, COMPANY)
    canvas.drawRightString(A4[0] - 1.5 * cm, A4[1] - 0.8 * cm, meta["code"])
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5 * cm, 1 * cm, f"{meta['title']}  |  Owner: {meta['owner']}  |  Fictional document for demo purposes")
    canvas.drawRightString(A4[0] - 1.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def render_block(block):
    if isinstance(block, str):
        return [Paragraph(block, BODY), Spacer(1, 6)]
    kind, data = block
    if kind == "bullets":
        return [ListFlowable([ListItem(Paragraph(x, BODY)) for x in data], bulletType="bullet", leftIndent=14), Spacer(1, 6)]
    rows = [[Paragraph(str(c), BODY) for c in r] for r in data]
    t = Table(rows, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0FB")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C7DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [t, Spacer(1, 8)]


def build(meta):
    path = OUT_DIR / meta["file"]
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=1.8 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm, title=meta["title"], author=COMPANY)
    story = [Spacer(1, 3 * cm), Paragraph(meta["title"], H1), Spacer(1, 6),
             Paragraph(f"{COMPANY}  -  Document {meta['code']}", SUB),
             Paragraph(f"Owner: {meta['owner']}  |  Effective: {meta['effective']}", SUB), Spacer(1, 1 * cm),
             Paragraph("Document Control", H2),
             render_block(("table", [["Field", "Value"], ["Document ID", meta["code"]], ["Owner", meta["owner"]],
                                      ["Effective", meta["effective"]], ["Classification", "Internal"],
                                      ["Review cycle", "Annual"]]))[0],
             PageBreak()]
    for heading, blocks in meta["sections"]:
        story.append(Paragraph(heading, H2))
        for b in blocks:
            story.extend(render_block(b))
    doc.build(story, onFirstPage=lambda c, d: on_page(c, d, meta), onLaterPages=lambda c, d: on_page(c, d, meta))
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for meta in DOCS:
        print("  +", build(meta).name)
    print(f"Generated {len(DOCS)} synthetic PDFs in {OUT_DIR}")


if __name__ == "__main__":
    main()
