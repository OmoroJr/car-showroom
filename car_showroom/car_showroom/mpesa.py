# Copyright (c) 2026, Wycliffs and contributors
# For license information, please see license.txt
"""
Safaricom M-Pesa Daraja API integration.

Covers:
  - Lipa na M-Pesa Online (STK Push) initiation
  - STK Push callback handling
  - C2B (Paybill/Till) validation + confirmation callbacks
  - Reconciliation of a successful M-Pesa payment against a Hire Purchase
    Agreement's outstanding installments, or a cash-sale Vehicle Sale.

Configure connection details in M-Pesa Settings before use. This module
makes real HTTP calls to Safaricom's Daraja API and must be run on a site
with outbound internet access and a callback URL reachable by Safaricom.
"""

import base64
import json
from datetime import datetime

import frappe
from frappe.utils import flt, now_datetime

try:
	import requests
except ImportError:  # pragma: no cover - requests ships with frappe/bench
	requests = None

SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"


def _base_url(settings):
	return PRODUCTION_BASE_URL if settings.environment == "Production" else SANDBOX_BASE_URL


def _get_settings():
	settings = frappe.get_single("M-Pesa Settings")
	if not settings.enabled:
		frappe.throw(frappe._("M-Pesa integration is disabled. Enable it in M-Pesa Settings first."))
	return settings


def get_access_token(settings=None):
	"""Fetch (and does not cache) an OAuth access token from Daraja."""
	settings = settings or _get_settings()
	url = f"{_base_url(settings)}/oauth/v1/generate?grant_type=client_credentials"

	response = requests.get(
		url,
		auth=(settings.consumer_key, settings.get_password("consumer_secret")),
		timeout=30,
	)
	response.raise_for_status()
	return response.json()["access_token"]


@frappe.whitelist()
def initiate_stk_push(phone_number, amount, account_reference, description="Vehicle Payment"):
	"""Trigger an STK Push (Lipa na M-Pesa Online) prompt on the customer's phone.

	account_reference should be the Hire Purchase Agreement name (for an
	installment payment) or the Vehicle Sale name (for a cash-sale payment) -
	it is used at callback time to know what to reconcile the payment against.
	"""
	settings = _get_settings()
	if not settings.callback_base_url:
		frappe.throw(frappe._("Set Callback Base URL in M-Pesa Settings before initiating STK Push."))

	access_token = get_access_token(settings)
	timestamp = now_datetime().strftime("%Y%m%d%H%M%S")
	password = base64.b64encode(
		f"{settings.business_shortcode}{settings.get_password('passkey')}{timestamp}".encode()
	).decode()

	payload = {
		"BusinessShortCode": settings.business_shortcode,
		"Password": password,
		"Timestamp": timestamp,
		"TransactionType": settings.transaction_type or "CustomerPayBillOnline",
		"Amount": int(flt(amount)),
		"PartyA": phone_number,
		"PartyB": settings.business_shortcode,
		"PhoneNumber": phone_number,
		"CallBackURL": f"{settings.callback_base_url.rstrip('/')}/api/method/car_showroom.car_showroom.mpesa.stk_callback",
		"AccountReference": f"{settings.account_reference_prefix}-{account_reference}"[:12],
		"TransactionDesc": description,
	}

	response = requests.post(
		f"{_base_url(settings)}/mpesa/stkpush/v1/processrequest",
		json=payload,
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=30,
	)
	data = response.json()

	txn = frappe.get_doc({
		"doctype": "M-Pesa Transaction",
		"transaction_type": "STK Push",
		"phone_number": phone_number,
		"amount": amount,
		"account_reference": account_reference,
		"transaction_date": now_datetime(),
		"merchant_request_id": data.get("MerchantRequestID"),
		"checkout_request_id": data.get("CheckoutRequestID"),
		"result_code": data.get("ResponseCode"),
		"result_desc": data.get("ResponseDescription") or data.get("errorMessage"),
		"raw_callback_payload": json.dumps(data),
		"status": "Pending" if data.get("ResponseCode") == "0" else "Failed",
	})
	txn.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"transaction": txn.name, "daraja_response": data}


