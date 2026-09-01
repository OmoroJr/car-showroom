# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days


class Reservation(Document):
	def validate(self):
		if self.status == "Active":
			existing = frappe.db.exists(
				"Reservation",
				{
					"vehicle": self.vehicle,
					"status": "Active",
					"name": ["!=", self.name],
				},
			)
			if existing:
				frappe.throw(
					f"Vehicle {self.vehicle} already has an active reservation ({existing})."
				)

	def on_update(self):
		if self.status == "Active":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "Reserved")
		elif self.status in ("Expired", "Cancelled"):
			current = frappe.db.get_value("Vehicle", self.vehicle, "status")
			if current == "Reserved":
				frappe.db.set_value("Vehicle", self.vehicle, "status", "Ready for Sale")


def expire_due_reservations():
	"""Scheduled daily job: flip Active reservations past their expiry date to Expired."""
	due = frappe.get_all(
		"Reservation",
		filters={"status": "Active", "expiry_date": ["<", nowdate()]},
		fields=["name", "vehicle"],
	)
	for r in due:
		frappe.db.set_value("Reservation", r.name, "status", "Expired")
		current = frappe.db.get_value("Vehicle", r.vehicle, "status")
		if current == "Reserved":
			frappe.db.set_value("Vehicle", r.vehicle, "status", "Ready for Sale")
	frappe.db.commit()


def alert_expiring_reservations():
	"""Scheduled daily job: notify assigned salesperson 1 day before a reservation expires."""
	tomorrow = add_days(nowdate(), 1)
	expiring = frappe.get_all(
		"Reservation",
		filters={"status": "Active", "expiry_date": tomorrow},
		fields=["name", "vehicle", "customer", "salesperson"],
	)
	for r in expiring:
		if not r.salesperson:
			continue
		frappe.get_doc({
			"doctype": "Notification Log",
			"subject": f"Reservation {r.name} expires tomorrow",
			"for_user": r.salesperson,
			"type": "Alert",
			"document_type": "Reservation",
			"document_name": r.name,
		}).insert(ignore_permissions=True)
