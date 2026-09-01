# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Quotation(Document):
	def validate(self):
		self.calculate_total_payable()

	def calculate_total_payable(self):
		self.total_payable = (
			flt(self.cash_price)
			- flt(self.discount)
			- flt(self.trade_in_value)
			+ flt(self.insurance)
			+ flt(self.transfer_fee)
			+ flt(self.other_fees)
		)
