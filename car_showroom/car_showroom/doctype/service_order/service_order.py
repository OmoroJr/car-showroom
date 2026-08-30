# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ServiceOrder(Document):

	def validate(self):
		self.total_cost = flt(self.parts_cost) + flt(self.labour_cost)
		self.check_warranty_coverage()

	def check_warranty_coverage(self):
		if not self.is_warranty_claim or not self.warranty:
			return
		warranty = frappe.get_doc("Warranty", self.warranty)
		if warranty.status != "Active":
			frappe.throw(
				frappe._("Warranty {0} is {1} and cannot cover this service order.").format(
					self.warranty, warranty.status
				)
			)
		if warranty.mileage_limit and self.odometer_reading and self.odometer_reading > warranty.mileage_limit:
			frappe.throw(
				frappe._(
					"Odometer reading {0} km exceeds the warranty's mileage limit of {1} km."
				).format(self.odometer_reading, warranty.mileage_limit)
			)
