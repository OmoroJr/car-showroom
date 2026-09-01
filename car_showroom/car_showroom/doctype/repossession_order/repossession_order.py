# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class RepossessionOrder(Document):
	def validate(self):
		if self.hire_purchase_agreement:
			agreement = frappe.db.get_value(
				"Hire Purchase Agreement", self.hire_purchase_agreement,
				["customer", "vehicle", "outstanding_balance"], as_dict=True,
			)
			if agreement:
				self.customer = agreement.customer
				self.vehicle = agreement.vehicle
				self.outstanding_balance_at_order = agreement.outstanding_balance

		if self.status == "Authorized" and not self.authorized_by:
			self.authorized_by = frappe.session.user
			self.authorization_date = nowdate()

	def before_submit(self):
		if self.status != "Recovered":
			frappe.throw("The vehicle must be marked Recovered before this order can be submitted.")

	def on_submit(self):
		frappe.db.set_value("Hire Purchase Agreement", self.hire_purchase_agreement, "status", "Repossessed")
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Repossessed")

		if self.storage_location:
			frappe.db.set_value(
				"Yard Location", self.storage_location,
				{"is_occupied": 1, "current_vehicle": self.vehicle},
			)

		if self.collection_case:
			from car_showroom.car_showroom.doctype.collection_case.collection_case import close_case_for_agreement
			close_case_for_agreement(self.hire_purchase_agreement, "Repossessed")

	def on_cancel(self):
		frappe.db.set_value("Hire Purchase Agreement", self.hire_purchase_agreement, "status", "Defaulted")
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Under Inspection")

		if self.storage_location:
			frappe.db.set_value(
				"Yard Location", self.storage_location,
				{"is_occupied": 0, "current_vehicle": None},
			)
