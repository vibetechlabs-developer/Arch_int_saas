# Functional Requirements Specification (FRS)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — pending approval
**Source:** `INT_Projects_Client_Requirements_and_Business_Flow.md`

This document breaks the business requirements (see `BRS.md`) into functional modules and their required behaviors. Each module below maps to a section in the source requirements document.

---

## 1. Platform Administration
- Manage companies (create/suspend/delete tenants)
- Manage subscription plans and active subscriptions
- View platform-wide usage
- Manage platform-level settings and feature flags
- Support tooling for companies
- View system audit logs
- Must operate independently of any company/tenant context

## 2. Company Management
- Company profile (name, branding, logo)
- GST/tax settings, currency, payment terms
- Invoice & quotation numbering configuration
- Notification settings

## 3. Authentication
- Login / logout
- Forgot password / reset password
- Email verification
- Session management
- 2FA (future)

## 4. User Management
- Add / edit / activate / deactivate users
- Role assignment, permission assignment
- User invitation flow
- Password reset (admin-initiated)
- Track last login
- A user's company membership must be explicit and auditable

## 5. Role & Permission Management
- Model: `User → Company Membership → Role → Permissions`
- Permission actions: View, Create, Edit, Delete, Approve, Export, Manage, Financial access
- Roles must be composable from these permission actions per module (e.g., Accountant = View/Create/Edit Invoice + View/Record Payment + View Expense + View Financial Reports)

## 6. Dashboard
KPI cards required: Total Projects, Active Projects, Total Quotations, Total Billed Revenue, Total Received, Pending Amount, Total Expenses, Net Profit/Loss.
Sections: Recent Projects, Recent Quotations, Pending Payments, Overdue Invoices, Recent Expenses, Upcoming Deadlines, Recent Activities, Project Profitability.

## 7. Client Management
- Fields: Name, Company, Email, Mobile, GSTIN
- Client 360 view: Basic Info, Contact Info, GST/Tax Info, Addresses, Contacts, Projects, Quotations, Contracts, Invoices, Payments, Documents, Notes, Activity
- A client must be reusable across multiple projects within the same company

## 8. Lead / CRM (Phase 3)
- Flow: Lead → Qualification → Follow-up → Site Visit → Won → Client → Project
- Lost leads require a loss reason and optional future follow-up date

## 9. Site Visit (Phase 3)
- Fields: client, project/lead, visit date, assigned person, address, measurements, requirements, photos, videos, notes, budget, site conditions, follow-up actions
- Produces a Site Visit Report that can create/update a project

## 10. Project Management
- Fields: client, project name, start date, deadline, status, priority, assigned to, follow-up reminder
- Project is the central entity, aggregating: Overview, Client, Team, Tasks, Milestones, Timeline, Design, Drawings, BOQ, Quotations, Contracts, Invoices, Payments, Expenses, Procurement, Site Activity, Documents, Snags, Reports
- Status lifecycle: Draft → Planning → Design → Quotation → Approved → Execution → Quality Check → Handover → Completed (plus On Hold / Cancelled)

## 11. Product Management
- Structure: Category → Subcategory → Product/Work Item → Unit → Default Cost → Default Selling Rate → Tax → Status
- Units: Nos, Sq.ft, Sq.m, Running ft, Kg, Litre, Set, Job
- Fields: image, name, category, subcategory, unit, price, status

## 12. BOQ (Bill of Quantities)
- Structure: Project → BOQ → Section → Item → Quantity → Unit → Rate → Amount
- Formula: `Amount = Quantity × Rate`
- Supports: discount, tax, total, notes, optional items, alternative items

## 13. Quotation
- Flow: Project → BOQ → Create Quotation → Internal Review → Send to Client → Client Review → (Revision → new version) | (Approval)
- Fields: quote number, client, project, items, BOQ reference, subtotal, discount, tax, total, terms, payment schedule, validity, notes, attachments, versioning, approval status

## 14. Contract (Phase 3+)
- Flow: Approved Quotation → Generate Contract → Terms/Scope/Payment Schedule → Client Acceptance → Contract Active

## 15. Invoice Management
- Flow: Contract/Approved Quotation → Invoice → Send to Client → Payment
- Fields: invoice number, client, project, items, tax, discount, total, due date, payment terms, payment status, attachments, notes
- Statuses: Draft, Sent, Partially Paid, Paid, Overdue, Cancelled

## 16. Payment Management
- Linked to invoice, client, project
- Fields: payment date, amount, method, reference number, notes, receipt
- Must support partial payments against an invoice (tracks paid vs. due)

## 17. Expense Management
- Structure: Company, Project, Category, Vendor, Employee, Amount, Tax, Date, Payment Method, Receipt, Notes, Added By, Approval Status
- Categories (existing): Labor/Employee Expense, Material Expense
- Workflow: Draft → Submitted → Approved → Paid

## 18. Project Costing
- `Project Profit = Project Revenue − Project Cost`
- Cost components: Materials, Labour, Vendors, Procurement, Transport, Other expenses
- Must compute and display margin % per project

## 19. Reports & Analytics
- Filters: date range, project
- Groups: Sales (leads, quotations, approval/rejection, conversion rate), Projects (active/completed/delayed, progress, profitability), Finance (revenue, received, outstanding, expenses, P&L, receivables), Expenses (by category/project/vendor/employee/date)

## 20. Design Management (Phase 3)
- Flow: Project → Design → Version N → Internal Review → Client Review → Revision → Version N+1 → Approval
- Files must be version-controlled (Design V1/V2/V3, Approved V3), not ad-hoc filenames

## 21. Procurement (Phase 4)
- Flow: BOQ → Material Requirement → Purchase Request → Approval → Vendor → Purchase Order → Goods Receipt → Inventory → Material Issue → Site

## 22. Site Management (Phase 4)
- Daily site report fields: date, workers, work completed, materials used, issues, photos, progress %, next-day plan

## 23. Snag Management (Phase 4)
- Flow: Inspection → Create Snag → Assign → Fix → Verify → Close
- Fields: project, location, description, priority, assigned user, due date, photos, status, resolution

## 24. Handover (Phase 4)
- Flow: Execution Complete → All Tasks Complete → All Snags Closed → Final Inspection → Final Invoice → Final Payment → Handover Documents → Client Acceptance → Project Completed

## 25. Client Portal (Phase 5)
- Client dashboard: Progress, Designs, Approvals, Quotations, Invoices, Payments, Documents, Messages, Service Requests
- Hard isolation: no visibility into other clients, other projects, internal expenses, salaries, internal notes, or internal margins/profit unless explicitly permitted

## 26. Notifications (Phase 5)
- Events: project assigned, task assigned/overdue, quotation sent/approved, design approval requested, invoice created/overdue, payment received, expense submitted/approved, snag assigned, deadline approaching
- Channels: in-app, email, WhatsApp (future)

## 27. Audit Trail
- Required for: invoices, payments, expenses, quotations, user permissions, project changes
- Fields: who, what changed, old value, new value, timestamp, entity, entity ID

---

## Cross-Cutting Functional Requirement: Tenant Scoping

Every functional module above operates on company-owned data. Every list/read/write operation must be scoped to the authenticated user's company membership, resolved server-side — see `05_Security/Tenant.md`.
