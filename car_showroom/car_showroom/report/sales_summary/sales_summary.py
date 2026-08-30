# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Sale", "fieldname": "name", "fieldtype": "Link", "options": "Vehicle Sale", "width": 120},
		{"label": "Date", "fieldname": "sale_date", "fieldtype": "Date", "width": 100},
		{"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Dealership Branch", "width": 120},
		{"label": "Salesperson", "fieldname": "salesperson", "fieldtype": "Link", "options": "Salesperson", "width": 130},
		{"label": "Vehicle", "fieldname": "vehicle", "fieldtype": "Link", "options": "Vehicle", "width": 100},
		{"label": "Sale Type", "fieldname": "sale_type", "fieldtype": "Data", "width": 130},
		{"label": "Total Amount", "fieldname": "total_amount", "fieldtype": "Currency", "width": 120},
		{"label": "Cost of Vehicle", "fieldname": "cost_of_vehicle", "fieldtype": "Currency", "width": 120},
		{"label": "Gross Profit", "fieldname": "gross_profit", "fieldtype": "Currency", "width": 120},
		{"label": "Commission", "fieldname": "commission_amount", "fieldtype": "Currency", "width": 110},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	conditions = ["docstatus = 1"]
	values = {}

	if filters.get("from_date"):
		conditions.append("sale_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("sale_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("branch"):
		conditions.append("branch = %(branch)s")
		values["branch"] = filters["branch"]
	if filters.get("salesperson"):
		conditions.append("salesperson = %(salesperson)s")
		values["salesperson"] = filters["salesperson"]
	if filters.get("sale_type"):
		conditions.append("sale_type = %(sale_type)s")
		values["sale_type"] = filters["sale_type"]

	where_clause = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select name, sale_date, branch, salesperson, vehicle, sale_type,
		       total_amount, cost_of_vehicle, gross_profit, commission_amount, status
		from `tabVehicle Sale`
		where {where_clause}
		order by sale_date desc
		""",
		values,
		as_dict=True,
	)
