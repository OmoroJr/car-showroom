from frappe import _


def get_data():
	return {
		"fieldname": "vehicle",
		"non_standard_fieldnames": {
			"Vehicle Lead": "interested_vehicle",
		},
		"transactions": [
			{"label": _("Sales Pipeline"), "items": ["Vehicle Lead", "Test Drive", "Vehicle Quotation", "Vehicle Reservation"]},
			{"label": _("Sale"), "items": ["Vehicle Sale"]},
			{"label": _("Inspection & Costs"), "items": ["Vehicle Inspection", "Vehicle Expense"]},
			{"label": _("After-Sales"), "items": ["Warranty", "Service Order"]},
		],
	}
