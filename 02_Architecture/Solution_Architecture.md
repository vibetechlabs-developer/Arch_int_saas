# Solution Architecture
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — pending approval
**Source:** `INT_Projects_Client_Requirements_and_Business_Flow.md`

---

## 1. Architecture Summary

The system is a **multi-tenant Interior & Architecture Business Management SaaS**, layered as:

```
Frontend
   ↓
API / Application Layer
   ↓
Business Modules
   ↓
Tenant / Permission Layer
   ↓
PostgreSQL
   ↓
Object/File Storage
```

## 2. Core Architectural Principles

- Multi-company from day one — every company-owned record is tenant-scoped
- Strict tenant data isolation, enforced server-side (never trust a client-supplied company ID)
- Role-based access control (RBAC) via `User → Company Membership → Role → Permissions`
- **Project** is the central operational entity; **Client** is the central commercial entity
- **BOQ** is the bridge between the product/work catalog and the quotation
- **Quotation** is the bridge to the commercial agreement (contract)
- **Invoice/Payment** is the financial lifecycle
- **Expenses** roll up into project cost
- **Reports** are derived from transactional data, never separately maintained
- Versioning required for quotations and designs
- Audit logs required for sensitive operations (invoices, payments, expenses, quotations, permissions, project changes)
- API-first, modular backend
- Permission-driven frontend (UI reflects what the role/permission model allows, but the server is the actual enforcement point)
- Scalable file/document storage (designs, drawings, attachments, receipts)

## 3. Business Entity Hierarchy

```
PLATFORM
 └── COMPANY (tenant)
      ├── USERS / ROLES
      ├── CLIENTS
      │     └── PROJECTS
      │          ├── BOQ → PRODUCTS
      │          ├── QUOTATIONS
      │          ├── CONTRACTS
      │          ├── INVOICES → PAYMENTS
      │          ├── EXPENSES
      │          ├── TASKS
      │          ├── DOCUMENTS
      │          └── SITE ACTIVITY
      └── REPORTS
```

## 4. Request Flow (every company-scoped request)

```
Request
 → Authentication
 → Identify User
 → Identify Company (from server-side membership, not client input)
 → Check Membership
 → Check Permission
 → Tenant-Scoped Data Query
 → Business Logic
 → Response
```

## 5. Target Business Flow (full, all phases)

```
PLATFORM → COMPANY → USERS/SETTINGS → DASHBOARD → CRM (LEAD/CLIENT)
 → SITE VISIT → PROJECT → {DESIGN, BOQ → QUOTATION → REVISION/APPROVAL → CONTRACT, TASKS}
 → PROCUREMENT → SITE EXECUTION {MATERIAL, LABOUR, EXPENSE} → PROJECT COST
 → INVOICE → PAYMENT → PROFIT/LOSS → REPORTS → SNAGGING → HANDOVER → WARRANTY
```

Current (MVP) core flow is the subset:

```
COMPANY → USERS/ROLES → DASHBOARD → CLIENT → PROJECT → PRODUCT/BOQ
 → QUOTATION → CLIENT APPROVAL → INVOICE → PAYMENT → EXPENSE
 → PROJECT COST → PROFIT/LOSS → REPORTS
```

## 6. Module Map

See `01_Business/FRS.md` for full functional detail. Top-level modules:

- **Platform:** Dashboard, Companies, Plans, Subscriptions, Usage, Feature Flags, Platform Users, Support, Audit Logs
- **Company:** Profile, Branding, Tax Settings, Invoice/Quotation Settings, Numbering, Currency, Payment Terms, Notification Settings
- **Core Business (MVP):** Users, Roles/Permissions, Dashboard, Clients, Projects, Products/Categories, BOQ, Quotations, Invoices, Payments, Expenses, Reports
- **Interior Workflow (Phase 3):** Leads, Site Visits, Design Management, Contracts, Tasks, Milestones, Documents
- **Execution (Phase 4):** Vendors, Procurement, Purchase Orders, Inventory, Site Management, Snags, Handover
- **Advanced SaaS (Phase 5):** Client Portal, Employee Portal, Notifications, Advanced Analytics, Subscription Billing, Feature Flags

## 7. Non-Functional Requirements (derived, to confirm with client)

- **Isolation:** zero cross-tenant data leakage under any circumstance — treat as a security-critical invariant, not just a business rule.
- **Auditability:** every financial mutation (invoice, payment, expense, quotation, permission change) must be reconstructable after the fact.
- **Extensibility:** the schema and API must accommodate Phase 3–5 modules without breaking Phase 1–2 tenant/permission foundations.
- **File storage:** must handle versioned design files, drawings, and receipts at scale — see `07_DevOps` for storage backend decisions.

## 8. Related Documents

- `02_Architecture/Technical_Architecture.md` — technology choices and system design
- `02_Architecture/HLD.md` — high-level component design
- `03_Database/ER_Diagram.md` — entity relationships
- `05_Security/Tenant.md` — tenant isolation implementation
- `05_Security/Permissions.md` — RBAC implementation
