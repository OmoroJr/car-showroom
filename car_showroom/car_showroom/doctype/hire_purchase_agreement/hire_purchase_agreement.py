# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_days, add_months, getdate

PERIODS_PER_YEAR = {
	"Weekly": 52,
	"Biweekly": 26,
	"Monthly": 12,
	"Custom": 12,
}


class HirePurchaseAgreement(Document):
	def validate(self):
		self.amount_financed = flt(self.cash_price) - flt(self.deposit)
		if self.amount_financed < 0:
			frappe.throw("Deposit cannot exceed the cash price.")

	def before_submit(self):
		self.calculate_schedule_totals()

	def on_submit(self):
		self.status = "Active"
		generate_installment_schedule(self)
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Sold")
		self.link_credit_assessment()

	def on_cancel(self):
		self.status = "Cancelled"
		frappe.db.delete("Hire Purchase Installment", {"hire_purchase_agreement": self.name})
		self.unlink_credit_assessment()

	def link_credit_assessment(self):
		"""Point the Credit Assessment that led to this agreement forward to it,
		and move the originating Credit Application to its final state."""
		if not self.credit_application:
			return

		assessment = frappe.db.get_value(
			"Credit Assessment",
			{"credit_application": self.credit_application, "docstatus": 1},
			"name",
			order_by="modified desc",
		)
		if assessment:
			frappe.db.set_value("Credit Assessment", assessment, "hire_purchase_agreement", self.name)

		frappe.db.set_value("Credit Application", self.credit_application, "status", "Agreement Created")

	def unlink_credit_assessment(self):
		if not self.credit_application:
			return

		assessment = frappe.db.get_value(
			"Credit Assessment",
			{"credit_application": self.credit_application, "hire_purchase_agreement": self.name},
			"name",
		)
		if assessment:
			frappe.db.set_value("Credit Assessment", assessment, "hire_purchase_agreement", None)

		frappe.db.set_value("Credit Application", self.credit_application, "status", "Approved")

	def calculate_schedule_totals(self):
		"""Pre-submit preview of installment amount / total interest / total payable,
		without persisting individual installment rows yet (that happens on_submit)."""
		principal = flt(self.amount_financed)
		n = number_of_periods(self)
		period_rate = period_interest_rate(self)

		if self.interest_type == "Flat Rate":
			total_interest = principal * flt(self.interest_rate) / 100 * (flt(self.term_months) / 12)
			installment = (principal + total_interest) / n if n else 0
		elif self.interest_type in ("Reducing Balance", "Fixed Installment"):
			if period_rate:
				installment = principal * period_rate * (1 + period_rate) ** n / (
					(1 + period_rate) ** n - 1
				)
			else:
				installment = principal / n if n else 0
			total_interest = installment * n - principal
		else:
			# Custom Schedule: leave zero, to be entered/generated manually.
			installment = 0
			total_interest = 0

		self.installment_amount = installment
		self.total_interest = total_interest
		self.total_payable = (
			principal + total_interest + flt(self.processing_fee)
			+ flt(self.insurance_fee) + flt(self.other_fees)
		)
		self.outstanding_balance = self.total_payable


def number_of_periods(doc):
	freq = doc.frequency or "Monthly"
	periods_per_year = PERIODS_PER_YEAR.get(freq, 12)
	return max(1, round(flt(doc.term_months) / 12 * periods_per_year))


def period_interest_rate(doc):
	freq = doc.frequency or "Monthly"
	periods_per_year = PERIODS_PER_YEAR.get(freq, 12)
	return (flt(doc.interest_rate) / 100) / periods_per_year


def period_step(doc, period_index):
	"""Return the due date for the given 1-based period index."""
	freq = doc.frequency or "Monthly"
	start = getdate(doc.agreement_date)
	if freq == "Weekly":
		return add_days(start, 7 * period_index)
	if freq == "Biweekly":
		return add_days(start, 14 * period_index)
	# Monthly and Custom (falls back to monthly steps)
	return add_months(start, period_index)


def generate_installment_schedule(doc):
	"""Build the full amortization schedule as Hire Purchase Installment records."""
	frappe.db.delete("Hire Purchase Installment", {"hire_purchase_agreement": doc.name})

	principal = flt(doc.amount_financed)
	n = number_of_periods(doc)
	period_rate = period_interest_rate(doc)
	balance = principal

	if doc.interest_type == "Flat Rate":
		flat_interest_total = principal * flt(doc.interest_rate) / 100 * (flt(doc.term_months) / 12)
		principal_per_period = principal / n if n else 0
		interest_per_period = flat_interest_total / n if n else 0
	else:
		principal_per_period = None  # computed per period below
		interest_per_period = None

	for i in range(1, n + 1):
		opening = balance

		if doc.interest_type == "Flat Rate":
			principal_component = principal_per_period
			interest_component = interest_per_period
		else:
			interest_component = opening * period_rate
			principal_component = flt(doc.installment_amount) - interest_component
			if i == n:
				# absorb any rounding drift into the final installment
				principal_component = opening

		closing = opening - principal_component
		fees = 0
		if i == 1:
			fees = flt(doc.processing_fee) + flt(doc.insurance_fee) + flt(doc.other_fees)

		amount_due = principal_component + interest_component + fees

		frappe.get_doc({
			"doctype": "Hire Purchase Installment",
			"hire_purchase_agreement": doc.name,
			"installment_number": i,
			"due_date": period_step(doc, i),
			"opening_balance": opening,
			"principal": principal_component,
			"interest": interest_component,
			"fees": fees,
			"penalty": 0,
			"amount_due": amount_due,
			"amount_paid": 0,
			"closing_balance": closing,
			"status": "Upcoming",
		}).insert(ignore_permissions=True)

		balance = closing

	frappe.db.commit()


def recompute_outstanding_balance(agreement_name):
	rows = frappe.get_all(
		"Hire Purchase Installment",
		filters={"hire_purchase_agreement": agreement_name},
		fields=["amount_due", "amount_paid"],
	)
	outstanding = sum(flt(r.amount_due) - flt(r.amount_paid) for r in rows)
	frappe.db.set_value("Hire Purchase Agreement", agreement_name, "outstanding_balance", outstanding)
	if outstanding <= 0 and rows:
		frappe.db.set_value("Hire Purchase Agreement", agreement_name, "status", "Completed")
