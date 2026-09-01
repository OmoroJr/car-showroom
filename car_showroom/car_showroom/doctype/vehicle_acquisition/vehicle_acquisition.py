# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleAcquisition(Document):
	def validate(self):
		self.balance = flt(self.purchase_price) - flt(self.deposit)

	def on_submit(self):
		self.push_cost_to_vehicle()

	def push_cost_to_vehicle(self):
		"""Add/refresh a 'Purchase' cost entry on the linked Vehicle's cost sheet."""
		if not self.vehicle:
			return
		vehicle = frappe.get_doc("Vehicle", self.vehicle)

		existing = None
		for row in vehicle.cost_entries:
			if row.reference == self.name:
				existing = row
				break

		if existing:
			existing.amount = self.purchase_price
			existing.date = self.purchase_date
		else:
			vehicle.append("cost_entries", {
				"cost_type": "Purchase",
				"amount": self.purchase_price,
				"date": self.purchase_date,
				"reference": self.name,
				"remarks": f"From Vehicle Acquisition {self.name} ({self.acquisition_type})",
			})

		vehicle.save(ignore_permissions=True)
