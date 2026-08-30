# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class HirePurchaseAgreement(Document):

	def validate(self):
		self.amount_financed = flt(self.cash_price) - flt(self.deposit)
		if not self.interest_calculation_method:
			settings = frappe.get_single("Hire Purchase Settings")
			self.interest_calculation_method = settings.default_interest_method or "Flat Rate"
		if self.status == "Draft" and self.amount_financed and self.number_of_installments:
			self.preview_totals()

	def preview_totals(self):
		"""Recompute headline totals (does not touch installment records)."""
		schedule = build_schedule(
			amount_financed=self.amount_financed,
			interest_rate=self.interest_rate,
			financing_period_months=self.financing_period_months,
			number_of_installments=self.number_of_installments,
			frequency=self.installment_frequency,
			method=self.interest_calculation_method,
			processing_fee=self.processing_fee,
			insurance=self.insurance,
			other_charges=self.other_charges,
			first_installment_date=self.first_installment_date or self.start_date,
		)
		self.total_interest = schedule["total_interest"]
		self.total_amount_payable = schedule["total_amount_payable"]
		self.installment_amount = schedule["rows"][0]["total"] if schedule["rows"] else 0
		self.final_installment = schedule["rows"][-1]["total"] if schedule["rows"] else 0

	# ------------------------------------------------------------------
	# Approval workflow (business rule: HP agreements require approval
	# before activation; approval limits are configurable, not hard-coded).
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def submit_for_approval(self):
		if self.status != "Draft":
			frappe.throw(frappe._("Only a Draft agreement can be submitted for approval."))
		if not self.credit_assessment:
			frappe.throw(frappe._("Attach a Credit Assessment before submitting for approval."))

		self.required_approver_role = get_required_approver_role(self.amount_financed)
		self.append("approval_log", {
			"approver_role": self.required_approver_role,
			"approver": frappe.session.user,
			"action": "Submitted",
			"comments": "Submitted for approval",
		})
		self.status = "Pending Approval"
		self.save()

	@frappe.whitelist()
	def approve(self, comments=None):
		self._check_approver_authorized()
		self.append("approval_log", {
			"approver_role": self.required_approver_role,
			"approver": frappe.session.user,
			"action": "Approved",
			"comments": comments,
		})
		self.status = "Approved"
		self.save()

	@frappe.whitelist()
	def reject(self, comments=None):
		self._check_approver_authorized()
		self.append("approval_log", {
			"approver_role": self.required_approver_role,
			"approver": frappe.session.user,
			"action": "Rejected",
			"comments": comments,
		})
		self.status = "Rejected"
		self.save()

	def _check_approver_authorized(self):
		if self.status != "Pending Approval":
			frappe.throw(frappe._("This agreement is not awaiting approval."))
		user_roles = frappe.get_roles(frappe.session.user)
		if "System Manager" in user_roles:
			return
		if self.required_approver_role and self.required_approver_role not in user_roles:
			frappe.throw(
				frappe._("You need the '{0}' role to act on this approval.").format(
					self.required_approver_role
				)
			)

	# ------------------------------------------------------------------
	# Activation + installment schedule generation (business rule:
	# installments must be automatically generated).
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def activate(self):
		if self.status != "Approved":
			frappe.throw(frappe._("Only an Approved agreement can be activated."))
		if not self.vehicle_sale:
			frappe.throw(
				frappe._("Link the Vehicle Sale for this agreement before activating it.")
			)
		if frappe.db.exists("Hire Purchase Installment", {"hire_purchase_agreement": self.name}):
			frappe.throw(frappe._("Installments already exist for this agreement."))

		schedule = build_schedule(
			amount_financed=self.amount_financed,
			interest_rate=self.interest_rate,
			financing_period_months=self.financing_period_months,
			number_of_installments=self.number_of_installments,
			frequency=self.installment_frequency,
			method=self.interest_calculation_method,
			processing_fee=self.processing_fee,
			insurance=self.insurance,
			other_charges=self.other_charges,
			first_installment_date=self.first_installment_date or self.start_date,
		)

		for row in schedule["rows"]:
			frappe.get_doc({
				"doctype": "Hire Purchase Installment",
				"hire_purchase_agreement": self.name,
				"installment_number": row["installment_number"],
				"due_date": row["due_date"],
				"principal": row["principal"],
				"interest": row["interest"],
				"fees": row["fees"],
			}).insert(ignore_permissions=True)

		self.total_interest = schedule["total_interest"]
		self.total_amount_payable = schedule["total_amount_payable"]
		self.installment_amount = schedule["rows"][0]["total"]
		self.final_installment = schedule["rows"][-1]["total"]
		self.status = "Active"
		self.save()


# ==========================================================================
# Hire Purchase calculator — usable standalone (e.g. from a marketplace
# "Calculate Hire Purchase" widget) or from the Agreement above.
# ==========================================================================

