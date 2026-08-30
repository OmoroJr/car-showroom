import frappe
from frappe import _


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view your hire purchase agreements."), frappe.PermissionError)

	customers = frappe.get_all(
		"Showroom Customer", filters={"portal_user": frappe.session.user}, pluck="name"
	)

	agreements = []
	if customers:
		agreements = frappe.get_all(
			"Hire Purchase Agreement",
			filters={"customer": ("in", customers)},
			fields=["name", "vehicle", "status", "amount_financed", "total_amount_payable",
			        "installment_amount", "number_of_installments"],
		)

		for a in agreements:
			installments = frappe.get_all(
				"Hire Purchase Installment",
				filters={"hire_purchase_agreement": a.name},
				fields=["name", "due_date", "total", "amount_paid", "balance", "status"],
				order_by="due_date asc",
			)
			a["installments"] = installments
			a["total_paid"] = sum(frappe.utils.flt(i.amount_paid) for i in installments)
			a["progress_percent"] = (
				round((a["total_paid"] / a.total_amount_payable) * 100, 1)
				if a.total_amount_payable else 0
			)
			next_due = next((i for i in installments if i.status in ("Pending", "Partially Paid", "Overdue")), None)
			a["next_due"] = next_due

	context.agreements = agreements
	context.has_account = bool(customers)
	context.title = "My Hire Purchase Agreements"
