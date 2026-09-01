# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate

DUE_STATUSES = ["Due", "Overdue", "Partially Paid"]
OPEN_STATUSES = ["Upcoming", "Due", "Overdue", "Partially Paid"]


class SettlementQuotation(Document):
	def validate(self):
		if self.hire_purchase_agreement:
			self.customer = frappe.db.get_value(
				"Hire Purchase Agreement", self.hire_purchase_agreement, "customer"
			)

		if self.status in ("Draft", "Issued"):
			self.calculate_settlement_figure()

	def calculate_settlement_figure(self):
		"""Payoff figure as of today: remaining principal, interest already accrued
		(installments due today or earlier), and any unpaid penalty/fees. Interest
		on installments that haven't fallen due yet is not charged, since the
		balance is being cleared early — that waiver is what early_settlement_rebate
		makes explicit on the quotation."""
		next_unpaid = frappe.get_all(
			"Hire Purchase Installment",
			filters={"hire_purchase_agreement": self.hire_purchase_agreement, "status": ["!=", "Paid"]},
			fields=["opening_balance"],
			order_by="installment_number asc",
			limit=1,
		)
		self.outstanding_principal = flt(next_unpaid[0].opening_balance) if next_unpaid else 0

		open_rows = frappe.get_all(
			"Hire Purchase Installment",
			filters={"hire_purchase_agreement": self.hire_purchase_agreement, "status": ["in", OPEN_STATUSES]},
			fields=["status", "interest", "penalty", "fees", "amount_paid", "principal"],
		)
		self.accrued_interest = sum(flt(r.interest) for r in open_rows if r.status in DUE_STATUSES)
		self.outstanding_penalty = sum(flt(r.penalty) for r in open_rows)
		self.outstanding_fees = sum(flt(r.fees) for r in open_rows if r.status in DUE_STATUSES)

		total = (
			flt(self.outstanding_principal) + flt(self.accrued_interest)
			+ flt(self.outstanding_penalty) + flt(self.outstanding_fees)
			- flt(self.early_settlement_rebate)
		)
		self.settlement_amount = max(total, 0)

	def before_submit(self):
		if self.status != "Accepted":
			frappe.throw("Only an Accepted settlement quotation can be applied. Set the status to Accepted first.")
		if flt(self.amount_received) < flt(self.settlement_amount):
			frappe.throw(
				f"Amount Received ({self.amount_received}) is less than the Settlement Amount "
				f"({self.settlement_amount})."
			)

	def on_submit(self):
		self.apply_settlement()
		if not self.settlement_date:
			self.db_set("settlement_date", nowdate())

		if self.collection_case:
			from car_showroom.car_showroom.doctype.collection_case.collection_case import close_case_for_agreement
			close_case_for_agreement(self.hire_purchase_agreement, "Settled")

	def on_cancel(self):
		frappe.msgprint(
			"Cancelling this Settlement Quotation does not automatically reopen the closed "
			"installment schedule — please review the Hire Purchase Agreement manually.",
			indicator="orange",
		)

	def apply_settlement(self):
		agreement = self.hire_purchase_agreement
		open_rows = frappe.get_all(
			"Hire Purchase Installment",
			filters={"hire_purchase_agreement": agreement, "status": ["!=", "Paid"]},
			fields=["name", "amount_due"],
		)
		for row in open_rows:
			frappe.db.set_value(
				"Hire Purchase Installment", row.name,
				{"amount_paid": row.amount_due, "status": "Paid"},
			)

		frappe.db.set_value("Hire Purchase Agreement", agreement, {
			"outstanding_balance": 0,
			"status": "Settled",
		})
		frappe.db.commit()
