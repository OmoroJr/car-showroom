import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from frappe import _


class VehiclePayment(Document):
	"""Records a payment against a Vehicle Sale and keeps the sale's
	balance/status in sync.

	Concurrency: validate() takes a row lock (SELECT ... FOR UPDATE) on the
	parent Vehicle Sale before reading its balance/status, and holds it for
	the rest of the transaction. This prevents two payments submitted at
	the same instant from both reading a stale balance and clobbering each
	other's update.
	"""

	def validate(self):
		if not frappe.db.exists("Vehicle Sale", self.sale):
			frappe.throw(_("Vehicle Sale {0} does not exist.").format(self.sale))

		sale_row = frappe.db.sql(
			"select customer, status, balance from `tabVehicle Sale` where name = %s for update",
			(self.sale,),
			as_dict=True,
		)[0]

		if not self.customer:
			self.customer = sale_row.customer

		if sale_row.status != "Awaiting Payment":
			frappe.throw(
				_("Cannot record a payment against Vehicle Sale {0} — its status is '{1}', not 'Awaiting Payment'.")
				.format(self.sale, sale_row.status)
			)

		self.validate_amount(sale_row.balance)
		self.validate_date()
		self.validate_reference()

	def validate_amount(self, outstanding):
		if flt(self.amount) <= 0:
			frappe.throw(_("Payment amount must be greater than zero."))

		if flt(self.amount) > flt(outstanding):
			# Same convention as the Payment doctype on the hire-purchase side:
			# flag it, don't silently block or silently absorb it.
			frappe.msgprint(
				_("Payment of {0} exceeds the outstanding balance of {1} on {2}. "
				  "It will be recorded as-is — please confirm this is intentional "
				  "before proceeding.")
				.format(self.amount, outstanding, self.sale)
			)

	def validate_date(self):
		if self.payment_date and getdate(self.payment_date) > getdate(nowdate()):
			frappe.throw(_("Payment date cannot be in the future."))

	def validate_reference(self):
		if self.payment_method == "Cash":
			return

		if not self.reference_number:
			frappe.throw(
				_("Reference Number is required for {0} payments.").format(self.payment_method)
			)

		duplicate = frappe.db.exists(
			"Vehicle Payment",
			{
				"payment_method": self.payment_method,
				"reference_number": self.reference_number,
				"docstatus": 1,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Reference {0} has already been recorded against payment {1}. "
				  "Check for a duplicate entry before submitting.")
				.format(self.reference_number, duplicate)
			)

	def on_submit(self):
		self.resync_sale(action=_("recorded"))

	def on_cancel(self):
		self.resync_sale(action=_("cancelled"))

	def resync_sale(self, action):
		frappe.db.sql(
			"select name from `tabVehicle Sale` where name = %s for update",
			(self.sale,),
		)
		sale = frappe.get_doc("Vehicle Sale", self.sale)
		previous_status = sale.status
		sale.calculate_totals()
		sale.db_update()

		note = _("Payment {0} of {1} via {2} {3}. Balance now {4}.").format(
			self.name, self.amount, self.payment_method, action, sale.balance
		)
		if sale.status != previous_status:
			note += " " + _("Status moved to {0}.").format(sale.status)
		sale.add_comment("Info", note)
