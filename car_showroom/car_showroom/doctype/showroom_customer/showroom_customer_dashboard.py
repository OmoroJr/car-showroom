from frappe import _


def get_data():
	return {
		"fieldname": "customer",
		"transactions": [
			{"label": _("Pipeline"), "items": ["Vehicle Lead", "Test Drive", "Vehicle Quotation", "Vehicle Reservation"]},
			{"label": _("Sales & Payments"), "items": ["Vehicle Sale", "Vehicle Payment", "Vehicle Trade In"]},
			{"label": _("Hire Purchase"), "items": ["Credit Assessment", "Hire Purchase Agreement", "Hire Purchase Payment", "Collection Activity"]},
			{"label": _("After-Sales"), "items": ["Service Order"]},
		],
	}
