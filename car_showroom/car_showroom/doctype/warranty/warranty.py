# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Warranty(Document):

	def validate(self):
		if self.status != "Voided":
			if self.end_date and frappe.utils.getdate(self.end_date) < frappe.utils.getdate(frappe.utils.nowdate()):
				self.status = "Expired"
			else:
				self.status = "Active"


def expire_warranties():
	"""Daily scheduled job: flip Active warranties past their end date."""
	expiring = frappe.get_all(
		"Warranty",
		filters={"status": "Active", "end_date": ("<", frappe.utils.nowdate())},
		pluck="name",
	)
	for name in expiring:
		doc = frappe.get_doc("Warranty", name)
		doc.save(ignore_permissions=True)
