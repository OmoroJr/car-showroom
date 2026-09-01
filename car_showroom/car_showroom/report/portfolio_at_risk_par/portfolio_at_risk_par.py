# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

THRESHOLDS = [30, 60, 90]


def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data


def get_columns():
	return [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 220},
		{"fieldname": "value", "label": _("Amount"), "fieldtype": "Currency", "width": 160},
		{"fieldname": "percent_of_portfolio", "label": _("% of Portfolio"), "fieldtype": "Percent", "width": 140},
	]


def get_data():
	total_outstanding = flt(frappe.db.sql(
		"""
		select sum(outstanding_balance) from `tabHire Purchase Agreement`
		where status in ('Active', 'Defaulted')
		"""
	)[0][0] or 0)

	data = [{
		"metric": _("Total Portfolio Outstanding"),
		"value": total_outstanding,
		"percent_of_portfolio": 100 if total_outstanding else 0,
	}]

	for threshold in THRESHOLDS:
		at_risk = flt(frappe.db.sql(
			"""
			select sum(distinct_agreements.outstanding_balance) from (
				select hpa.name, hpa.outstanding_balance
				from `tabHire Purchase Agreement` hpa
				where hpa.status in ('Active', 'Defaulted')
				and exists (
					select 1 from `tabHire Purchase Installment` hpi
					where hpi.hire_purchase_agreement = hpa.name
					and hpi.status = 'Overdue'
					and DATEDIFF(CURDATE(), hpi.due_date) >= %s
				)
			) distinct_agreements
			""",
			(threshold,),
		)[0][0] or 0)

		pct = (at_risk / total_outstanding * 100) if total_outstanding else 0
		data.append({
			"metric": _("PAR {0} (Outstanding on Agreements Overdue \u2265 {0} Days)").format(threshold),
			"value": at_risk,
			"percent_of_portfolio": pct,
		})

	return data
