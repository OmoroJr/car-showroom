# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _


class VehicleSale(Document):
	def validate(self):
		self.check_no_duplicate_active_sale()
		self.pull_vehicle_cost()
		self.calculate_totals()

	def check_no_duplicate_active_sale(self):
		"""Data integrity: a vehicle cannot have two active (non-cancelled) sales."""
		existing = frappe.db.exists(
			"Vehicle Sale",
			{
				"vehicle": self.vehicle,
				"status": ["not in", ["Cancelled"]],
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				_("Vehicle {0} already has an active sale record ({1}). Cancel it first.")
				.format(self.vehicle, existing)
			)

	def pull_vehicle_cost(self):
		self.vehicle_cost = frappe.db.get_value("Vehicle", self.vehicle, "total_cost") or 0

	def calculate_totals(self):
		self.net_sale_price = (
			flt(self.cash_price) - flt(self.discount) - flt(self.trade_in_value)
		)
		self.balance = flt(self.net_sale_price) - flt(self.deposit)
		self.gross_profit = flt(self.net_sale_price) - flt(self.vehicle_cost)
		self.gross_margin = (
			(self.gross_profit / self.net_sale_price * 100) if self.net_sale_price else 0
		)

	def on_submit(self):
		if self.status == "Draft":
			self.status = "Confirmed"
		frappe.db.set_value("Vehicle", self.vehicle, "status", "Sold")
		self.create_commission_record()

	def on_cancel(self):
		self.status = "Cancelled"
		current = frappe.db.get_value("Vehicle", self.vehicle, "status")
		if current == "Sold":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "Ready for Sale")

	def create_commission_record(self):
		if not self.salesperson:
			return
		if frappe.db.exists("Commission", {"vehicle_sale": self.name}):
			return
		frappe.get_doc({
			"doctype": "Commission",
			"salesperson": self.salesperson,
			"vehicle_sale": self.name,
			"branch": self.branch,
			"commission_type": "Gross-Profit-Based",
			"gross_profit": self.gross_profit,
			"status": "Pending",
		}).insert(ignore_permissions=True)
