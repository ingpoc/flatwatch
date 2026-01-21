Product Requirements Document (PRD)
1. Document Overview
1.1 Product Name
FlatWatch – Society Cash Tracker
1.2 Version
1.0 (Proof of Concept - POC)
1.3 Document Purpose
This PRD outlines the requirements for developing an AI-powered web application designed to enhance financial transparency and accountability in Indian housing societies. The application addresses concerns regarding the mismanagement of maintenance funds by providing automated tracking, validation, and public visibility of financial transactions. It leverages integrations with payment gateways like Razorpay and incorporates AI-driven analysis to detect discrepancies, thereby reducing opportunities for corruption.
1.4 Scope
The POC focuses on core functionalities for a single housing society (approximately 650 flats). Future iterations may include multi-society support, advanced analytics, and mobile applications. Out-of-scope items include full accounting software integration (e.g., Tally) and legal enforcement mechanisms.
1.5 Stakeholders

Primary Users: Residents of the housing society.
Administrators: Society managing committee (e.g., treasurer, secretary).
Developers: The product owner and technical team.
Regulators: Indirectly, through compliance with cooperative society bye-laws (e.g., Maharashtra Co-operative Societies Act, 1960).

1.6 Revision History

Version 1.0: Initial draft based on user discussions (January 20, 2026).

2. Business Objectives
2.1 Problem Statement
Housing societies in India often face opacity in fund utilization, leading to suspicions of corruption. Maintenance collections (e.g., INR 6,000–8,000 per flat monthly) lack verifiable tracking, with audits potentially compromised. The application introduces transparency by automating data ingestion, validation, and public querying, fostering accountability through visibility and community oversight.
2.2 Goals

Achieve real-time visibility of society balances, revenues, and expenditures.
Detect and flag financial discrepancies automatically to prevent manipulation.
Empower residents to query and challenge transactions via an intuitive interface.
Ensure compliance with relevant bye-laws by embedding legal knowledge into AI processes.
Promote a "fear of detection" through immutable records and named attributions.

2.3 Success Metrics

Adoption: 80% of residents actively using the dashboard within the first month.
Transparency: Reduction in unmatched transactions to below 5% monthly.
User Satisfaction: Net Promoter Score (NPS) above 70 via post-launch surveys.
Security: Zero reported data breaches in the POC phase.

3. User Personas
3.1 Resident (End-User)

Demographics: Adult flat owners or tenants, tech-savvy or basic users.
Needs: View financial summaries, query specifics, challenge suspicious entries.
Pain Points: Lack of trust in committee reports; difficulty accessing audit details.
Access Level: Read-only for most features; ability to upload receipts and initiate challenges.

3.2 Treasurer/Committee Member (Administrator)

Demographics: Elected society officials handling finances.
Needs: Upload documents, approve transactions, respond to challenges.
Pain Points: Manual reconciliation; defending against unfounded accusations.
Access Level: Full administrative privileges, with audit trails for all actions.

3.3 Developer/Admin (Product Owner)

Demographics: Technical individual or team building/maintaining the app.
Needs: Monitor system performance, update bye-laws knowledge base.
Pain Points: Ensuring data integrity and scalability.
Access Level: Super-admin for configuration and debugging.

4. Functional Requirements
The application is structured around five core features, ensuring tamper-proof data handling. All inputs are validated against multiple sources to prevent manipulation.
4.1 Live Money Feed

Description: Automatically ingest and display real-time transaction data from Razorpay (integrated via MyGate).
Requirements:
Integrate Razorpay API/webhooks for pulling JSON data (e.g., timestamps, amounts, sender VPAs, narrations).
Support test mode for POC with simulated transactions.
Categorize transactions (e.g., inflows as maintenance dues, outflows as expenses).
Frequency: Poll every 5 minutes; store in a secure database.

Validation: Cross-reference against uploaded receipts; flag mismatches (e.g., amount discrepancies).

4.2 Receipt Snap (Document Upload and Processing)

Description: Allow users to upload receipts or bills for verification against transaction logs.
Requirements:
Support formats: PDF, images (via mobile camera), Excel/CSV exports.
Use OCR tools (e.g., Google Cloud Vision or Tesseract) to extract key fields (amount, date, vendor).
Auto-match with nearest UPI/Razorpay entry (within ±2 hours).
Flag levels: Red (no match), Yellow (partial match, e.g., vendor mismatch).
Storage: Encrypted cloud storage (e.g., AWS S3).

