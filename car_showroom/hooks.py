from . import __version__ as app_version

app_name = "car_showroom"
app_title = "Car Showroom"
app_publisher = "Wycliffs"
app_description = "Car Dealership & Hire Purchase Management System for Mombasa, Kenya"
app_email = "admin@example.com"
app_license = "MIT"
app_icon = "octicon octicon-car"
app_color = "#1F3A5F"

# Includes in <head>
# ------------------
app_include_js = "/assets/car_showroom/js/car_showroom.js"

# Website / Portal
# ----------------
portal_menu_items = [
	{"title": "My Hire Purchase Agreements", "route": "/my-agreements", "reference_doctype": "Hire Purchase Agreement"},
]

# Document Events
# ----------------
doc_events = {
	"Vehicle": {
		"validate": "car_showroom.car_showroom.doctype.vehicle.vehicle.validate_vehicle",
	},
	"Test Drive": {
		"validate": "car_showroom.car_showroom.doctype.test_drive.test_drive.validate_test_drive",
		"on_update": "car_showroom.car_showroom.doctype.test_drive.test_drive.sync_vehicle_status",
	},
}

# Scheduled Tasks
# ----------------
# Order matters: overdue status must be refreshed before penalties are
# calculated and before overdue reminders are sent.
scheduler_events = {
	"daily": [
		"car_showroom.car_showroom.doctype.vehicle_reservation.vehicle_reservation.auto_expire_reservations",
		"car_showroom.car_showroom.doctype.hire_purchase_installment.hire_purchase_installment.mark_overdue_installments",
		"car_showroom.car_showroom.doctype.penalty.penalty.apply_penalties",
		"car_showroom.car_showroom.reminders.send_payment_reminders",
		"car_showroom.car_showroom.document_alerts.check_document_expiries",
		"car_showroom.car_showroom.doctype.warranty.warranty.expire_warranties",
	],
}

# Installation
# ------------
after_install = "car_showroom.install.after_install"

# Fixtures (populated in later phases: roles, custom fields, workflows)
# fixtures = []
