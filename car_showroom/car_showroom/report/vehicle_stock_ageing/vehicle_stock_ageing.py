# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _

IN_STOCK_STATUSES = [
	"Sourced", "Purchased", "In Transit", "At Port", "Under Clearing", "Cleared",
	"At Yard", "Under Inspection", "Under Repair", "Ready for Sale", "Advertised",
	"Reserved", "Consignment", "Wholesale",
]


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "name", "label": _("Stock #"), "fieldtype": "Link", "options": "Vehicle", "width": 130},
		{"fieldname": "make", "label": _("Make"), "fieldtype": "Data", "width": 100},
		{"fieldname": "model", "label": _("Model"), "fieldtype": "Data", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "date_acquired", "label": _("Date Acquired"), "fieldtype": "Date", "width": 100},
		{"fieldname": "days_in_stock", "label": _("Days in Stock"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_cost", "label": _("Total Cost"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "asking_price", "label": _("Asking Price"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "gross_margin", "label": _("Gross Margin %"), "fieldtype": "Percent", "width": 120},
	]


def get_data(filters):
	conditions = ["status in %(statuses)s"]
	values = {"statuses": tuple(IN_STOCK_STATUSES)}

	if filters.get("min_days_in_stock"):
		conditions.append("days_in_stock >= %(min_days_in_stock)s")
		values["min_days_in_stock"] = filters["min_days_in_stock"]

	where_clause = " and ".join(conditions)

	return frappe.db.sql(
		f"""
		select name, make, model, status, date_acquired, days_in_stock, total_cost, asking_price, gross_margin
		from `tabVehicle`
		where {where_clause}
		order by days_in_stock desc
		""",
		values,
		as_dict=True,
	)
