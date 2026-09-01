# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

BUCKETS = ["0-30 Days", "31-60 Days", "61-90 Days", "90+ Days"]


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"fieldname": "bucket", "label": _("Ageing Bucket"), "fieldtype": "Data", "width": 130},
		{"fieldname": "priority", "label": _("Priority"), "fieldtype": "Data", "width": 90},
		{"fieldname": "case_count", "label": _("Open Cases"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_overdue", "label": _("Total Overdue Amount"), "fieldtype": "Currency", "width": 160},
		{"fieldname": "total_outstanding", "label": _("Total Outstanding Balance"), "fieldtype": "Currency", "width": 180},
	]


def bucket_for(days):
	if days <= 30:
		return BUCKETS[0]
	if days <= 60:
		return BUCKETS[1]
	if days <= 90:
		return BUCKETS[2]
	return BUCKETS[3]


def get_data(filters):
	conditions = ["status not in ('Resolved', 'Closed')"]
	values = {}
	if filters.get("assigned_collector"):
		conditions.append("assigned_collector = %(assigned_collector)s")
		values["assigned_collector"] = filters["assigned_collector"]

	where_clause = " and ".join(conditions)
	cases = frappe.db.sql(
		f"""
		select days_overdue, priority, overdue_amount, total_outstanding
		from `tabCollection Case`
		where {where_clause}
		""",
		values,
		as_dict=True,
	)

	summary = {}
	for c in cases:
		key = (bucket_for(c.days_overdue or 0), c.priority or "Low")
		row = summary.setdefault(key, {"case_count": 0, "total_overdue": 0, "total_outstanding": 0})
		row["case_count"] += 1
		row["total_overdue"] += flt(c.overdue_amount)
		row["total_outstanding"] += flt(c.total_outstanding)

	data = []
	for bucket in BUCKETS:
		for priority in ("Critical", "High", "Medium", "Low"):
			row = summary.get((bucket, priority))
			if row:
				data.append({
					"bucket": bucket, "priority": priority,
					"case_count": row["case_count"],
					"total_overdue": row["total_overdue"],
					"total_outstanding": row["total_outstanding"],
				})
	return data
