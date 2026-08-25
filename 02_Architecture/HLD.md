# High-Level Design (HLD)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — pending approval

---

## 1. System Components

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                          │
│   Company App (Owner/Admin/PM/Designer/Accountant/Sales) │
│   Platform Admin Console (separate surface)               │
│   Client Portal (Phase 5, separate surface)                │
└───────────────────────────┬────────────────────────────┘
                             │  HTTPS / REST (or GraphQL) API
┌───────────────────────────▼────────────────────────────┐
│                     API / Application Layer               │
│   AuthN service · AuthZ (Tenant + Permission) middleware  │
└───────────────────────────┬────────────────────────────┘
                             │
┌───────────────────────────▼────────────────────────────┐
│                      Business Modules                     │
│  Company · User/Role · Client · Project · Product/BOQ     │
│  Quotation · Contract · Invoice · Payment · Expense        │
│  Report · (Phase 3+: Lead, Site Visit, Design, ...)         │
└───────────────────────────┬────────────────────────────┘
                             │
              ┌──────────────┴───────────────┐
┌─────────────▼─────────────┐   ┌─────────────▼─────────────┐
│   PostgreSQL (system of    │   │  Object/File Storage       │
│   record; tenant-scoped)   │   │  (designs, drawings,       │
│                             │   │   attachments, receipts)   │
└─────────────────────────────┘   └─────────────────────────────┘
```

Cross-cutting: **Audit Log** (append-only, written by business modules on sensitive mutations) and **Notification Service** (Phase 5) sit alongside the business modules layer.

## 2. Component Responsibilities

| Component | Responsibility |
|---|---|
| Platform Admin Console | Manage companies, plans, subscriptions, feature flags, platform audit — operates outside tenant context |
| Company App (Frontend) | Role-driven UI for Company Owner/Admin/PM/Designer/Accountant/Sales/Supervisor |
| Client Portal (Phase 5) | Isolated, read-mostly + approval surface for clients |
| AuthN Service | Login, session/token issuance, password reset, email verification |
| Tenant + Permission Middleware | Resolves user → company membership → role → permission on every request; rejects any request lacking valid tenant context |
| Business Modules | Encapsulate domain logic per entity (Project, BOQ, Quotation, Invoice, ...); the **only** layer allowed to touch PostgreSQL for business data |
| Audit Log | Append-only record of who/what/old/new/when for sensitive entities |
| Report Engine | Computes dashboard KPIs and report groups (Sales/Projects/Finance/Expenses) from live transactional data — not a separately maintained store |
| Object Storage | Versioned file storage for designs/drawings/attachments/receipts, always tagged with company + entity + version |

## 3. Key Data Flows

### 3.1 Quotation Approval Flow
```
Project → BOQ → Create Quotation → Internal Review
 → Send to Client → Client Review → (Revision → new version)
                                   → (Approval → triggers Contract eligibility)
```

### 3.2 Invoice → Payment → Profitability Flow
```
Approved Quotation/Contract → Invoice → Send to Client
 → Payment(s) recorded (partial or full) → Invoice status updates
 → Project Cost aggregates Expenses (Materials/Labour/Vendor/Other)
 → Project Profit = Revenue (Invoiced/Received) − Project Cost
 → Reports/Dashboard reflect updated figures
```

### 3.3 Tenant-Scoped Request
```
Client request → AuthN validates token → Tenant/Permission middleware
 resolves company from server-side membership (never from client input)
 → checks role/permission for requested action
 → business module executes tenant-scoped query
 → response
```

## 4. Deployment View (indicative — see `07_DevOps/`)

- Frontend, API layer, and Platform Admin Console deployable as independent services/containers.
- PostgreSQL as a managed or self-hosted instance, single instance serving all tenants under the shared-schema strategy (see `02_Architecture/Technical_Architecture.md` §3).
- Object storage as an external managed service (e.g., S3-compatible).

## 5. Related Documents

- `02_Architecture/Solution_Architecture.md` — architecture principles and entity hierarchy
- `02_Architecture/LLD.md` — low-level design (pending)
- `03_Database/ER_Diagram.md` — entity relationships
- `04_API/` — per-module API specs
- `05_Security/` — JWT, tenant, permissions implementation
