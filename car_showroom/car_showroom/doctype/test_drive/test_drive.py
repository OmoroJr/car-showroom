# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TestDrive(Document):

	def validate(self):
		self.check_double_booking()

	def check_double_booking(self):
		"""Prevent overlapping test drives for the same vehicle on the same date."""
		if not (self.vehicle and self.date):
			return

		clashes = frappe.db.sql(
			"""
			select name, start_time, end_time from `tabTest Drive`
			where vehicle = %s
			and date = %s
			and name != %s
			and status in ('Scheduled', 'In Progress')
			""",
			(self.vehicle, self.date, self.name or ""),
			as_dict=True,
		)

		for clash in clashes:
			if self._times_overlap(clash.start_time, clash.end_time):
				frappe.throw(
					frappe._(
						"Vehicle {0} is already booked for a test drive ({1}) on {2}."
					).format(self.vehicle, clash.name, self.date)
				)

	def _times_overlap(self, other_start, other_end):
		# If either booking is missing explicit times, treat same-day bookings
		# as conflicting to be safe.
		if not (self.start_time and self.end_time and other_start and other_end):
			return True
		return self.start_time < other_end and other_start < self.end_time


def validate_test_drive(doc, method=None):
	doc.check_double_booking()


def sync_vehicle_status(doc, method=None):
	"""Keep Vehicle.status in step with the test drive lifecycle."""
	if not doc.vehicle:
		return

	current_status = frappe.db.get_value("Vehicle", doc.vehicle, "status")

	if doc.status == "In Progress" and current_status not in ("Sold", "Delivered", "Reserved"):
		frappe.db.set_value("Vehicle", doc.vehicle, "status", "On Test Drive")
	elif doc.status in ("Completed", "Cancelled") and current_status == "On Test Drive":
		frappe.db.set_value("Vehicle", doc.vehicle, "status", "Available")
