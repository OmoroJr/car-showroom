# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class TestDrive(Document):
	def validate(self):
		self.check_conflicts()

	def check_conflicts(self):
		"""Prevent double-booking the same vehicle for an overlapping slot."""
		conflict = frappe.db.exists(
			"Test Drive",
			{
				"vehicle": self.vehicle,
				"scheduled_date": self.scheduled_date,
				"scheduled_time": self.scheduled_time,
				"status": ["not in", ["Cancelled", "Completed"]],
				"name": ["!=", self.name],
			},
		)
		if conflict:
			frappe.throw(
				_("Vehicle {0} already has a test drive scheduled at this time (see {1}).")
				.format(self.vehicle, conflict)
			)

	def on_update(self):
		if self.status == "In Progress":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "On Test Drive")
		elif self.status in ("Completed", "Cancelled"):
			current = frappe.db.get_value("Vehicle", self.vehicle, "status")
			if current == "On Test Drive":
				frappe.db.set_value("Vehicle", self.vehicle, "status", "Ready for Sale")
