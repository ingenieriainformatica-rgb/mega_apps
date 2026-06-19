/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const PHOTO_CATEGORIES = [
    ["externa", "Externa"],
    ["interna", "Interna"],
    ["dano_existente", "Daño existente"],
    ["pertenencias", "Pertenencias"],
    ["documentos", "Documentos"],
    ["otro", "Otro"],
];

publicWidget.registry.WorkshopReceptionPhotos = publicWidget.Widget.extend({
    selector: ".js-workshop-reception-form",
    events: {
        "change .js-workshop-customer-type": "_onCustomerTypeChanged",
        "change .js-workshop-photo-input": "_onFilesSelected",
        "change .js-workshop-photo-category": "_onCategoryChanged",
        "click .js-workshop-photo-remove": "_onRemovePhoto",
    },

    start() {
        this.photos = [];
        this.input = this.el.querySelector(".js-workshop-photo-input");
        this.preview = this.el.querySelector(".js-workshop-photo-preview");
        this.counter = this.el.querySelector(".js-workshop-photo-count");
        this._updateCustomerType();
        return this._super(...arguments);
    },

    _onCustomerTypeChanged() {
        this._updateCustomerType();
    },

    _updateCustomerType() {
        const customerType = this.el.querySelector("[name='customer_type']:checked")?.value || "particular";
        const isRenting = customerType === "renting";
        const particularFields = this.el.querySelector(".js-workshop-particular-fields");
        const rentingFields = this.el.querySelector(".js-workshop-renting-fields");

        particularFields.classList.toggle("d-none", isRenting);
        rentingFields.classList.toggle("d-none", !isRenting);

        for (const input of particularFields.querySelectorAll("input, select, textarea")) {
            input.disabled = isRenting;
        }
        for (const input of rentingFields.querySelectorAll("input, select, textarea")) {
            input.disabled = !isRenting;
        }
        for (const input of particularFields.querySelectorAll(".js-workshop-particular-required")) {
            input.required = !isRenting;
        }

        const deliveredName = this.el.querySelector("[name='delivered_by_name']");
        const deliveredPhone = this.el.querySelector("[name='delivered_by_phone']");
        deliveredName.required = isRenting;
        deliveredPhone.required = isRenting;
    },

    _onFilesSelected(event) {
        const selectedFiles = Array.from(event.currentTarget.files || []);
        this.photos.push(...selectedFiles.map((file) => ({file, category: "externa"})));
        this._syncInputFiles();
        this._renderPreviews();
    },

    _onCategoryChanged(event) {
        const index = Number.parseInt(event.currentTarget.dataset.index, 10);
        if (this.photos[index]) {
            this.photos[index].category = event.currentTarget.value;
        }
    },

    _onRemovePhoto(event) {
        event.preventDefault();
        const index = Number.parseInt(event.currentTarget.dataset.index, 10);
        this.photos.splice(index, 1);
        this._syncInputFiles();
        this._renderPreviews();
    },

    _syncInputFiles() {
        const transfer = new DataTransfer();
        for (const photo of this.photos) {
            transfer.items.add(photo.file);
        }
        this.input.files = transfer.files;
    },

    _renderPreviews() {
        this.preview.replaceChildren();
        this.counter.textContent = `${this.photos.length} ${this.photos.length === 1 ? "foto" : "fotos"}`;

        this.photos.forEach((photo, index) => {
            const column = document.createElement("div");
            column.className = "col-sm-6 col-lg-4";

            const card = document.createElement("div");
            card.className = "workshop-photo-preview-card";

            const image = document.createElement("img");
            image.src = URL.createObjectURL(photo.file);
            image.alt = photo.file.name;
            image.onload = () => URL.revokeObjectURL(image.src);

            const body = document.createElement("div");
            body.className = "p-2";

            const topRow = document.createElement("div");
            topRow.className = "d-flex align-items-start justify-content-between gap-2 mb-2";

            const filename = document.createElement("span");
            filename.className = "small fw-semibold text-truncate";
            filename.title = photo.file.name;
            filename.textContent = photo.file.name;

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "btn btn-sm btn-link text-danger p-0 js-workshop-photo-remove";
            removeButton.dataset.index = index;
            removeButton.title = "Quitar foto";
            removeButton.setAttribute("aria-label", "Quitar foto");
            removeButton.innerHTML = '<i class="fa fa-trash" aria-hidden="true"></i>';

            const category = document.createElement("select");
            category.name = "photo_category";
            category.className = "form-select form-select-sm js-workshop-photo-category";
            category.dataset.index = index;
            for (const [value, label] of PHOTO_CATEGORIES) {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = label;
                option.selected = value === photo.category;
                category.appendChild(option);
            }

            topRow.append(filename, removeButton);
            body.append(topRow, category);
            card.append(image, body);
            column.appendChild(card);
            this.preview.appendChild(column);
        });
    },
});
