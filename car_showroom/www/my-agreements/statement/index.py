import frappe
from frappe import _


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view your statement."), frappe.PermissionError)

	agreement_name = frappe.form_dict.get("agreement")
	if not agreement_name:
		frappe.throw(_("No agreement specified."))

	agreement = frappe.get_doc("Hire Purchase Agreement", agreement_name)
	customers = frappe.get_all(
		"Showroom Customer", filters={"portal_user": frappe.session.user}, pluck="name"
	)
	if agreement.customer not in customers:
		frappe.throw(_("You do not have access to this statement."), frappe.PermissionError)

	context.agreement = agreement
	context.installments = frappe.get_all(
		"Hire Purchase Installment",
		filters={"hire_purchase_agreement": agreement_name},
		fields=["due_date", "principal", "interest", "fees", "total", "amount_paid", "balance", "status"],
		order_by="due_date asc",
	)
	context.payments = frappe.get_all(
		"Hire Purchase Payment",
		filters={"hire_purchase_agreement": agreement_name, "docstatus": 1},
		fields=["payment_date", "amount", "payment_method", "receipt_number"],
		order_by="payment_date desc",
	)
	context.title = f"Statement — {agreement_name}"
