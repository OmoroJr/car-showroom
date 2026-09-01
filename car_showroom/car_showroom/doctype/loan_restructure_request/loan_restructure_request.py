# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_days, add_months, getdate

PERIODS_PER_YEAR = {"Weekly": 52, "Biweekly": 26, "Monthly": 12, "Custom": 12}

ARREARS_STATUSES = ["Due", "Overdue", "Partially Paid"]
OPEN_STATUSES = ["Upcoming", "Due", "Overdue", "Partially Paid"]


class LoanRestructureRequest(Document):
	def validate(self):
		if self.hire_purchase_agreement:
			self.customer = frappe.db.get_value(
				"Hire Purchase Agreement", self.hire_purchase_agreement, "customer"
			)
			self.snapshot_current_position()
			self.preview_new_schedule()

		if self.status == "Approved" and not self.approved_by:
			self.approved_by = frappe.session.user
			self.approval_date = nowdate()

	def snapshot_current_position(self):
		agreement = frappe.db.get_value(
			"Hire Purchase Agreement", self.hire_purchase_agreement,
			["outstanding_balance", "installment_amount"], as_dict=True,
		)
		self.current_outstanding_balance = agreement.outstanding_balance if agreement else 0
		self.current_installment_amount = agreement.installment_amount if agreement else 0

		open_rows = frappe.get_all(
			"Hire Purchase Installment",
			filters={"hire_purchase_agreement": self.hire_purchase_agreement, "status": ["in", OPEN_STATUSES]},
			fields=["name", "status", "amount_due", "amount_paid"],
		)
		self.current_remaining_installments = len(open_rows)
		self.arrears_amount = sum(
			flt(r.amount_due) - flt(r.amount_paid) for r in open_rows if r.status in ARREARS_STATUSES
		)

	def preview_new_schedule(self):
		"""Compute (without persisting) what the restructured schedule would look
		like, so the requester can see the new figures before it is approved."""
		if not self.new_term_months or not self.restructure_effective_date:
			return

		next_unpaid = frappe.get_all(
			"Hire Purchase Installment",
			filters={"hire_purchase_agreement": self.hire_purchase_agreement, "status": ["!=", "Paid"]},
			fields=["opening_balance"],
			order_by="installment_number asc",
			limit=1,
		)
		remaining_principal = flt(next_unpaid[0].opening_balance) if next_unpaid else 0

		capitalized = 0
		if self.capitalize_arrears:
			capitalized = flt(self.arrears_amount)
			if self.waive_penalty:
				penalty_in_arrears = sum(
					flt(r.penalty) for r in frappe.get_all(
						"Hire Purchase Installment",
						filters={"hire_purchase_agreement": self.hire_purchase_agreement, "status": ["in", ARREARS_STATUSES]},
						fields=["penalty"],
					)
				)
				capitalized -= penalty_in_arrears

		principal = remaining_principal + capitalized
		self.new_principal = principal

		n = max(1, round(flt(self.new_term_months) / 12 * PERIODS_PER_YEAR.get(self.new_frequency or "Monthly", 12)))
		period_rate = (flt(self.new_interest_rate) / 100) / PERIODS_PER_YEAR.get(self.new_frequency or "Monthly", 12)

		if period_rate:
			installment = principal * period_rate * (1 + period_rate) ** n / ((1 + period_rate) ** n - 1)
		else:
			installment = principal / n if n else 0

		total_payable = installment * n
		self.new_installment_amount = installment
		self.new_total_interest = total_payable - principal
		self.new_total_payable = total_payable

	def before_submit(self):
		if self.status != "Approved":
			frappe.throw("Only an Approved restructure request can be applied. Set the status to Approved first.")

	def on_submit(self):
		self.apply_restructure()
		self.db_set("status", "Applied")

		if self.collection_case:
			from car_showroom.car_showroom.doctype.collection_case.collection_case import close_case_for_agreement
			close_case_for_agreement(self.hire_purchase_agreement, "Restructured")

	def on_cancel(self):
		if self.status == "Applied":
			frappe.throw(
				"An applied restructure cannot be cancelled, since the schedule has already "
				"been rebuilt. Raise a new Loan Restructure Request if terms need to change again."
			)
		self.status = "Rejected"

	def apply_restructure(self):
		agreement = self.hire_purchase_agreement

		# Keep paid installments as history; drop everything still open so the
		# new schedule can take over from the effective date.
		frappe.db.delete("Hire Purchase Installment", {"hire_purchase_agreement": agreement, "status": ["!=", "Paid"]})

		n = max(1, round(flt(self.new_term_months) / 12 * PERIODS_PER_YEAR.get(self.new_frequency or "Monthly", 12)))
		period_rate = (flt(self.new_interest_rate) / 100) / PERIODS_PER_YEAR.get(self.new_frequency or "Monthly", 12)
		principal = flt(self.new_principal)
		balance = principal

		for i in range(1, n + 1):
			opening = balance
			interest_component = opening * period_rate
			principal_component = flt(self.new_installment_amount) - interest_component
			if i == n:
				principal_component = opening
			closing = opening - principal_component
			amount_due = principal_component + interest_component

			frappe.get_doc({
				"doctype": "Hire Purchase Installment",
				"hire_purchase_agreement": agreement,
				"installment_number": i,
				"due_date": _period_step(self.restructure_effective_date, self.new_frequency, i),
				"opening_balance": opening,
				"principal": principal_component,
				"interest": interest_component,
				"fees": 0,
				"penalty": 0,
				"amount_due": amount_due,
				"amount_paid": 0,
				"closing_balance": closing,
				"status": "Upcoming",
				"is_restructured": 1,
			}).insert(ignore_permissions=True)

			balance = closing

		frappe.db.set_value("Hire Purchase Agreement", agreement, {
			"frequency": self.new_frequency,
			"interest_rate": self.new_interest_rate,
			"installment_amount": self.new_installment_amount,
			"total_interest": self.new_total_interest,
			"total_payable": self.new_total_payable,
			"outstanding_balance": self.new_total_payable,
			"status": "Active",
		})
		frappe.db.commit()


def _period_step(start_date, frequency, period_index):
	start = getdate(start_date)
	if frequency == "Weekly":
		return add_days(start, 7 * period_index)
	if frequency == "Biweekly":
		return add_days(start, 14 * period_index)
	return add_months(start, period_index)
