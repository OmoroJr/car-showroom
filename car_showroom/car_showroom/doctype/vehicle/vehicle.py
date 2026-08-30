# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.website.website_generator import WebsiteGenerator


class Vehicle(WebsiteGenerator):

	def validate(self):
		self.set_stock_number()
		self.calculate_costs()
		self.set_route()

	def set_stock_number(self):
		"""Auto-generate stock number as <branch_code>-<year>-<serial>, e.g. MSA-2026-00001."""
		if self.stock_number:
			return
		if not self.branch:
			return

		branch_code = frappe.db.get_value("Dealership Branch", self.branch, "branch_code") or "STK"
		year = frappe.utils.nowdate()[:4]
		prefix = f"{branch_code}-{year}-"

		last = frappe.db.sql(
			"""
			select stock_number from `tabVehicle`
			where stock_number like %s
			order by creation desc limit 1
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

		self.stock_number = f"{prefix}{last_serial + 1:05d}"

	def calculate_costs(self):
		cost_fields = [
			"purchase_price", "clearing_cost", "transport_cost", "repair_cost",
			"inspection_cost", "insurance_cost", "other_costs",
		]
		upfront_cost = sum(flt(self.get(f)) for f in cost_fields)
		posted_expenses = flt(frappe.db.sql(
			"select coalesce(sum(amount), 0) from `tabVehicle Expense` where vehicle = %s",
			(self.name,),
		)[0][0]) if not self.is_new() else 0

		self.total_cost = upfront_cost + posted_expenses

		if self.asking_price:
			self.expected_profit = flt(self.asking_price) - flt(self.total_cost)

	def set_route(self):
		"""Slug used for the public vehicle detail page, e.g.
		vehicles/toyota-prado-2022-msa-2026-00001."""
		if self.route:
			return
		base = "-".join(filter(None, [self.make, self.model, str(self.year or ""), self.stock_number]))
		self.route = "vehicles/" + frappe.utils.scrub(base).replace("_", "-")

	def get_context(self, context):
		"""Powers templates/generators/vehicle.html for the public website."""
		context.no_cache = 1
		context.vehicle = self
		context.cover_image = next(
			(img.image for img in self.images if img.is_cover), self.images[0].image if self.images else None
		)
		context.similar_vehicles = frappe.get_all(
			"Vehicle",
			filters={
				"make": self.make, "status": "Available", "is_published": 1,
				"name": ("!=", self.name),
			},
			fields=["name", "route", "make", "model", "year", "asking_price"],
			limit_page_length=4,
		)
		context.title = f"{self.make} {self.model} {self.year or ''}".strip()

	def on_update(self):
		pass


def validate_vehicle(doc, method=None):
	"""Guard rules for Vehicle status transitions (business rules #1-#3).

	- A vehicle cannot be sold twice: once Sold/Delivered, it can only move to
	  Delivered or Returned (reversal), not back to Available/Reserved silently.
	- A Reserved vehicle should not be marked Sold without the reservation
	  being converted first (enforced fully once the Reservation doctype
	  lands in a later phase; here we just prevent silently skipping status).
	"""
	if not doc.get("__islocal") and doc.has_value_changed("status"):
		previous_status = frappe.db.get_value("Vehicle", doc.name, "status")
		if previous_status in ("Sold", "Delivered") and doc.status in ("Available", "Reserved"):
			frappe.throw(
				frappe._(
					"Vehicle {0} is already {1} and cannot be moved back to {2} directly. "
					"Use a proper return/cancellation workflow instead."
				).format(doc.name, previous_status, doc.status)
			)
