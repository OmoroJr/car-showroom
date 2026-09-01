# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class TradeIn(Document):
	def validate(self):
		self.net_trade_in_value = flt(self.appraised_value) - flt(self.existing_finance_balance)
