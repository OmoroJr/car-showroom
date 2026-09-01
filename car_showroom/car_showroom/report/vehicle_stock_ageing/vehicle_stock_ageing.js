// Copyright (c) 2026, Car Showroom and contributors
// For license information, please see license.txt

frappe.query_reports["Vehicle Stock Ageing"] = {
	"filters": [
		{
			"fieldname": "min_days_in_stock",
			"label": __("Minimum Days in Stock"),
			"fieldtype": "Int",
		},
	],
};
