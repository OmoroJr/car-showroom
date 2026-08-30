# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleQuotation(Document):

	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		self.total_payable = (
			flt(self.selling_price)
			- flt(self.discount)
			- flt(self.trade_in_allowance)
			+ flt(self.insurance_amount)
			+ flt(self.transfer_charges)
			+ flt(self.other_charges)
		)
		self.balance = flt(self.total_payable) - flt(self.deposit)
