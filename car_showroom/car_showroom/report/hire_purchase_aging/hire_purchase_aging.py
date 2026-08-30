# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, nowdate

BUCKETS = ["Current", "1-30 Days", "31-60 Days", "61-90 Days", "90+ Days"]


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Agreement", "fieldname": "hire_purchase_agreement", "fieldtype": "Link",
		 "options": "Hire Purchase Agreement", "width": 140},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link",
		 "options": "Showroom Customer", "width": 160},
		{"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link",
		 "options": "Vehicle", "width": 120},
		{"label": "Installments Overdue", "fieldname": "installments_overdue", "fieldtype": "Int", "width": 140},
		{"label": "Days Overdue", "fieldname": "days_overdue", "fieldtype": "Int", "width": 110},
		{"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 110},
		{"label": "Outstanding", "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
		{"label": "Last Payment", "fieldname": "last_payment_date", "fieldtype": "Date", "width": 110},
		{"label": "Next Payment Due", "fieldname": "next_due_date", "fieldtype": "Date", "width": 130},
	]


def get_data(filters):
	today = getdate(nowdate())

	overdue_rows = frappe.get_all(
		"Hire Purchase Installment",
		filters={"status": "Overdue"},
		fields=["hire_purchase_agreement", "due_date", "balance"],
	)

	by_agreement = {}
	for row in overdue_rows:
		bucket = by_agreement.setdefault(row.hire_purchase_agreement, {
			"installments_overdue": 0,
			"max_days_overdue": 0,
			"outstanding": 0,
		})
		days = (today - getdate(row.due_date)).days
		bucket["installments_overdue"] += 1
		bucket["max_days_overdue"] = max(bucket["max_days_overdue"], days)
		bucket["outstanding"] += flt(row.balance)

	if filters.get("hire_purchase_agreement"):
		by_agreement = {
			k: v for k, v in by_agreement.items() if k == filters["hire_purchase_agreement"]
		}

	data = []
	for agreement_name, agg in by_agreement.items():
		agreement = frappe.db.get_value(
			"Hire Purchase Agreement", agreement_name,
			["customer", "vehicle"], as_dict=True,
		)
		if not agreement:
			continue

		last_payment_date = frappe.db.get_value(
			"Hire Purchase Payment",
			{"hire_purchase_agreement": agreement_name, "docstatus": 1},
			"payment_date",
			order_by="payment_date desc",
		)
		next_due_date = frappe.db.get_value(
			"Hire Purchase Installment",
			{"hire_purchase_agreement": agreement_name, "status": ("in", ["Pending", "Partially Paid"])},
			"due_date",
			order_by="due_date asc",
		)

		data.append({
			"hire_purchase_agreement": agreement_name,
			"customer": agreement.customer,
			"vehicle": agreement.vehicle,
			"installments_overdue": agg["installments_overdue"],
			"days_overdue": agg["max_days_overdue"],
			"bucket": _bucket_for(agg["max_days_overdue"]),
			"outstanding": agg["outstanding"],
			"last_payment_date": last_payment_date,
			"next_due_date": next_due_date,
		})

	data.sort(key=lambda r: r["days_overdue"], reverse=True)
	return data


def _bucket_for(days_overdue):
	if days_overdue <= 0:
		return "Current"
	if days_overdue <= 30:
		return "1-30 Days"
	if days_overdue <= 60:
		return "31-60 Days"
	if days_overdue <= 90:
		return "61-90 Days"
	return "90+ Days"
