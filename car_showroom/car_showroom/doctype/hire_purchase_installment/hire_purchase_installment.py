# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class HirePurchaseInstallment(Document):

	def validate(self):
		self.total = flt(self.principal) + flt(self.interest) + flt(self.fees)
		self.balance = flt(self.total) - flt(self.amount_paid)

		if self.status not in ("Waived", "Rescheduled"):
			is_past_due = self.due_date and frappe.utils.getdate(self.due_date) < frappe.utils.getdate(frappe.utils.nowdate())

			if flt(self.balance) <= 0:
				self.status = "Paid"
			elif is_past_due:
				self.status = "Overdue"
			elif flt(self.amount_paid) > 0:
				self.status = "Partially Paid"
			else:
				self.status = "Pending"


def mark_overdue_installments():
	"""Daily scheduled job: flip any Pending/Partially Paid installment whose
	due date has passed to Overdue (re-saving re-runs validate(), which sets
	the status based on balance and due_date)."""
	candidates = frappe.get_all(
		"Hire Purchase Installment",
		filters={
			"status": ("in", ["Pending", "Partially Paid"]),
			"due_date": ("<", frappe.utils.nowdate()),
		},
		pluck="name",
	)
	for name in candidates:
		doc = frappe.get_doc("Hire Purchase Installment", name)
		doc.save(ignore_permissions=True)
