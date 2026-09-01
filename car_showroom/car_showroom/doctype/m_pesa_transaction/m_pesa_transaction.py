# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MPesaTransaction(Document):
	def after_insert(self):
		self.try_auto_match_and_post()

	def try_auto_match_and_post(self):
		if not self.hire_purchase_agreement:
			self.match_by_phone()

		if not self.hire_purchase_agreement:
			frappe.db.set_value("M-Pesa Transaction", self.name, "status", "Unmatched")
			return

		frappe.db.set_value("M-Pesa Transaction", self.name, "status", "Matched")
		self.create_payment()

	def match_by_phone(self):
		if not self.phone_number:
			return
		customer = frappe.db.get_value("Customer", {"phone": self.phone_number}, "name")
		if not customer:
			return
		agreement = frappe.db.get_value(
			"Hire Purchase Agreement",
			{"customer": customer, "status": "Active"},
			"name",
			order_by="creation desc",
		)
		if agreement:
			self.hire_purchase_agreement = agreement
			self.customer = customer
			frappe.db.set_value("M-Pesa Transaction", self.name, {
				"hire_purchase_agreement": agreement,
				"customer": customer,
			})

	def create_payment(self):
		payment = frappe.get_doc({
			"doctype": "Payment",
			"hire_purchase_agreement": self.hire_purchase_agreement,
			"customer": self.customer,
			"payment_date": (self.transaction_date or frappe.utils.nowdate()),
			"amount": self.amount,
			"payment_method": "M-Pesa",
			"mpesa_transaction": self.name,
		})
		payment.insert(ignore_permissions=True)
		payment.submit()

		frappe.db.set_value("M-Pesa Transaction", self.name, {
			"payment": payment.name,
			"status": "Posted",
		})
