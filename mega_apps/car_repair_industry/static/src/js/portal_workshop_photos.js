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
publicWidget.registry.WorkshopSpareRequest = publicWidget.Widget.extend({
    selector: "#workshop-spare-request-section",

    start() {
        this._lines = [];
        this._selected = null;
        this._debounceTimer = null;

        this._searchInput = this.el.querySelector("#spare-catalog-search");
        this._dropdown = this.el.querySelector("#spare-catalog-dropdown");
        this._qtyInput = this.el.querySelector("#spare-catalog-qty");
        this._noteInput = this.el.querySelector("#spare-catalog-note");
        this._addBtn = this.el.querySelector("#spare-add-line-btn");
        this._tbody = this.el.querySelector("#spare-lines-tbody");
        this._linesContainer = this.el.querySelector("#spare-lines-container");
        this._linesEmpty = this.el.querySelector("#spare-lines-empty");
        this._submitBtn = this.el.querySelector("#spare-submit-btn");
        this._errorBox = this.el.querySelector("#spare-submit-error");
        this._successBox = this.el.querySelector("#spare-submit-success");

        this._catalogUrl = this.el.dataset.catalogUrl;
        this._submitUrl = this.el.dataset.submitUrl;

        this._searchInput.addEventListener("input", () => this._onSearchInput());
        this._searchInput.addEventListener("blur", () => {
            setTimeout(() => this._hideDropdown(), 200);
        });
        this._addBtn.addEventListener("click", () => this._onAddLine());
        this._submitBtn.addEventListener("click", () => this._onSubmit());

        return this._super(...arguments);
    },

    _onSearchInput() {
        clearTimeout(this._debounceTimer);
        this._selected = null;
        this._addBtn.disabled = true;
        const q = this._searchInput.value.trim();
        if (q.length < 2) {
            this._hideDropdown();
            return;
        }
        this._debounceTimer = setTimeout(() => this._fetchCatalog(q), 300);
    },

    async _fetchCatalog(q) {
        try {
            const resp = await fetch(`${this._catalogUrl}?q=${encodeURIComponent(q)}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!resp.ok) {
                this._hideDropdown();
                return;
            }
            const items = await resp.json();
            this._renderDropdown(items);
        } catch {
            this._hideDropdown();
        }
    },

    _renderDropdown(items) {
        this._dropdown.replaceChildren();
        if (!items || items.length === 0) {
            this._hideDropdown();
            return;
        }
        for (const item of items) {
            const a = document.createElement("a");
            a.className = "dropdown-item";
            a.href = "#";
            a.textContent = item.name;
            a.addEventListener("mousedown", (e) => {
                e.preventDefault();
                this._selectCatalogItem(item);
            });
            this._dropdown.appendChild(a);
        }
        this._dropdown.style.display = "block";
    },

    _selectCatalogItem(item) {
        this._selected = item;
        this._searchInput.value = item.name;
        this._addBtn.disabled = false;
        this._hideDropdown();
    },

    _hideDropdown() {
        this._dropdown.style.display = "none";
    },

    _onAddLine() {
        if (!this._selected) return;
        const qty = parseFloat(this._qtyInput.value) || 0;
        if (qty <= 0) {
            this._qtyInput.focus();
            return;
        }
        const note = this._noteInput.value.trim();
        this._lines.push({ catalog_id: this._selected.id, name: this._selected.name, quantity: qty, note });
        this._renderLines();
        this._searchInput.value = "";
        this._qtyInput.value = "1";
        this._noteInput.value = "";
        this._selected = null;
        this._addBtn.disabled = true;
    },

    _renderLines() {
        this._tbody.replaceChildren();
        if (this._lines.length === 0) {
            this._linesContainer.style.display = "none";
            this._linesEmpty.style.display = "";
            this._submitBtn.disabled = true;
            return;
        }
        this._linesContainer.style.display = "";
        this._linesEmpty.style.display = "none";
        this._submitBtn.disabled = false;

        this._lines.forEach((line, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="small">${this._escapeHtml(line.name)}</td>
                <td class="text-center small">${line.quantity}</td>
                <td class="small text-muted">${this._escapeHtml(line.note || "—")}</td>
                <td class="text-center">
                    <button type="button" class="btn btn-sm btn-link text-danger p-0 js-spare-remove-line"
                            data-idx="${idx}" title="Quitar">
                        <i class="fa fa-trash" aria-hidden="true"></i>
                    </button>
                </td>`;
            tr.querySelector(".js-spare-remove-line").addEventListener("click", () => {
                this._lines.splice(idx, 1);
                this._renderLines();
            });
            this._tbody.appendChild(tr);
        });
    },

    async _onSubmit() {
        this._errorBox.classList.add("d-none");
        this._successBox.classList.add("d-none");
        if (this._lines.length === 0) return;

        const csrfToken = this.el.querySelector("#spare-csrf-token")?.value || "";
        const body = new FormData();
        body.append("csrf_token", csrfToken);
        body.append("lines", JSON.stringify(
            this._lines.map((l) => ({ catalog_id: l.catalog_id, quantity: l.quantity, note: l.note }))
        ));

        this._submitBtn.disabled = true;
        this._submitBtn.textContent = "Enviando…";

        try {
            const resp = await fetch(this._submitUrl, { method: "POST", body });
            const data = await resp.json();
            if (data.ok) {
                this._successBox.textContent = "Solicitud enviada correctamente. Recargando…";
                this._successBox.classList.remove("d-none");
                this._lines = [];
                setTimeout(() => window.location.reload(), 1500);
            } else {
                this._errorBox.textContent = data.error || "Error al enviar la solicitud.";
                this._errorBox.classList.remove("d-none");
                this._submitBtn.disabled = false;
                this._submitBtn.textContent = "Enviar solicitud al almacén";
            }
        } catch {
            this._errorBox.textContent = "Error de red. Intente de nuevo.";
            this._errorBox.classList.remove("d-none");
            this._submitBtn.disabled = false;
            this._submitBtn.textContent = "Enviar solicitud al almacén";
        }
    },

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    },
});

publicWidget.registry.WorkshopPrintChecklist = publicWidget.Widget.extend({
    selector: ".js-workshop-print-checklist",
    events: {
        "click": "_onPrintClick",
    },
    _onPrintClick() {
        const targetId = this.el.dataset.target;
        const target = targetId && document.getElementById(targetId);
        if (!target) {
            window.print();
            return;
        }
        const hadClass = document.body.classList.contains("workshop-printing-checklist");
        document.body.classList.add("workshop-printing-checklist");
        const cleanup = () => {
            document.body.classList.remove("workshop-printing-checklist");
            window.removeEventListener("afterprint", cleanup);
        };
        window.addEventListener("afterprint", cleanup);
        const restore = () => {
            if (!hadClass) {
                document.body.classList.remove("workshop-printing-checklist");
            }
        };
        setTimeout(restore, 1500);
        window.print();
    },
});
