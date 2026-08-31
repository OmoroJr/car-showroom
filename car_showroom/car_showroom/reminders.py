# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt
"""
Payment reminders across Email, SMS (Africa's Talking-style gateway), and
WhatsApp (Twilio/Meta Cloud API-style gateway). Channels, gateway
credentials, and message templates are all configured in Notification
Settings — nothing here is hard-coded.

Run daily via the scheduler (see hooks.py). Idempotent: an installment gets
at most one reminder per scenario per day (checked via Payment Reminder Log).
"""

import json

import frappe
from frappe.utils import flt, getdate, nowdate

try:
	import requests
except ImportError:  # pragma: no cover
	requests = None

SCENARIOS = [
	# (label, day_offset_from_due_date, template_fieldname)
	("7 Days Before", -7, "template_upcoming"),
	("Due Today", 0, "template_due_today"),
	("3 Days Overdue", 3, "template_overdue_3"),
	("30+ Days Overdue", 30, "template_overdue_30"),
]


def send_payment_reminders():
	"""Daily scheduled job: find installments matching each reminder
	scenario and send a reminder on every enabled channel, once per day."""
	settings = frappe.get_single("Car Showroom Notification Settings")
	today = getdate(nowdate())

	for scenario_label, offset, template_field in SCENARIOS:
		target_date = frappe.utils.add_days(today, offset)

		installments = frappe.get_all(
			"Hire Purchase Installment",
			filters={
				"due_date": target_date,
				"status": ("in", ["Pending", "Partially Paid", "Overdue"]),
			},
			fields=["name", "hire_purchase_agreement", "balance", "due_date"],
		)

		for row in installments:
			if _already_sent_today(row.name, scenario_label):
				continue
			_send_reminder_for_installment(row, scenario_label, template_field, settings)


def _already_sent_today(installment, scenario_label):
	return frappe.db.exists(
		"Payment Reminder Log",
		{
			"hire_purchase_installment": installment,
			"scenario": scenario_label,
			"sent_on": (">=", nowdate()),
		},
	)


def _send_reminder_for_installment(installment_row, scenario_label, template_field, settings):
	agreement = frappe.get_doc("Hire Purchase Agreement", installment_row.hire_purchase_agreement)
	customer = frappe.get_doc("Showroom Customer", agreement.customer)
	company = frappe.defaults.get_global_default("company") or "Car Showroom"

	template = settings.get(template_field) or ""
	message = template.format(
		customer_name=customer.full_name,
		amount=flt(installment_row.balance),
		due_date=frappe.utils.format_date(installment_row.due_date),
		agreement=agreement.name,
		vehicle=agreement.vehicle,
		company=company,
	)

	if settings.enable_email and customer.email:
		_send_and_log(installment_row.name, scenario_label, "Email", customer.email,
		              message, lambda: send_email(customer.email, "Payment Reminder", message))

	if settings.enable_sms and customer.phone:
		_send_and_log(installment_row.name, scenario_label, "SMS", customer.phone,
		              message, lambda: send_sms(customer.phone, message, settings))

	if settings.enable_whatsapp and customer.phone:
		_send_and_log(installment_row.name, scenario_label, "WhatsApp", customer.phone,
		              message, lambda: send_whatsapp(customer.phone, message, settings))


def _send_and_log(installment, scenario_label, channel, recipient, message, send_fn):
	try:
		send_fn()
		status, error = "Sent", None
	except Exception as e:
		status, error = "Failed", str(e)
		frappe.log_error(title=f"Payment Reminder Failed ({channel})", message=str(e))

	frappe.get_doc({
		"doctype": "Payment Reminder Log",
		"hire_purchase_installment": installment,
		"scenario": scenario_label,
		"channel": channel,
		"recipient": recipient,
		"message": message,
		"status": status,
		"error": error,
	}).insert(ignore_permissions=True)


def send_email(email, subject, message):
	frappe.sendmail(recipients=[email], subject=subject, message=message)


def send_sms(phone_number, message, settings=None):
	"""Generic SMS gateway call, defaulting to Africa's Talking's HTTP API.
	Swap the request shape here if you use a different provider."""
	settings = settings or frappe.get_single("Car Showroom Notification Settings")

	if settings.sms_provider == "Africa's Talking":
		response = requests.post(
			settings.sms_api_url or "https://api.africastalking.com/version1/messaging",
			data={
				"username": settings.sms_username,
				"to": phone_number,
				"message": message,
				"from": settings.sms_sender_id,
			},
			headers={
				"apiKey": settings.get_password("sms_api_key"),
				"Content-Type": "application/x-www-form-urlencoded",
				"Accept": "application/json",
			},
			timeout=30,
		)
		response.raise_for_status()
		return response.json()

	frappe.throw(frappe._("Configure a supported SMS provider, or implement send_sms() for your custom gateway."))


def send_whatsapp(phone_number, message, settings=None):
	"""Generic WhatsApp gateway call. Twilio and Meta Cloud API have
	different request shapes; both are sketched here — keep only the one
	you use."""
	settings = settings or frappe.get_single("Car Showroom Notification Settings")

	if settings.whatsapp_provider == "Twilio":
		response = requests.post(
			settings.whatsapp_api_url
			or f"https://api.twilio.com/2010-04-01/Accounts/{settings.whatsapp_account_sid}/Messages.json",
			data={
				"From": f"whatsapp:{settings.whatsapp_from_number}",
				"To": f"whatsapp:{phone_number}",
				"Body": message,
			},
			auth=(settings.whatsapp_account_sid, settings.get_password("whatsapp_auth_token")),
			timeout=30,
		)
		response.raise_for_status()
		return response.json()

	if settings.whatsapp_provider == "Meta Cloud API":
		response = requests.post(
			settings.whatsapp_api_url,
			headers={
				"Authorization": f"Bearer {settings.get_password('whatsapp_auth_token')}",
				"Content-Type": "application/json",
			},
			data=json.dumps({
				"messaging_product": "whatsapp",
				"to": phone_number,
				"type": "text",
				"text": {"body": message},
			}),
			timeout=30,
		)
		response.raise_for_status()
		return response.json()

	frappe.throw(frappe._("Configure a supported WhatsApp provider, or implement send_whatsapp() for your custom gateway."))
