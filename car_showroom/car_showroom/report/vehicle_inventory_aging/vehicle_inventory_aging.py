# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Stock Number", "fieldname": "stock_number", "fieldtype": "Link", "options": "Vehicle", "width": 130},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Dealership Branch", "width": 120},
		{"label": "Make", "fieldname": "make", "fieldtype": "Data", "width": 100},
		{"label": "Model", "fieldname": "model", "fieldtype": "Data", "width": 100},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
		{"label": "Days in Stock", "fieldname": "days_in_stock", "fieldtype": "Int", "width": 110},
		{"label": "Aging Bucket", "fieldname": "aging_bucket", "fieldtype": "Data", "width": 110},
		{"label": "Total Cost", "fieldname": "total_cost", "fieldtype": "Currency", "width": 120},
		{"label": "Asking Price", "fieldname": "asking_price", "fieldtype": "Currency", "width": 120},
		{"label": "Expected Profit", "fieldname": "expected_profit", "fieldtype": "Currency", "width": 120},
	]


def get_data(filters):
	conditions = ["status not in ('Sold', 'Delivered', 'Returned')"]
	values = {}

	if filters.get("branch"):
		conditions.append("branch = %(branch)s")
		values["branch"] = filters["branch"]
	if filters.get("status"):
		conditions.append("status = %(status)s")
		values["status"] = filters["status"]

	where_clause = " and ".join(conditions)

	rows = frappe.db.sql(
		f"""
		select name as stock_number, branch, make, model, status, creation,
		       total_cost, asking_price, expected_profit
		from `tabVehicle`
		where {where_clause}
		""",
		values,
		as_dict=True,
	)

	today = getdate(nowdate())
	for row in rows:
		days = (today - getdate(row.creation)).days
		row["days_in_stock"] = days
		row["aging_bucket"] = _bucket_for(days)

	rows.sort(key=lambda r: r["days_in_stock"], reverse=True)
	return rows


def _bucket_for(days):
	if days <= 30:
		return "0-30 Days"
	if days <= 60:
		return "31-60 Days"
	if days <= 90:
		return "61-90 Days"
	return "90+ Days"
