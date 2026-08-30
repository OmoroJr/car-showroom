# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt
"""Guest-callable endpoints backing the public vehicle marketplace pages.

Anonymous visitors can request financing info or a test drive, and preview
a hire-purchase estimate — all captured as a Vehicle Lead for staff to
follow up on, never as an auto-confirmed booking.
"""

import frappe


@frappe.whitelist(allow_guest=True)
def request_financing(vehicle, full_name, phone, email=None, message=None):
	return _create_or_update_lead(
		vehicle=vehicle,
		full_name=full_name,
		phone=phone,
		email=email,
		status="Financing",
		activity_type="Other",
		notes=message or "Requested financing information from the website.",
	)


@frappe.whitelist(allow_guest=True)
def book_test_drive(vehicle, full_name, phone, preferred_date=None, email=None):
	notes = "Requested a test drive from the website."
	if preferred_date:
		notes += f" Preferred date: {preferred_date}."

	return _create_or_update_lead(
		vehicle=vehicle,
		full_name=full_name,
		phone=phone,
		email=email,
		status="Test Drive",
		activity_type="Test Drive",
		notes=notes,
	)


def _create_or_update_lead(vehicle, full_name, phone, email, status, activity_type, notes):
	if not (vehicle and full_name and phone):
		frappe.throw(frappe._("Vehicle, name, and phone are required."))

	if not frappe.db.exists("Vehicle", vehicle):
		frappe.throw(frappe._("That vehicle could not be found."))

	branch = frappe.db.get_value("Vehicle", vehicle, "branch")

	lead = frappe.get_doc({
		"doctype": "Vehicle Lead",
		"lead_name": full_name,
		"phone": phone,
		"email": email,
		"source": "Website",
		"interested_vehicle": vehicle,
		"branch": branch,
		"status": status,
	})
	lead.insert(ignore_permissions=True)

	frappe.get_doc({
		"doctype": "Vehicle Lead Activity",
		"lead": lead.name,
		"activity_type": activity_type,
		"notes": notes,
	}).insert(ignore_permissions=True)

	return {"lead": lead.name, "message": "Thank you — our team will contact you shortly."}


@frappe.whitelist(allow_guest=True)
def calculate_hp_preview(cash_price, deposit, interest_rate, period_months,
                          frequency="Monthly", processing_fee=0, insurance=0,
                          other_charges=0, method=None):
	"""Thin passthrough to the Hire Purchase Agreement calculator, so the
	public 'Calculate Hire Purchase' button doesn't need desk access. Takes
	a period in months + a frequency and derives the installment count."""
	from car_showroom.car_showroom.doctype.hire_purchase_agreement.hire_purchase_agreement import (
		calculate_schedule_preview,
	)

	period_months = frappe.utils.flt(period_months)
	installments_per_month = {"Weekly": 52 / 12, "Bi-weekly": 26 / 12, "Monthly": 1}
	number_of_installments = max(1, round(period_months * installments_per_month.get(frequency, 1)))

	if not method:
		method = frappe.get_single("Hire Purchase Settings").default_interest_method or "Flat Rate"

	return calculate_schedule_preview(
		cash_price=cash_price,
		deposit=deposit,
		interest_rate=interest_rate,
		financing_period_months=period_months,
		number_of_installments=number_of_installments,
		frequency=frequency,
		method=method,
		processing_fee=processing_fee,
		insurance=insurance,
		other_charges=other_charges,
	)


@frappe.whitelist()
def pay_installment_via_mpesa(agreement, phone_number, amount):
	"""Customer-portal 'Pay Now' action. Requires login, and only lets a
	customer trigger an STK Push against their own agreement."""
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Please log in first."), frappe.PermissionError)

	customers = frappe.get_all(
		"Showroom Customer", filters={"portal_user": frappe.session.user}, pluck="name"
	)
	agreement_customer = frappe.db.get_value("Hire Purchase Agreement", agreement, "customer")

	if not agreement_customer or agreement_customer not in customers:
		frappe.throw(frappe._("You do not have access to this agreement."), frappe.PermissionError)

	from car_showroom.car_showroom.mpesa import initiate_stk_push

	result = initiate_stk_push(
		phone_number=phone_number,
		amount=amount,
		account_reference=agreement,
		description="Hire Purchase Installment",
	)
	return {"message": "Payment request sent — check your phone to complete it.", "result": result}
