# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VehiclePayment(Document):

	def validate(self):
		self.set_receipt_number()
		self.check_sale_status()

	def set_receipt_number(self):
		if self.receipt_number:
			return
		year = frappe.utils.nowdate()[:4]
		prefix = f"RCT-{year}-"
		last = frappe.db.sql(
			"""
			select receipt_number from `tabVehicle Payment`
			where receipt_number like %s order by creation desc limit 1
			""",
			(prefix + "%",),
		)
		if last and last[0][0]:
			try:
				last_serial = int(last[0][0].split("-")[-1])
			except ValueError:
				last_serial = 0
		else:
			last_serial = 0
		self.receipt_number = f"{prefix}{last_serial + 1:05d}"

	def check_sale_status(self):
		if not self.sale:
			return
		sale_docstatus = frappe.db.get_value("Vehicle Sale", self.sale, "docstatus")
		if sale_docstatus == 2:
			frappe.throw(frappe._("Cannot record a payment against a cancelled sale."))

	def on_submit(self):
		self.reallocate_sale_balance()

	def on_cancel(self):
		self.reallocate_sale_balance()

	def reallocate_sale_balance(self):
		sale = frappe.get_doc("Vehicle Sale", self.sale)
		sale.calculate_totals()
		sale.save(ignore_permissions=True)
		if sale.balance_due <= 0 and sale.status == "Confirmed":
			sale.db_set("status", "Fully Paid")
