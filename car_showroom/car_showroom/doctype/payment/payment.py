# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, random_string

# Fallback order if Finance Settings hasn't been configured yet.
DEFAULT_ORDER = ["Penalty", "Fees", "Interest", "Principal"]


class Payment(Document):
	def validate(self):
		if self.hire_purchase_agreement and not self.customer:
			self.customer = frappe.db.get_value(
				"Hire Purchase Agreement", self.hire_purchase_agreement, "customer"
			)

	def before_submit(self):
		from car_showroom.car_showroom.doctype.hire_purchase_agreement.hire_purchase_agreement import (
			recompute_outstanding_balance,
		)

		self.previous_balance = frappe.db.get_value(
			"Hire Purchase Agreement", self.hire_purchase_agreement, "outstanding_balance"
		) or 0
		self.receipt_number = self.name or f"RCPT-{random_string(8).upper()}"
		self.allocate_payment()
		recompute_outstanding_balance(self.hire_purchase_agreement)
		self.new_balance = frappe.db.get_value(
			"Hire Purchase Agreement", self.hire_purchase_agreement, "outstanding_balance"
		) or 0
		self.status = "Allocated"

	def allocate_payment(self):
		self.set("allocations", [])
		remaining = flt(self.amount)
		order = get_allocation_order()

		installments = frappe.get_all(
			"Hire Purchase Installment",
			filters={
				"hire_purchase_agreement": self.hire_purchase_agreement,
				"status": ["not in", ["Paid"]],
			},
			fields=["name", "principal", "interest", "fees", "penalty", "amount_due",
					"amount_paid"],
			order_by="installment_number asc",
		)

		for inst in installments:
			if remaining <= 0:
				break

			buckets = remaining_buckets(inst)
			total_paid_this_installment = 0

			for bucket in order:
				if remaining <= 0:
					break
				available = buckets.get(bucket, 0)
				if available <= 0:
					continue
				take = min(available, remaining)
				if take <= 0:
					continue
				self.append("allocations", {
					"installment": inst.name,
					"allocation_type": bucket,
					"amount_allocated": take,
				})
				remaining -= take
				total_paid_this_installment += take

			if total_paid_this_installment:
				new_amount_paid = flt(inst.amount_paid) + total_paid_this_installment
				new_status = "Paid" if new_amount_paid >= flt(inst.amount_due) else "Partially Paid"
				frappe.db.set_value("Hire Purchase Installment", inst.name, {
					"amount_paid": new_amount_paid,
					"status": new_status,
				})

		if remaining > 0:
			# Overpayment: no installments left to absorb it — flagged for manual handling
			# (credit note / advance payment) rather than silently discarded.
			frappe.msgprint(
				f"Payment exceeds outstanding balance by {remaining}. "
				f"Excess has not been allocated — please handle as an advance/credit."
			)


def remaining_buckets(inst):
	"""How much of each component on this installment is still unpaid, based on
	prior submitted Payment Allocation Entry rows against it."""
	allocated = frappe.db.sql(
		"""
		select pae.allocation_type, sum(pae.amount_allocated) as total
		from `tabPayment Allocation Entry` pae
		inner join `tabPayment` p on p.name = pae.parent
		where pae.installment = %s and p.docstatus = 1
		group by pae.allocation_type
		""",
		(inst.name,),
		as_dict=True,
	)
	allocated_map = {row.allocation_type: flt(row.total) for row in allocated}

	return {
		"Penalty": max(0, flt(inst.penalty) - allocated_map.get("Penalty", 0)),
		"Fees": max(0, flt(inst.fees) - allocated_map.get("Fees", 0)),
		"Interest": max(0, flt(inst.interest) - allocated_map.get("Interest", 0)),
		"Principal": max(0, flt(inst.principal) - allocated_map.get("Principal", 0)),
	}


def get_allocation_order():
	settings = frappe.get_single("Finance Settings")
	raw = settings.payment_allocation_order or "Penalty, Fees, Interest, Principal"
	return [x.strip() for x in raw.split(",")]
