# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VehicleExpense(Document):

	def on_update(self):
		self.refresh_vehicle_costs()

	def on_trash(self):
		self.refresh_vehicle_costs()

	def refresh_vehicle_costs(self):
		if not self.vehicle:
			return
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		vehicle.calculate_costs()
		vehicle.save(ignore_permissions=True)
