import frappe

REQUIRED_ROLES = [
	"Managing Director",
	"Director",
	"General Manager",
	"Branch Manager",
	"Sales Manager",
	"Salesperson",
	"Credit Officer",
	"Finance Manager",
	"Accountant",
	"Cashier",
	"Collections Officer",
	"Inventory Manager",
	"Vehicle Inspector",
	"Service Manager",
	"Marketing Officer",
	"Auditor",
]


def after_install():
	create_roles()
	seed_hire_purchase_settings()


def create_roles():
	for role_name in REQUIRED_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}).insert(ignore_permissions=True)


def seed_hire_purchase_settings():
	"""Seed a usable default so Hire Purchase Agreements can be submitted for
	approval immediately after install. Administrators should review and
	adjust these limits for their own dealership."""
	settings = frappe.get_single("Hire Purchase Settings")
	if settings.approval_limits:
		return  # already configured, don't overwrite

	settings.default_interest_method = settings.default_interest_method or "Flat Rate"
	settings.grace_period_days = settings.grace_period_days or 0
	settings.default_penalty_type = settings.default_penalty_type or "Percentage"
	settings.default_penalty_rate = settings.default_penalty_rate or 5
	settings.max_penalty_amount = settings.max_penalty_amount or 0
	settings.append("approval_limits", {"up_to_amount": 500000, "approver_role": "Finance Manager"})
	settings.append("approval_limits", {"up_to_amount": 1500000, "approver_role": "General Manager"})
	settings.append("approval_limits", {"up_to_amount": 0, "approver_role": "Director"})
	settings.save(ignore_permissions=True)
