# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data()
	return columns, data


def get_columns():
	return [
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 140},
		{"fieldname": "agreement_count", "label": _("Agreements"), "fieldtype": "Int", "width": 100},
		{"fieldname": "total_financed", "label": _("Total Amount Financed"), "fieldtype": "Currency", "width": 170},
		{"fieldname": "total_payable", "label": _("Total Payable"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "total_outstanding", "label": _("Total Outstanding"), "fieldtype": "Currency", "width": 150},
	]


def get_data():
	return frappe.db.sql(
		"""
		select
			status,
			count(*) as agreement_count,
			sum(amount_financed) as total_financed,
			sum(total_payable) as total_payable,
			sum(outstanding_balance) as total_outstanding
		from `tabHire Purchase Agreement`
		group by status
		order by field(status, 'Active', 'Defaulted', 'Repossessed', 'Completed', 'Settled', 'Cancelled', 'Draft', 'Pending Activation')
		""",
		as_dict=True,
	)
