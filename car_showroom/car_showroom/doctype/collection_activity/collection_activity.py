# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CollectionActivity(Document):

	def validate(self):
		if self.activity_type == "Promise to Pay" and not self.promise_to_pay_date:
			frappe.throw(frappe._("Set a Promise to Pay Date for this activity type."))
