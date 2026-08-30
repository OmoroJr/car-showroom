import frappe


def get_context(context):
	context.no_cache = 1
	filters = frappe.form_dict

	conditions = {"status": "Available", "is_published": 1}
	if filters.get("make"):
		conditions["make"] = filters.get("make")
	if filters.get("model"):
		conditions["model"] = ["like", f"%{filters.get('model')}%"]
	if filters.get("body_type"):
		conditions["body_type"] = filters.get("body_type")
	if filters.get("fuel_type"):
		conditions["fuel_type"] = filters.get("fuel_type")
	if filters.get("transmission"):
		conditions["transmission"] = filters.get("transmission")
	if filters.get("year"):
		conditions["year"] = filters.get("year")
	if filters.get("min_price") or filters.get("max_price"):
		conditions["asking_price"] = [
			"between",
			[filters.get("min_price") or 0, filters.get("max_price") or 999999999],
		]
	if filters.get("max_mileage"):
		conditions["mileage"] = ["<=", filters.get("max_mileage")]

	vehicles = frappe.get_all(
		"Vehicle",
		filters=conditions,
		fields=["name", "route", "stock_number", "make", "model", "variant", "year",
		        "asking_price", "mileage", "fuel_type", "transmission", "body_type"],
		order_by="modified desc",
		limit_page_length=48,
	)

	for v in vehicles:
		cover = frappe.db.get_value(
			"Vehicle Image", {"parent": v.name, "is_cover": 1}, "image"
		) or frappe.db.get_value("Vehicle Image", {"parent": v.name}, "image")
		v["cover_image"] = cover

	context.vehicles = vehicles
	context.filters = filters
	context.makes = frappe.get_all(
		"Vehicle", filters={"status": "Available", "is_published": 1},
		pluck="make", distinct=True,
	)
	context.title = "Available Vehicles"
