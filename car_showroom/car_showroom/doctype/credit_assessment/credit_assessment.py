# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CreditAssessment(Document):
	def validate(self):
		self.fetch_customer()
		self.calculate_ratios()
		self.calculate_score_and_rating()

	def fetch_customer(self):
		if self.credit_application and not self.customer:
			self.customer = frappe.db.get_value(
				"Credit Application", self.credit_application, "customer"
			)

	def calculate_ratios(self):
		income = flt(self.monthly_income)
		if income:
			self.debt_to_income_ratio = (
				(flt(self.existing_obligations) + flt(self.proposed_installment)) / income * 100
			)
			self.installment_to_income_ratio = flt(self.proposed_installment) / income * 100
		else:
			self.debt_to_income_ratio = 0
			self.installment_to_income_ratio = 0

	def calculate_score_and_rating(self):
		"""
		Simple transparent scoring model (0-100), combining DTI and
		installment-to-income ratio. Credit officers can always override
		credit_score / risk_rating manually before approval.
		"""
		dti = flt(self.debt_to_income_ratio)
		iti = flt(self.installment_to_income_ratio)

		score = 100
		score -= max(0, dti - 30) * 1.5   # penalise DTI above 30%
		score -= max(0, iti - 40) * 2.0   # penalise installment load above 40%
		score = max(0, min(100, round(score)))

		if not self.credit_score:
			self.credit_score = score

		if self.credit_score >= 75:
			self.risk_rating = "Low"
		elif self.credit_score >= 55:
			self.risk_rating = "Medium"
		elif self.credit_score >= 35:
			self.risk_rating = "High"
		else:
			self.risk_rating = "Very High"

	def on_submit(self):
		if self.credit_application:
			frappe.db.set_value(
				"Credit Application", self.credit_application, "status", "Credit Officer Review"
			)
