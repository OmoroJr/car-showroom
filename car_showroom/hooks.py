from . import __version__ as app_version

app_name = "car_showroom"
app_title = "Car Showroom"
app_publisher = "Mombasa Auto Group"
app_description = "Enterprise Car Dealership, Showroom, Vehicle Sales & Hire Purchase Management ERP"
app_email = "admin@example.com"
app_license = "MIT"

# Includes in <head>
# ------------------
# app_include_css = "/assets/car_showroom/css/car_showroom.css"
# app_include_js = "/assets/car_showroom/js/car_showroom.js"

# include js, css files in header of web template
# web_include_css = "/assets/car_showroom/css/car_showroom.css"
# web_include_js = "/assets/car_showroom/js/car_showroom.js"

# Home Pages
# ----------
# application home page (will override Website Settings)
# home_page = "login"

# Generators
# ----------
# automatically create page for each record of this doctype
# website_generators = ["Vehicle"]

# Installation
# ------------
# before_install = "car_showroom.install.before_install"
# after_install = "car_showroom.install.after_install"

# Document Events
# ---------------
# Hook on document methods and events
# Note: Vehicle's before_save/on_update are already implemented as controller
# methods on the Vehicle class (car_showroom/doctype/vehicle/vehicle.py) and
# fire automatically — they do not need (and must not have) doc_events entries
# here, since those are module-level functions, not class methods, and would
# fail to resolve.
# doc_events = {}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"car_showroom.car_showroom.doctype.vehicle.vehicle.update_days_in_stock",
		"car_showroom.car_showroom.doctype.reservation.reservation.expire_due_reservations",
		"car_showroom.car_showroom.doctype.reservation.reservation.alert_expiring_reservations",
		"car_showroom.car_showroom.doctype.hire_purchase_installment.hire_purchase_installment.update_overdue_and_penalties",
		"car_showroom.car_showroom.doctype.collection_case.collection_case.sync_collection_cases",
	],
}

# Fixtures
# --------
# Ships the custom roles referenced in doctype permissions (Sales User,
# Sales Manager, Finance Officer, Finance Manager, Cashier / Accounts,
# Collections Officer, Collections Manager) so `bench migrate` creates them
# automatically. Without this, the permission rows on doctypes reference
# roles that don't exist on the site and nobody can be assigned to them.
fixtures = [
	{
		"doctype": "Role",
		"filters": [
			["role_name", "in", [
				"Sales User", "Sales Manager",
				"Finance Officer", "Finance Manager",
				"Cashier / Accounts",
				"Collections Officer", "Collections Manager",
			]]
		]
	}
]

# Testing
# -------
# before_tests = "car_showroom.install.before_tests"
