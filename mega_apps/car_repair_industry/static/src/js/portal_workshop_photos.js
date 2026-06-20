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
        "change .js-workshop-vehicle-brand": "_onVehicleBrandChanged",
    },

    start() {
        this.photos = [];
        this.input = this.el.querySelector(".js-workshop-photo-input");
        this.preview = this.el.querySelector(".js-workshop-photo-preview");
        this.counter = this.el.querySelector(".js-workshop-photo-count");
        this.brandSelect = this.el.querySelector(".js-workshop-vehicle-brand");
        this.modelSelect = this.el.querySelector(".js-workshop-vehicle-model");
        this._updateCustomerType();
        this._updateVehicleModels();
        return this._super(...arguments);
    },

    _onCustomerTypeChanged() {
        this._updateCustomerType();
    },

    _updateCustomerType() {
        const customerType = this.el.querySelector("[name='customer_type']:checked")?.value || "particular";
        const isCompany = customerType === "renting" || customerType === "corporate";
        const particularFields = this.el.querySelector(".js-workshop-particular-fields");
        const rentingFields = this.el.querySelector(".js-workshop-renting-fields");
        const corporateFields = this.el.querySelector(".js-workshop-corporate-fields");

        particularFields.classList.toggle("d-none", isCompany);
        rentingFields.classList.toggle("d-none", customerType !== "renting");
        if (corporateFields) {
            corporateFields.classList.toggle("d-none", customerType !== "corporate");
        }

        for (const input of particularFields.querySelectorAll("input, select, textarea")) {
            input.disabled = isCompany;
        }
        for (const input of rentingFields.querySelectorAll("input, select, textarea")) {
            input.disabled = customerType !== "renting";
        }
        if (corporateFields) {
            for (const input of corporateFields.querySelectorAll("input, select, textarea")) {
                input.disabled = customerType !== "corporate";
            }
        }
        for (const input of particularFields.querySelectorAll(".js-workshop-particular-required")) {
            input.required = !isCompany;
        }
        for (const input of (corporateFields?.querySelectorAll(".js-workshop-corporate-required") || [])) {
            input.required = customerType === "corporate";
        }

        const deliveredName = this.el.querySelector("[name='delivered_by_name']");
        const deliveredPhone = this.el.querySelector("[name='delivered_by_phone']");
        deliveredName.required = isCompany;
        deliveredPhone.required = isCompany;
    },

    _onVehicleBrandChanged() {
        this._updateVehicleModels();
    },

    _updateVehicleModels() {
        if (!this.brandSelect || !this.modelSelect) {
            return;
        }
        const brandId = this.brandSelect.value;
        const placeholder = this.modelSelect.querySelector("option[value='']");
        for (const option of this.modelSelect.querySelectorAll("option")) {
            if (option === placeholder) {
                option.hidden = false;
                continue;
            }
            const optBrand = option.dataset.brandId || "0";
            option.hidden = brandId !== "" && optBrand !== brandId;
        }
        if (this.modelSelect.selectedOptions[0] && this.modelSelect.selectedOptions[0].hidden) {
            this.modelSelect.value = "";
        }
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

publicWidget.registry.WorkshopTechnicianPhotos = publicWidget.Widget.extend({
    selector: ".js-workshop-technician-photos",
    events: {
        "change .js-workshop-technician-photo-input": "_onFilesSelected",
        "change .js-workshop-technician-photo-category": "_onCategoryChanged",
        "click .js-workshop-technician-photo-remove": "_onRemovePhoto",
    },

    start() {
        this.photos = [];
        this.input = this.el.querySelector(".js-workshop-technician-photo-input");
        this.preview = this.el.querySelector(".js-workshop-technician-photo-preview");
        this.counter = this.el.querySelector(".js-workshop-technician-photo-count");
        return this._super(...arguments);
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
            removeButton.className = "btn btn-sm btn-link text-danger p-0 js-workshop-technician-photo-remove";
            removeButton.dataset.index = index;
            removeButton.title = "Quitar foto";
            removeButton.setAttribute("aria-label", "Quitar foto");
            removeButton.innerHTML = '<i class="fa fa-trash" aria-hidden="true"></i>';

            const category = document.createElement("select");
            category.name = "tech_photo_category";
            category.className = "form-select form-select-sm js-workshop-technician-photo-category";
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
publicWidget.registry.WorkshopOrderRow = publicWidget.Widget.extend({
    selector: ".js-workshop-order-row",
    events: {
        "click": "_onRowClick",
    },
    _onRowClick(event) {
        if (event.target.closest("a, button, input, select, textarea")) {
            return;
        }
        const href = this.el.dataset.href;
        if (href) {
            window.location.assign(href);
        }
    },
});
