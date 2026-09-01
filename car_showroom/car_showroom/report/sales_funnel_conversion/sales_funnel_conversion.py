# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "stage", "label": _("Stage"), "fieldtype": "Data", "width": 200},
		{"fieldname": "count", "label": _("Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "conversion_from_leads", "label": _("% of Leads"), "fieldtype": "Percent", "width": 120},
	]


def get_data(filters):
	conditions = []
	values = {}
	if filters.get("branch"):
		conditions.append("branch = %(branch)s")
		values["branch"] = filters["branch"]
	if filters.get("assigned_salesperson"):
		conditions.append("assigned_salesperson = %(assigned_salesperson)s")
		values["assigned_salesperson"] = filters["assigned_salesperson"]

	lead_where = (" where " + " and ".join(conditions)) if conditions else ""
	lead_count = frappe.db.sql(f"select count(*) from `tabLead`{lead_where}", values)[0][0] or 0

	test_drive_count = frappe.db.count("Test Drive")
	quotation_count = frappe.db.count("Quotation")
	sale_count = frappe.db.count("Vehicle Sale", {"docstatus": 1})

	def pct(n):
		return (n / lead_count * 100) if lead_count else 0

	return [
		{"stage": _("Leads"), "count": lead_count, "conversion_from_leads": pct(lead_count)},
		{"stage": _("Test Drives Booked"), "count": test_drive_count, "conversion_from_leads": pct(test_drive_count)},
		{"stage": _("Quotations Issued"), "count": quotation_count, "conversion_from_leads": pct(quotation_count)},
		{"stage": _("Vehicles Sold"), "count": sale_count, "conversion_from_leads": pct(sale_count)},
	]
