frappe.provide("car_showroom");

/**
 * Open a WhatsApp "click to chat" link pre-filled with a message.
 * If a phone number is given, the chat opens directly with that contact;
 * otherwise it opens WhatsApp's contact picker with the message ready to send.
 */
car_showroom.share_via_whatsapp = function (phone, message) {
	let digits = (phone || "").replace(/[^\d]/g, "");
	// Normalize common Kenyan local formats (07xx / 01xx) to +254 international.
	if (digits.startsWith("0")) {
		digits = "254" + digits.substring(1);
	}
	const base = digits ? `https://wa.me/${digits}` : "https://wa.me/";
	window.open(`${base}?text=${encodeURIComponent(message)}`, "_blank");
};
