// Copyright (c) 2026, Car Showroom and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Funnel Conversion"] = {
	"filters": [
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
		},
		{
			"fieldname": "assigned_salesperson",
			"label": __("Salesperson"),
			"fieldtype": "Link",
			"options": "User",
		},
	],
};
