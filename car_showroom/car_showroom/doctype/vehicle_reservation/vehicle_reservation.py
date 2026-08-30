# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VehicleReservation(Document):

	def validate(self):
		self.check_vehicle_available()

	def check_vehicle_available(self):
		if self.status != "Active" or not self.vehicle:
			return

		vehicle_status = frappe.db.get_value("Vehicle", self.vehicle, "status")
		if vehicle_status not in ("Available", "Reserved"):
			frappe.throw(
				frappe._("Vehicle {0} is {1} and cannot be reserved.").format(
					self.vehicle, vehicle_status
				)
			)

		# another active reservation on the same vehicle?
		other = frappe.db.exists(
			"Vehicle Reservation",
			{"vehicle": self.vehicle, "status": "Active", "name": ("!=", self.name or "")},
		)
		if other:
			frappe.throw(
				frappe._("Vehicle {0} already has an active reservation ({1}).").format(
					self.vehicle, other
				)
			)

	def on_update(self):
		self.sync_vehicle_status()

	def sync_vehicle_status(self):
		if not self.vehicle:
			return
		current = frappe.db.get_value("Vehicle", self.vehicle, "status")
		if self.status == "Active" and current == "Available":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "Reserved")
		elif self.status in ("Expired", "Cancelled") and current == "Reserved":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "Available")


def auto_expire_reservations():
	"""Daily scheduled job: release reservations past their expiry date."""
	expired = frappe.get_all(
		"Vehicle Reservation",
		filters={"status": "Active", "expiry_date": ("<", frappe.utils.nowdate())},
		pluck="name",
	)
	for name in expired:
		doc = frappe.get_doc("Vehicle Reservation", name)
		doc.status = "Expired"
		doc.save(ignore_permissions=True)
