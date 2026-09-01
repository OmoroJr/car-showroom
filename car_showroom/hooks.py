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

doc_events = {
	"Vehicle": {
		"before_save": "car_showroom.car_showroom.doctype.vehicle.vehicle.before_save",
		"on_update": "car_showroom.car_showroom.doctype.vehicle.vehicle.on_update",
	}
}

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
# fixtures = []

# Testing
# -------
# before_tests = "car_showroom.install.before_tests"
