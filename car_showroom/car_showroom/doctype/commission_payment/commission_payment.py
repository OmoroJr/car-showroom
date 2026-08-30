# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommissionPayment(Document):

	def on_update(self):
		if self.status == "Paid" and self.vehicle_sale:
			frappe.db.set_value("Vehicle Sale", self.vehicle_sale, "commission_status", "Paid")
