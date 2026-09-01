# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Installment"), "fieldtype": "Link", "options": "Hire Purchase Installment", "width": 130},
		{"fieldname": "hire_purchase_agreement", "label": _("Agreement"), "fieldtype": "Link", "options": "Hire Purchase Agreement", "width": 130},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 160},
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Vehicle", "width": 110},
		{"fieldname": "installment_number", "label": _("Inst #"), "fieldtype": "Int", "width": 70},
		{"fieldname": "due_date", "label": _("Due Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_overdue", "label": _("Days Overdue"), "fieldtype": "Int", "width": 100},
		{"fieldname": "amount_due", "label": _("Amount Due"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "amount_paid", "label": _("Amount Paid"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "outstanding", "label": _("Outstanding"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "penalty", "label": _("Penalty Accrued"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "assigned_collector", "label": _("Assigned Collector"), "fieldtype": "Link", "options": "User", "width": 140},
	]


def get_data(filters):
	conditions = ["hpi.status = 'Overdue'"]
	values = {}

	if filters.get("customer"):
		conditions.append("hpa.customer = %(customer)s")
		values["customer"] = filters["customer"]

	if filters.get("min_days_overdue"):
		conditions.append("DATEDIFF(CURDATE(), hpi.due_date) >= %(min_days_overdue)s")
		values["min_days_overdue"] = filters["min_days_overdue"]

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select
			hpi.name, hpi.hire_purchase_agreement, hpa.customer, hpa.vehicle,
			hpi.installment_number, hpi.due_date,
			DATEDIFF(CURDATE(), hpi.due_date) as days_overdue,
			hpi.amount_due, hpi.amount_paid, hpi.penalty,
			cc.assigned_collector
		from `tabHire Purchase Installment` hpi
		inner join `tabHire Purchase Agreement` hpa on hpa.name = hpi.hire_purchase_agreement
		left join `tabCollection Case` cc on cc.hire_purchase_agreement = hpa.name
			and cc.status not in ('Resolved', 'Closed')
		where {where_clause}
		order by days_overdue desc
		""",
		values,
		as_dict=True,
	)

	for r in rows:
		r["outstanding"] = flt(r["amount_due"]) - flt(r["amount_paid"])

	return rows
