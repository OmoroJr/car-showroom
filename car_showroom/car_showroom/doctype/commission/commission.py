# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Commission(Document):
	def validate(self):
		self.apply_defaults()
		self.calculate_commission()

	def apply_defaults(self):
		if not self.commission_type or not self.rate:
			settings = frappe.get_single("Sales Settings")
			if not self.commission_type:
				self.commission_type = settings.default_commission_type or "Gross-Profit-Based"
			if self.commission_type in ("Percentage", "Gross-Profit-Based") and not self.rate:
				self.rate = settings.default_commission_rate or 0

	def calculate_commission(self):
		if self.commission_type == "Fixed":
			self.commission_amount = flt(self.fixed_amount)
		else:
			# Percentage and Gross-Profit-Based both apply rate% to gross profit.
			# Tiered commission structures can extend this method later.
			self.commission_amount = flt(self.gross_profit) * flt(self.rate) / 100

	def on_update_after_submit(self):
		pass

	def approve(self):
		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.save()
