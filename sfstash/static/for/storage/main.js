"use strict";

document.addEventListener("DOMContentLoaded", () => {
	document.querySelectorAll("ul.listing.public").forEach(listing => {
		listing.querySelectorAll("li.entry").forEach(entry => {
			const link = Object.assign(document.createElement("button"), {
				type: "button",
				onclick: click => {
					const linkContentElement = click.target.parentElement.querySelector("a.link-content");
					navigator.clipboard.writeText(linkContentElement.href).catch(error => {
						console.error(error);
					});
				},
				classList: "widget link",
			});
			entry.querySelector("a.link-content").style.display = "none";
			entry.querySelector("div.entry-component").appendChild(link);
		});
	});

	document.querySelector("form.upload button[type=submit]").style.display = "none";
});
