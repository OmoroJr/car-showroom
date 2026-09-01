# Copyright (c) 2026, Car Showroom and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

# Maps a completed approval stage decision to the Credit Application's next status.
NEXT_STATUS_ON_APPROVE = {
	"Document Verification": "Credit Assessment",
	"Credit Officer Review": "Finance Manager Review",
	"Finance Manager Review": "Management Approval",
	"Management Approval": "Approved",
}


class CreditApproval(Document):
	def before_insert(self):
		self.approver = frappe.session.user
		self.decision_date = now_datetime()

	def after_insert(self):
		if not self.credit_application:
			return

		if self.decision == "Rejected":
			frappe.db.set_value("Credit Application", self.credit_application, "status", "Rejected")
		elif self.decision == "Returned for Correction":
			frappe.db.set_value(
				"Credit Application", self.credit_application, "status", "Document Verification"
			)
		elif self.decision == "Approved":
			next_status = NEXT_STATUS_ON_APPROVE.get(self.approval_stage)
			if next_status:
				frappe.db.set_value("Credit Application", self.credit_application, "status", next_status)
