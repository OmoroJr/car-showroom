// Copyright (c) 2026, Car Showroom and contributors
// For license information, please see license.txt

frappe.query_reports["Overdue Installments"] = {
	"filters": [
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "min_days_overdue",
			"label": __("Minimum Days Overdue"),
			"fieldtype": "Int",
		},
	],
};
