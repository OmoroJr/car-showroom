frappe.ui.form.on("Vehicle Quotation", {
	refresh(frm) {
		if (!frm.doc.customer) return;

		frm.add_custom_button(__("Send via WhatsApp"), () => {
			frappe.db.get_value("Showroom Customer", frm.doc.customer, "phone").then((r) => {
				const phone = r.message.phone;
				const vehicle_label = frm.doc.vehicle || "";
				const message =
					`Hello, here is your quotation ${frm.doc.name} for ${vehicle_label}: ` +
					`Total payable KES ${format_number(frm.doc.total_payable)}, ` +
					`balance KES ${format_number(frm.doc.balance)}. Valid till ${frm.doc.valid_till || "-"}.`;
				car_showroom.share_via_whatsapp(phone, message);
			});
		});
	},
});
