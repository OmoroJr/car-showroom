# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class VehicleSale(Document):

	def validate(self):
		self.calculate_totals()
		self.check_business_rules()

	def calculate_totals(self):
		self.total_amount = (
			flt(self.selling_price) - flt(self.discount) - flt(self.trade_in_value)
		)
		if self.docstatus == 0:
			# balance recalculated fully only pre-submit; post-submit it is
			# maintained incrementally by Vehicle Payment records.
			paid = flt(self.deposit_paid) + self.get_total_payments()
			self.balance_due = flt(self.total_amount) - paid

		self.cost_of_vehicle = flt(frappe.db.get_value("Vehicle", self.vehicle, "total_cost"))
		self.gross_profit = flt(self.total_amount) - flt(self.cost_of_vehicle)

		rate = flt(self.commission_rate)
		self.commission_amount = flt(self.gross_profit) * rate / 100 if rate else 0

	def get_total_payments(self):
		total = frappe.db.sql(
			"""
			select coalesce(sum(amount), 0) from `tabVehicle Payment`
			where sale = %s and docstatus = 1
			""",
			(self.name,),
		)
		return flt(total[0][0]) if total else 0

	def check_business_rules(self):
		if not self.vehicle:
			return

		vehicle_status = frappe.db.get_value("Vehicle", self.vehicle, "status")

		# Rule: a vehicle cannot be sold twice.
		if self.is_new() and vehicle_status in ("Sold", "Delivered"):
			frappe.throw(
				frappe._("Vehicle {0} is already {1} and cannot be sold again.").format(
					self.vehicle, vehicle_status
				)
			)

		# Rule: a reserved vehicle cannot be sold to a different customer
		# without authorization (here: without cancelling/converting the
		# reservation first).
		if vehicle_status == "Reserved" and not self.reservation:
			active_reservation = frappe.db.get_value(
				"Vehicle Reservation",
				{"vehicle": self.vehicle, "status": "Active"},
				["name", "customer"],
				as_dict=True,
			)
			if active_reservation and active_reservation.customer != self.customer:
				frappe.throw(
					frappe._(
						"Vehicle {0} is actively reserved for another customer ({1}). "
						"Cancel or convert reservation {2} first."
					).format(self.vehicle, active_reservation.customer, active_reservation.name)
				)

		# Rule: cannot mark as Delivered until balance is cleared.
		if self.status == "Delivered" and flt(self.balance_due) > 0:
			frappe.throw(
				frappe._(
					"Cannot mark this sale as Delivered while a balance of {0} is still due."
				).format(self.balance_due)
			)

	def on_submit(self):
		frappe.db.set_value(
			"Vehicle", self.vehicle,
			{"status": "Sold", "actual_profit": self.gross_profit},
		)
		if self.reservation:
			frappe.db.set_value("Vehicle Reservation", self.reservation, "status", "Converted to Sale")
		if self.trade_in:
			frappe.db.set_value("Vehicle Trade In", self.trade_in, "status", "Applied")
		if self.status == "Draft":
			self.db_set("status", "Confirmed")

	def on_cancel(self):
		"""Reversal workflow (business rule: no hard deletes of financial docs)."""
		current = frappe.db.get_value("Vehicle", self.vehicle, "status")
		if current == "Sold":
			frappe.db.set_value("Vehicle", self.vehicle, "status", "Available")
		self.db_set("status", "Cancelled")

	@frappe.whitelist()
	def create_sales_invoice(self):
		"""Best-effort ERPNext accounting integration.

		Requires ERPNext to be installed on the site, and a default Item and
		Income Account configured for vehicle sales (set these up in ERPNext
		before calling this). Creates/reuses an ERPNext Customer matching this
		Showroom Customer by name.
		"""
		if "erpnext" not in frappe.get_installed_apps():
			frappe.throw(
				frappe._(
					"ERPNext is not installed on this site, so a Sales Invoice "
					"cannot be created automatically. Record accounting entries "
					"manually, or install ERPNext to enable this."
				)
			)

		if self.sales_invoice:
			frappe.throw(frappe._("Sales Invoice {0} already exists for this sale.").format(self.sales_invoice))

		customer_name = frappe.db.get_value("Showroom Customer", self.customer, "full_name")
		erp_customer = frappe.db.exists("Customer", customer_name)
		if not erp_customer:
			erp_customer_doc = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Individual",
			})
			erp_customer_doc.insert(ignore_permissions=True)
			erp_customer = erp_customer_doc.name

		item_code = frappe.db.get_value("Item", {"item_name": self.vehicle}, "name")
		if not item_code:
			frappe.throw(
				frappe._(
					"No ERPNext Item found for vehicle {0}. Create an Item for "
					"this vehicle (or a generic 'Vehicle Sale' service item) "
					"before generating the invoice."
				).format(self.vehicle)
			)

		invoice = frappe.get_doc({
			"doctype": "Sales Invoice",
			"customer": erp_customer,
			"items": [{
				"item_code": item_code,
				"qty": 1,
				"rate": self.total_amount,
			}],
		})
		invoice.insert(ignore_permissions=True)
		self.db_set("sales_invoice", invoice.name)
		return invoice.name
