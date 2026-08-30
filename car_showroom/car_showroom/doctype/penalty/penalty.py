# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Penalty(Document):

	def validate(self):
		if self.status != "Waived":
			self.calculate_amount()

	def calculate_amount(self):
		settings = frappe.get_single("Hire Purchase Settings")
		installment = frappe.get_doc("Hire Purchase Installment", self.installment)
		base = flt(installment.balance) or flt(installment.total)

		rate = flt(self.penalty_rate)
		penalty_type = self.penalty_type

		if penalty_type == "Fixed":
			amount = rate
		elif penalty_type == "Percentage":
			amount = base * rate / 100
		elif penalty_type == "Daily":
			amount = base * (rate / 100) * flt(self.days_overdue)
		elif penalty_type == "Monthly":
			months_overdue = max(1, flt(self.days_overdue) / 30)
			amount = base * (rate / 100) * months_overdue
		else:
			amount = 0

		max_penalty = flt(settings.get("max_penalty_amount"))
		if max_penalty and amount > max_penalty:
			amount = max_penalty

		self.calculated_amount = round(amount, 2)

	@frappe.whitelist()
	def waive(self, reason=None):
		self.status = "Waived"
		self.waived_by = frappe.session.user
		self.waiver_reason = reason
		self.save()


def apply_penalties():
	"""Daily scheduled job: create/update Penalty records for every overdue
	installment, using the grace period and rates configured in
	Hire Purchase Settings (never hard-coded)."""
	settings = frappe.get_single("Hire Purchase Settings")
	grace_period = int(settings.get("grace_period_days") or 0)
	penalty_type = settings.get("default_penalty_type")
	penalty_rate = flt(settings.get("default_penalty_rate"))

	if not penalty_type or not penalty_rate:
		return  # penalties not configured; nothing to do

	overdue_installments = frappe.get_all(
		"Hire Purchase Installment",
		filters={"status": "Overdue"},
		fields=["name", "hire_purchase_agreement", "due_date"],
	)

	today = frappe.utils.getdate(frappe.utils.nowdate())

	for row in overdue_installments:
		days_overdue = (today - frappe.utils.getdate(row.due_date)).days
		if days_overdue <= grace_period:
			continue

		existing = frappe.db.get_value(
			"Penalty", {"installment": row.name, "status": ("!=", "Waived")}, "name"
		)
		if existing:
			penalty = frappe.get_doc("Penalty", existing)
			penalty.days_overdue = days_overdue
			penalty.penalty_type = penalty_type
			penalty.penalty_rate = penalty_rate
			penalty.status = "Applied"
			penalty.save(ignore_permissions=True)
		else:
			frappe.get_doc({
				"doctype": "Penalty",
				"hire_purchase_agreement": row.hire_purchase_agreement,
				"installment": row.name,
				"days_overdue": days_overdue,
				"penalty_type": penalty_type,
				"penalty_rate": penalty_rate,
				"status": "Applied",
			}).insert(ignore_permissions=True)