Validation: Require multi-source confirmation (e.g., UPI log + physical receipt) for entries above INR 500.

4.3 Chat Guard (Interactive Query Interface)

Description: AI-powered chat for residents to inquire about financials and receive compliance viewpoints.
Requirements:
Natural language queries (e.g., "Show water bills last month").
Responses: Tabular data with details (date, amount, VPA, receipt link); flag unverified entries.
Integrate bye-laws knowledge base for contextual advice (e.g., "This expense complies with Bye-Law No. 65").
Backend: Use Claude Agent SDK for agentic processing and multi-turn conversations.

Validation: Responses based solely on verified data; notify if data is incomplete.

4.4 Challenge Mode (Dispute Resolution)

Description: Enable residents to dispute transactions, requiring proof for resolution.
Requirements:
Initiate via dashboard or chat; place disputed entry in a public queue.
Time-bound: 48 hours for committee to provide evidence (e.g., additional receipts or UPI confirmations).
Resolution: Auto-reject if unresolved; notify all users via push alerts.
Voting: Optional community vote for high-value disputes (> INR 10,000).

Validation: Require at least two independent proofs for approval; log all actions immutably.

4.5 Shame Dashboard (Transparency Visualization)

Description: Public-facing interface displaying real-time financial status.
Requirements:
Key Metrics: Current balance, recent inflows/outflows, unmatched entries.
Attribution: Attach names/roles to transactions (e.g., "Approved by Treasurer Rajesh").
Integration: Embed in MyGate notices or physical displays (e.g., QR codes in lifts).
Alerts: Daily/weekly summaries pushed to users (e.g., via email or WhatsApp integration).

Validation: Data pulled from reconciled sources only; no manual overrides.

4.6 Additional Features

Daily/Weekly AI Analysis: Automated midnight scans for mismatches; generate reports highlighting issues.
Bye-Laws Integration: Embedded database of state-specific bye-laws, updated quarterly.
Notifications: Real-time alerts for flags, challenges, or unresolved items.

5. Non-Functional Requirements
5.1 Performance

Response Time: <2 seconds for queries; <5 minutes for data ingestion.
Scalability: Handle 650 users concurrently; design for 10x growth.

5.2 Security

Authentication: Multi-factor (MFA) via Firebase; role-based access control (RBAC).
Data Protection: AES-256 encryption; compliance with Digital Personal Data Protection Act, 2023.
Audit Trails: Immutable logging of all actions; no delete functionality.
Vulnerability: HTTPS enforcement; regular penetration testing in POC.

5.3 Usability

Interface: Mobile-first, responsive design; intuitive for non-technical users.
Accessibility: WCAG 2.1 compliance (e.g., screen reader support).

5.4 Reliability

Uptime: 99.5% target; automated backups daily.
Error Handling: Graceful degradation for API failures (e.g., fallback to cached data).

6. Technical Specifications
6.1 Tech Stack

Backend: Python with Flask/FastAPI; Claude Agent SDK for AI workflows.
Frontend: Next.js with Tailwind CSS.
Database: SQLite (POC); migrate to PostgreSQL for production.
Integrations: Razorpay API/webhooks; Google Cloud Vision for OCR; Firebase for auth.
Hosting: Vercel or Render; cost under INR 4,000/month initially.
Cron Jobs: Scheduled tasks for data pulls and analyses.

6.2 Dependencies

Razorpay merchant account (read-only access via committee).
MyGate exports for initial data seeding.
Internet connectivity for API calls.

7. Assumptions and Risks
7.1 Assumptions

Committee provides Razorpay access post-POC demo.
Users have basic digital literacy for uploads and queries.
Legal bye-laws remain stable during development.

7.2 Risks and Mitigations

Risk: Resistance from committee – Mitigation: AGM resolution for transparency.
Risk: Data privacy breaches – Mitigation: Third-party security audit.
Risk: API downtime – Mitigation: Redundant data sources (e.g., manual uploads).

8. Launch and Roadmap
8.1 POC Timeline

Week 1: Setup dummy environment with personal UPI for testing.
Week 2: Develop core features and internal demo.
Week 3: Present to society committee for feedback and access approval.
Week 4: Launch beta; monitor usage and iterate.

8.2 Future Roadmap

Version 1.1: Multi-society support; advanced ML for anomaly detection.
Version 2.0: Mobile app; integration with additional gateways (e.g., PhonePe).

This PRD serves as a foundational guide for development. Should additional details or modifications be required, please provide further specifications.