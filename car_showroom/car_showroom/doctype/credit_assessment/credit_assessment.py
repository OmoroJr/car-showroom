# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CreditAssessment(Document):

	def validate(self):
		self.calculate_ratios()
		self.calculate_score_and_risk()

	def calculate_ratios(self):
		total_income = flt(self.monthly_income) + flt(self.other_income)
		if total_income <= 0:
			self.debt_to_income_ratio = 0
			self.installment_to_income_ratio = 0
			return

		obligations = flt(self.existing_loan_obligations) + flt(self.monthly_expenses)
		self.debt_to_income_ratio = (obligations / total_income) * 100
		self.installment_to_income_ratio = (flt(self.proposed_installment_amount) / total_income) * 100

	def calculate_score_and_risk(self):
		# Simple, transparent scoring: start at 100 and deduct for strain on
		# the customer's income. Administrators can refine this formula later.
		score = 100 - flt(self.debt_to_income_ratio) * 0.5 - flt(self.installment_to_income_ratio) * 0.7
		self.credit_score = max(0, min(100, round(score)))

		if self.credit_score >= 70:
			self.risk_rating = "Low"
		elif self.credit_score >= 40:
			self.risk_rating = "Medium"
		else:
			self.risk_rating = "High"
