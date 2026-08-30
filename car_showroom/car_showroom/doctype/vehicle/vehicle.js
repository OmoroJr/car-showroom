frappe.ui.form.on("Vehicle", {
	refresh(frm) {
		if (!frm.doc.is_published || !frm.doc.route) return;

		frm.add_custom_button(__("Share on WhatsApp"), () => {
			const url = `${window.location.origin}/${frm.doc.route}`;
			const message =
				`Check out this ${frm.doc.make} ${frm.doc.model} (${frm.doc.year || ""}) — ` +
				`KES ${format_number(frm.doc.asking_price)}. ${url}`;
			car_showroom.share_via_whatsapp(null, message);
		});
	},
});
