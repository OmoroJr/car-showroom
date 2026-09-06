frappe.ui.form.on("Vehicle Sale", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.status === "Awaiting Payment") {
			const balance_label = format_currency(frm.doc.balance);
			frm.add_custom_button(__("Record Payment ({0} due)", [balance_label]), () => {
				frappe.new_doc("Vehicle Payment", {
					sale: frm.doc.name,
					customer: frm.doc.customer,
					amount: frm.doc.balance,
					payment_date: frappe.datetime.get_today(),
				});
			}).addClass("btn-primary");
		}
	},
});
