# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class HirePurchasePayment(Document):

	def validate(self):
		self.set_receipt_number()

	def set_receipt_number(self):
		if self.receipt_number:
			return
		year = frappe.utils.nowdate()[:4]
		prefix = f"HP-RCT-{year}-"
		last = frappe.db.sql(
			"""
			select receipt_number from `tabHire Purchase Payment`
			where receipt_number like %s order by creation desc limit 1
			""",
			(prefix + "%",),
		)
		if last and last[0][0]:
			try:
				last_serial = int(last[0][0].split("-")[-1])
			except ValueError:
				last_serial = 0
		else:
			last_serial = 0
		self.receipt_number = f"{prefix}{last_serial + 1:05d}"

	def before_submit(self):
		self.auto_allocate()

	def auto_allocate(self):
		"""FIFO allocation: pay off the oldest outstanding installments first."""
		self.allocations = []
		remaining = flt(self.amount)

		outstanding = frappe.get_all(
			"Hire Purchase Installment",
			filters={
				"hire_purchase_agreement": self.hire_purchase_agreement,
				"status": ("in", ["Pending", "Partially Paid", "Overdue"]),
			},
			fields=["name", "balance"],
			order_by="due_date asc",
		)

		for row in outstanding:
			if remaining <= 0:
				break
			balance = flt(row.balance)
			if balance <= 0:
				continue
			allocate = min(balance, remaining)
			self.append("allocations", {
				"installment": row.name,
				"allocated_amount": allocate,
			})
			remaining -= allocate

		self.unallocated_amount = remaining

	def on_submit(self):
		self.apply_allocations(reverse=False)

	def on_cancel(self):
		self.apply_allocations(reverse=True)

	def apply_allocations(self, reverse=False):
		for row in self.allocations:
			installment = frappe.get_doc("Hire Purchase Installment", row.installment)
			delta = -flt(row.allocated_amount) if reverse else flt(row.allocated_amount)
			installment.amount_paid = flt(installment.amount_paid) + delta
			installment.save(ignore_permissions=True)
