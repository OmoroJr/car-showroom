# Car Showroom

Enterprise Car Dealership, Showroom, Vehicle Sales & Hire Purchase Management ERP
for multi-branch, multi-dealer, multi-finance operations in Mombasa, Kenya, built
on the Frappe Framework.

## Phased build plan

1. **Foundation** — Company/Branch/Yard, Vehicle Master, Customer, Lead (this scaffold)
2. **Sales** — CRM, test drives, quotations, sales orders, trade-ins, commissions
3. **Finance** — financing products, credit assessment, hire purchase, amortization, M-Pesa
4. **Collections** — overdue management, restructuring, settlement, recovery (done)

## Reports (Car Showroom module)

- Overdue Installments
- Collections Aging Summary
- Portfolio at Risk (PAR)
- Hire Purchase Portfolio Summary
- Vehicle Stock Ageing
- Repossession & Recovery Summary
- Sales Funnel Conversion

## Notifications (Car Showroom module)

- Installment Overdue Alert
- Collection Case Escalated
- Collection Case Assigned
- Loan Restructure Approved / Applied
- Settlement Quotation Issued / Applied
- Repossession Authorized / Completed
- Payment Receipt
5. **After-sales** — service, warranty, handover
6. **Intelligence** — dashboards, BI, reporting
7. **Marketplace** — public website, customer portal, financing calculator

## Install (bench)

```
bench get-app car_showroom /path/to/car_showroom
bench --site your-site.local install-app car_showroom
bench --site your-site.local migrate
```
