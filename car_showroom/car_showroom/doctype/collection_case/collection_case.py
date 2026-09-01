# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff, flt

# Only ever escalate a case forward automatically; a collector who has already
# moved a case on manually (e.g. into "Promise to Pay") should not be bumped
# backwards by the nightly sync.
STATUS_RANK = {
	"Open": 1,
	"In Progress": 1,
	"Promise to Pay": 1,
	"Escalated": 2,
	"Legal Notice": 2,
	"Repossession Recommended": 3,
	"Resolved": 4,
	"Closed": 4,
}


class CollectionCase(Document):
	def validate(self):
		if self.hire_purchase_agreement:
			agreement = frappe.db.get_value(
				"Hire Purchase Agreement", self.hire_purchase_agreement, ["customer", "vehicle"], as_dict=True
			)
			if agreement:
				self.customer = agreement.customer
				self.vehicle = agreement.vehicle

		if self.status in ("Resolved", "Closed") and not self.closed_date:
			self.closed_date = nowdate()


def sync_collection_cases():
	"""Scheduled daily job: open, refresh and escalate Collection Cases for every
	Hire Purchase Agreement that has at least one Overdue installment."""
	settings = frappe.get_single("Finance Settings")
	trigger_days = settings.collection_trigger_days or 7
	escalate_days = settings.collection_escalate_days or 30
	repo_days = settings.repossession_recommend_days or 60

	rows = frappe.db.sql(
		"""
		select hpa.name as agreement, hpa.customer, hpa.vehicle,
			min(hpi.due_date) as oldest_due_date,
			sum(hpi.amount_due - hpi.amount_paid) as overdue_amount
		from `tabHire Purchase Installment` hpi
		inner join `tabHire Purchase Agreement` hpa on hpa.name = hpi.hire_purchase_agreement
		where hpi.status = 'Overdue' and hpa.status = 'Active'
		group by hpa.name
		""",
		as_dict=True,
	)

	today = nowdate()
	for row in rows:
		days_overdue = date_diff(today, row.oldest_due_date)
		if days_overdue < trigger_days:
			continue

		total_outstanding = frappe.db.get_value(
			"Hire Purchase Agreement", row.agreement, "outstanding_balance"
		) or 0

		if days_overdue >= repo_days:
			priority, suggested_status = "Critical", "Repossession Recommended"
		elif days_overdue >= escalate_days:
			priority, suggested_status = "High", "Escalated"
		else:
			priority, suggested_status = "Medium", "Open"

		existing = frappe.db.exists(
			"Collection Case",
			{"hire_purchase_agreement": row.agreement, "status": ["not in", ["Resolved", "Closed"]]},
		)

		if existing:
			case = frappe.get_doc("Collection Case", existing)
			case.days_overdue = days_overdue
			case.overdue_amount = row.overdue_amount
			case.total_outstanding = total_outstanding
			case.oldest_due_date = row.oldest_due_date
			case.priority = priority
			if STATUS_RANK.get(suggested_status, 0) > STATUS_RANK.get(case.status, 0):
				case.status = suggested_status
			case.save(ignore_permissions=True)
		else:
			frappe.get_doc({
				"doctype": "Collection Case",
				"hire_purchase_agreement": row.agreement,
				"customer": row.customer,
				"vehicle": row.vehicle,
				"days_overdue": days_overdue,
				"overdue_amount": row.overdue_amount,
				"total_outstanding": total_outstanding,
				"oldest_due_date": row.oldest_due_date,
				"priority": priority,
				"status": suggested_status,
			}).insert(ignore_permissions=True)

	frappe.db.commit()


def close_case_for_agreement(agreement_name, resolution):
	"""Helper used by Loan Restructure Request / Settlement Quotation / Repossession
	Order on_submit to close out any open Collection Case for the agreement."""
	open_case = frappe.db.exists(
		"Collection Case",
		{"hire_purchase_agreement": agreement_name, "status": ["not in", ["Resolved", "Closed"]]},
	)
	if not open_case:
		return
	frappe.db.set_value(
		"Collection Case", open_case,
		{"status": "Resolved", "resolution": resolution, "closed_date": nowdate()},
	)
