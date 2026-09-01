# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, date_diff


class HirePurchaseInstallment(Document):
	pass


def update_overdue_and_penalties():
	"""Scheduled daily job: mark Due/Overdue installments and accrue penalties."""
	settings = frappe.get_single("Finance Settings")
	grace_days = settings.overdue_penalty_grace_days or 0

	open_rows = frappe.get_all(
		"Hire Purchase Installment",
		filters={"status": ["in", ["Upcoming", "Due", "Overdue", "Partially Paid"]]},
		fields=["name", "hire_purchase_agreement", "due_date", "amount_due", "amount_paid",
				"penalty", "status"],
	)

	today = nowdate()
	for row in open_rows:
		days_overdue = date_diff(today, row.due_date)
		outstanding = flt(row.amount_due) - flt(row.amount_paid)

		if outstanding <= 0:
			continue

		if days_overdue < 0:
			new_status = "Upcoming"
		elif days_overdue == 0:
			new_status = "Due"
		elif days_overdue <= grace_days:
			new_status = "Due"
		else:
			new_status = "Overdue"
			product_rate = get_penalty_rate(row.hire_purchase_agreement)
			if product_rate:
				accrued = outstanding * flt(product_rate) / 100
				frappe.db.set_value(
					"Hire Purchase Installment", row.name, "penalty",
					flt(row.penalty) + accrued, update_modified=False,
				)

		if new_status != row.status:
			frappe.db.set_value("Hire Purchase Installment", row.name, "status", new_status,
								 update_modified=False)

	frappe.db.commit()


def get_penalty_rate(agreement_name):
	product = frappe.db.get_value("Hire Purchase Agreement", agreement_name, "financing_product")
	if not product:
		return 0
	return frappe.db.get_value("Financing Product", product, "penalty_rate_percent") or 0