PERIODS_PER_YEAR = {"Weekly": 52, "Bi-weekly": 26, "Monthly": 12}


def _next_due_date(current_date, frequency):
	if frequency == "Weekly":
		return frappe.utils.add_days(current_date, 7)
	if frequency == "Bi-weekly":
		return frappe.utils.add_days(current_date, 14)
	return frappe.utils.add_months(current_date, 1)


def build_schedule(amount_financed, interest_rate, financing_period_months,
                    number_of_installments, frequency, method,
                    processing_fee=0, insurance=0, other_charges=0,
                    first_installment_date=None):
	"""Pure calculation helper: returns a schedule dict, does not touch the DB.

	method: "Flat Rate" or "Reducing Balance"
	"""
	amount_financed = flt(amount_financed)
	interest_rate = flt(interest_rate)
	number_of_installments = int(number_of_installments or 0)
	total_fees = flt(processing_fee) + flt(insurance) + flt(other_charges)

	if number_of_installments <= 0:
		return {"rows": [], "total_interest": 0, "total_amount_payable": total_fees}

	fee_per_installment = total_fees / number_of_installments
	annual_rate = interest_rate / 100

	rows = []
	due_date = first_installment_date or frappe.utils.nowdate()

	if method == "Reducing Balance":
		periods_per_year = PERIODS_PER_YEAR.get(frequency, 12)
		periodic_rate = annual_rate / periods_per_year if periods_per_year else 0

		if periodic_rate:
			installment_pi = amount_financed * periodic_rate / (
				1 - (1 + periodic_rate) ** -number_of_installments
			)
		else:
			installment_pi = amount_financed / number_of_installments

		balance = amount_financed
		total_interest = 0
		for i in range(1, number_of_installments + 1):
			interest = balance * periodic_rate
			principal = installment_pi - interest
			if i == number_of_installments:
				principal = balance  # absorb rounding on the last installment
			balance -= principal
			total_interest += interest
			rows.append({
				"installment_number": i,
				"due_date": due_date,
				"principal": round(principal, 2),
				"interest": round(interest, 2),
				"fees": round(fee_per_installment, 2),
				"total": round(principal + interest + fee_per_installment, 2),
			})
			due_date = _next_due_date(due_date, frequency)

		total_interest = round(total_interest, 2)

	else:  # Flat Rate
		total_interest = amount_financed * annual_rate * (flt(financing_period_months) / 12)
		interest_per_installment = total_interest / number_of_installments
		principal_per_installment = amount_financed / number_of_installments

		allocated_principal = 0
		for i in range(1, number_of_installments + 1):
			principal = round(principal_per_installment, 2)
			if i == number_of_installments:
				principal = round(amount_financed - allocated_principal, 2)
			allocated_principal += principal
			rows.append({
				"installment_number": i,
				"due_date": due_date,
				"principal": principal,
				"interest": round(interest_per_installment, 2),
				"fees": round(fee_per_installment, 2),
				"total": round(principal + interest_per_installment + fee_per_installment, 2),
			})
			due_date = _next_due_date(due_date, frequency)

		total_interest = round(total_interest, 2)

	total_amount_payable = round(amount_financed + total_interest + total_fees, 2)
	return {
		"rows": rows,
		"total_interest": total_interest,
		"total_amount_payable": total_amount_payable,
	}


@frappe.whitelist()
def calculate_schedule_preview(cash_price, deposit, interest_rate, financing_period_months,
                                number_of_installments, frequency, method,
                                processing_fee=0, insurance=0, other_charges=0,
                                first_installment_date=None):
	"""Whitelisted entry point for a standalone Hire Purchase calculator
	(e.g. a public 'Calculate Hire Purchase' widget) - takes raw inputs and
	returns the computed schedule without creating any documents."""
	amount_financed = flt(cash_price) - flt(deposit)
	return build_schedule(
		amount_financed=amount_financed,
		interest_rate=interest_rate,
		financing_period_months=financing_period_months,
		number_of_installments=number_of_installments,
		frequency=frequency,
		method=method,
		processing_fee=processing_fee,
		insurance=insurance,
		other_charges=other_charges,
		first_installment_date=first_installment_date,
	)


def get_required_approver_role(amount_financed):
	settings = frappe.get_single("Hire Purchase Settings")
	tiers = sorted(settings.approval_limits, key=lambda r: (flt(r.up_to_amount) or float("inf")))
	amount_financed = flt(amount_financed)

	for tier in tiers:
		limit = flt(tier.up_to_amount)
		if limit and amount_financed <= limit:
			return tier.approver_role

	# no tier matched (amount exceeds all finite limits, or a 0/blank limit
	# tier exists to represent "no upper limit") -> use the last configured
	# tier as the ultimate authority.
	if tiers:
		return tiers[-1].approver_role

	frappe.throw(
		frappe._(
			"No approval limits are configured in Hire Purchase Settings. "
			"Add at least one approval tier before submitting agreements."
		)
	)