@frappe.whitelist(allow_guest=True)
def stk_callback():
	"""Safaricom posts here after the customer completes (or cancels/fails)
	the STK Push prompt. Must be registered as CallBackURL and reachable
	without authentication."""
	payload = json.loads(frappe.request.data or "{}")
	frappe.log_error(title="M-Pesa STK Callback", message=json.dumps(payload))

	stk_callback_data = (
		payload.get("Body", {}).get("stkCallback", {})
	)
	checkout_request_id = stk_callback_data.get("CheckoutRequestID")
	result_code = stk_callback_data.get("ResultCode")
	result_desc = stk_callback_data.get("ResultDesc")

	txn_name = frappe.db.get_value(
		"M-Pesa Transaction", {"checkout_request_id": checkout_request_id}, "name"
	)
	if not txn_name:
		frappe.log_error(
			title="M-Pesa Callback: Unmatched Transaction",
			message=f"No M-Pesa Transaction found for CheckoutRequestID {checkout_request_id}",
		)
		return {"ResultCode": 0, "ResultDesc": "Accepted"}

	txn = frappe.get_doc("M-Pesa Transaction", txn_name)
	txn.result_code = result_code
	txn.result_desc = result_desc
	txn.raw_callback_payload = json.dumps(payload)

	if str(result_code) == "0":
		metadata = {
			item["Name"]: item.get("Value")
			for item in stk_callback_data.get("CallbackMetadata", {}).get("Item", [])
		}
		txn.mpesa_receipt_number = metadata.get("MpesaReceiptNumber")
		txn.amount = metadata.get("Amount") or txn.amount
		txn.status = "Success"
		txn.save(ignore_permissions=True)
		frappe.db.commit()
		reconcile_transaction(txn.name)
	else:
		txn.status = "Cancelled" if str(result_code) == "1032" else "Failed"
		txn.save(ignore_permissions=True)
		frappe.db.commit()

	# Safaricom expects this exact acknowledgement shape.
	return {"ResultCode": 0, "ResultDesc": "Accepted"}


@frappe.whitelist(allow_guest=True)
def c2b_validation():
	"""Optional: accept/reject a C2B payment before it completes. Returning
	success accepts all incoming payments; add business checks here if
	Safaricom validation is enabled on your shortcode."""
	return {"ResultCode": 0, "ResultDesc": "Accepted"}


@frappe.whitelist(allow_guest=True)
def c2b_confirmation():
	"""Safaricom posts here once a Paybill/Till payment is confirmed."""
	payload = json.loads(frappe.request.data or "{}")
	frappe.log_error(title="M-Pesa C2B Confirmation", message=json.dumps(payload))

	txn = frappe.get_doc({
		"doctype": "M-Pesa Transaction",
		"transaction_type": "C2B Paybill",
		"phone_number": payload.get("MSISDN"),
		"amount": payload.get("TransAmount"),
		"account_reference": payload.get("BillRefNumber"),
		"transaction_date": now_datetime(),
		"mpesa_receipt_number": payload.get("TransID"),
		"raw_callback_payload": json.dumps(payload),
		"status": "Success",
	})
	txn.insert(ignore_permissions=True)
	frappe.db.commit()
	reconcile_transaction(txn.name)

	return {"ResultCode": 0, "ResultDesc": "Accepted"}


def reconcile_transaction(mpesa_transaction_name):
	"""Match a successful M-Pesa Transaction to the right agreement/sale and
	create + submit the corresponding payment record, allocating it
	automatically."""
	txn = frappe.get_doc("M-Pesa Transaction", mpesa_transaction_name)
	if txn.status != "Success" or not txn.account_reference:
		return

	reference = txn.account_reference

	if frappe.db.exists("Hire Purchase Agreement", reference):
		payment = frappe.get_doc({
			"doctype": "Hire Purchase Payment",
			"hire_purchase_agreement": reference,
			"payment_date": frappe.utils.nowdate(),
			"amount": txn.amount,
			"payment_method": "M-Pesa",
			"reference_number": txn.mpesa_receipt_number,
			"mpesa_transaction": txn.name,
		})
		payment.insert(ignore_permissions=True)
		payment.submit()
		txn.db_set("linked_hire_purchase_payment", payment.name)
		return

	if frappe.db.exists("Vehicle Sale", reference):
		payment = frappe.get_doc({
			"doctype": "Vehicle Payment",
			"sale": reference,
			"payment_date": frappe.utils.nowdate(),
			"amount": txn.amount,
			"payment_method": "M-Pesa",
			"reference_number": txn.mpesa_receipt_number,
		})
		payment.insert(ignore_permissions=True)
		payment.submit()
		txn.db_set("linked_vehicle_payment", payment.name)
		return

	frappe.log_error(
		title="M-Pesa Reconciliation: No Match",
		message=(
			f"M-Pesa Transaction {txn.name} has account reference '{reference}' "
			"which does not match any Hire Purchase Agreement or Vehicle Sale. "
			"Reconcile it manually."
		),
	)
