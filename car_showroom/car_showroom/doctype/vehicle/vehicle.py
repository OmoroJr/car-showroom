# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff, flt


class Vehicle(Document):
	def autoname(self):
		if not self.stock_number:
			self.stock_number = make_stock_number(self)
		self.name = self.stock_number

	def before_insert(self):
		if not self.date_acquired:
			self.date_acquired = nowdate()
		self._previous_status = None

	def before_save(self):
		# capture previous status before it's overwritten, for the status log
		if not self.is_new():
			previous = frappe.db.get_value("Vehicle", self.name, "status")
			self._previous_status = previous if previous != self.status else None
		else:
			self._previous_status = None

		recalculate_cost_and_profit(self)
		update_days_in_stock_for_doc(self)

	def on_update(self):
		if getattr(self, "_previous_status", None):
			log_status_change(self)


def make_stock_number(doc):
	"""Generate a stock number like MSA-2026-00001, scoped per calendar year."""
	from frappe.model.naming import make_autoname

	prefix = "MSA"
	year = nowdate()[:4]
	return make_autoname(f"{prefix}-{year}-.#####")


def recalculate_cost_and_profit(doc):
	total_cost = sum(flt(row.amount) for row in (doc.cost_entries or []))
	doc.total_cost = total_cost

	selling_price = flt(doc.asking_price) or flt(doc.market_price)
	if selling_price:
		doc.gross_profit = selling_price - total_cost
		doc.gross_margin = (doc.gross_profit / selling_price * 100) if selling_price else 0
	else:
		doc.gross_profit = 0
		doc.gross_margin = 0


def update_days_in_stock_for_doc(doc):
	if doc.date_acquired:
		doc.days_in_stock = date_diff(nowdate(), doc.date_acquired)


def log_status_change(doc):
	frappe.get_doc({
		"doctype": "Vehicle Status Log",
		"vehicle": doc.name,
		"previous_status": doc._previous_status,
		"new_status": doc.status,
		"changed_by": frappe.session.user,
		"changed_on": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)


def update_days_in_stock():
	"""Scheduled daily job: refresh days_in_stock for all vehicles still in stock."""
	in_stock_statuses = [
		"Sourced", "Purchased", "In Transit", "At Port", "Under Clearing", "Cleared",
		"At Yard", "Under Inspection", "Under Repair", "Ready for Sale", "Advertised",
		"Reserved", "Consignment", "Wholesale",
	]
	vehicles = frappe.get_all(
		"Vehicle",
		filters={"status": ["in", in_stock_statuses], "date_acquired": ["is", "set"]},
		fields=["name", "date_acquired"],
	)
	for v in vehicles:
		days = date_diff(nowdate(), v.date_acquired)
		frappe.db.set_value("Vehicle", v.name, "days_in_stock", days, update_modified=False)
	frappe.db.commit()
