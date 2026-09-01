# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, date_diff


def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Repossession Order"), "fieldtype": "Link", "options": "Repossession Order", "width": 150},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 150},
		{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Vehicle", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{"fieldname": "order_date", "label": _("Order Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "recovery_date", "label": _("Recovery Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_to_recover", "label": _("Days to Recover"), "fieldtype": "Int", "width": 110},
		{"fieldname": "outstanding_balance_at_order", "label": _("Balance at Order"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "repossession_cost", "label": _("Recovery Cost"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "estimated_resale_value", "label": _("Est. Resale Value"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "vehicle_condition", "label": _("Condition"), "fieldtype": "Data", "width": 90},
	]


def get_data():
	rows = frappe.get_all(
		"Repossession Order",
		fields=[
			"name", "customer", "vehicle", "status", "order_date", "recovery_date",
			"outstanding_balance_at_order", "repossession_cost", "estimated_resale_value",
			"vehicle_condition",
		],
		order_by="order_date desc",
	)
	for r in rows:
		r["days_to_recover"] = date_diff(r.recovery_date, r.order_date) if r.recovery_date else None
	return rows
