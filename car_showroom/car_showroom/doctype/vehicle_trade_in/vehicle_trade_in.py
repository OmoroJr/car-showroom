# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class TradeIn(Document):

	def validate(self):
		self.calculate_net_value()

	def calculate_net_value(self):
		self.net_trade_in_value = flt(self.trade_in_value) - flt(self.outstanding_finance)
