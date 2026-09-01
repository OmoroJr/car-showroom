// Copyright (c) 2026, Car Showroom and contributors
// For license information, please see license.txt

frappe.query_reports["Collections Aging Summary"] = {
	"filters": [
		{
			"fieldname": "assigned_collector",
			"label": __("Assigned Collector"),
			"fieldtype": "Link",
			"options": "User",
		},
	],
};
