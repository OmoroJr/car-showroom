# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt
"""Vehicle document expiry tracking (spec section 27).

Scans each Vehicle's Documents table for attachments with an expiry_date
within the configured alert window and notifies the vehicle's branch
manager (falling back to System Managers) via a ToDo + email, once per
document per day.
"""

import frappe
from frappe.utils import add_days, getdate, nowdate


def check_document_expiries():
	settings = frappe.get_single("Hire Purchase Settings")
	alert_days = int(settings.get("document_expiry_alert_days") or 30)
	cutoff = add_days(nowdate(), alert_days)

	expiring_docs = frappe.get_all(
		"Vehicle Document",
		filters={
			"expiry_date": ("between", [nowdate(), cutoff]),
		},
		fields=["name", "parent", "document_type", "expiry_date"],
	)

	for row in expiring_docs:
		if _already_alerted_today(row.name):
			continue
		_notify(row)


def _already_alerted_today(vehicle_document_name):
	return frappe.db.exists(
		"ToDo",
		{
			"reference_type": "Vehicle Document",
			"reference_name": vehicle_document_name,
			"creation": (">=", nowdate()),
		},
	)


def _notify(row):
	vehicle = frappe.get_doc("Vehicle", row.parent)
	recipient_user = None

	if vehicle.branch:
		recipient_user = frappe.db.get_value("Dealership Branch", vehicle.branch, "branch_manager")

	if not recipient_user:
		system_managers = frappe.get_all(
			"Has Role", filters={"role": "System Manager", "parenttype": "User"}, fields=["parent"]
		)
		recipient_user = system_managers[0].parent if system_managers else "Administrator"

	description = (
		f"{row.document_type} for vehicle {vehicle.name} ({vehicle.registration_number or vehicle.stock_number}) "
		f"expires on {row.expiry_date}."
	)

	frappe.get_doc({
		"doctype": "ToDo",
		"allocated_to": recipient_user,
		"reference_type": "Vehicle Document",
		"reference_name": row.name,
		"description": description,
		"priority": "High" if getdate(row.expiry_date) <= getdate(nowdate()) else "Medium",
	}).insert(ignore_permissions=True)

	if recipient_user and recipient_user != "Administrator":
		email = frappe.db.get_value("User", recipient_user, "email")
		if email:
			try:
				frappe.sendmail(recipients=[email], subject="Vehicle Document Expiring Soon", message=description)
			except Exception:
				frappe.log_error(title="Document Expiry Email Failed", message=description)
