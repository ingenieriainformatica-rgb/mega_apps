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
        "change .js-workshop-renting-mode": "_onRentingModeChanged",
        "change .js-workshop-photo-input": "_onFilesSelected",
        "change .js-workshop-camera-input": "_onCameraFileSelected",
        "change .js-workshop-photo-category": "_onCategoryChanged",
        "click .js-workshop-photo-remove": "_onRemovePhoto",
        "change .js-workshop-vehicle-brand": "_onVehicleBrandChanged",
        "input .workshop-input-uppercase": "_onUppercaseInput",
        "input .js-partner-vat-lookup": "_onVatInput",
        "input .js-plate-lookup": "_onPlateInput",
        "change .js-same-person-check": "_onSamePersonCheck",
        "change .js-client-doc-type": "_onDocTypeChange",
        "input [name='client_name'], input [name='client_phone'], input [name='client_email'], input [name='client_vat']": "_onClientFieldChange",
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
        this._initVehicleComboboxes();
        this._updateDocTypeDisplay();
        return this._super(...arguments);
    },

    _onCustomerTypeChanged() {
        this._updateCustomerType();
    },

    _onRentingModeChanged() {
        this._updateRentingMode();
    },

    _updateCustomerType() {
        const customerType = this.el.querySelector("[name='customer_type']:checked")?.value || "particular";
        const isRenting = customerType === "renting";
        const isCorporate = customerType === "corporate";
        const isCompany = isRenting || isCorporate;

        const particularFields = this.el.querySelector(".js-workshop-particular-fields");
        const rentingFields = this.el.querySelector(".js-workshop-renting-fields");
        const corporateFields = this.el.querySelector(".js-workshop-corporate-fields");
        const rentingModeSection = this.el.querySelector(".js-workshop-renting-mode-section");

        if (rentingModeSection) {
            rentingModeSection.classList.toggle("d-none", !isRenting);
            for (const input of rentingModeSection.querySelectorAll("input, select, textarea")) {
                input.disabled = !isRenting;
            }
        }

        if (corporateFields) {
            corporateFields.classList.toggle("d-none", !isCorporate);
            for (const input of corporateFields.querySelectorAll("input, select, textarea")) {
                input.disabled = !isCorporate;
            }
            for (const input of corporateFields.querySelectorAll(".js-workshop-corporate-required")) {
                input.required = isCorporate;
            }
        }

        if (isRenting) {
            this._updateRentingMode();
        } else {
            particularFields.classList.toggle("d-none", isCorporate);
            rentingFields.classList.add("d-none");
            for (const input of particularFields.querySelectorAll("input, select, textarea")) {
                input.disabled = isCorporate;
            }
            for (const input of rentingFields.querySelectorAll("input, select, textarea")) {
                input.disabled = true;
            }
            for (const input of particularFields.querySelectorAll(".js-workshop-particular-required")) {
                input.required = !isCorporate;
            }
        }

        const deliveredName = this.el.querySelector("[name='delivered_by_name']");
        const deliveredPhone = this.el.querySelector("[name='delivered_by_phone']");
        deliveredName.required = isCompany;
        deliveredPhone.required = isCompany;
    },

    _updateRentingMode() {
        const rentingMode = this.el.querySelector("[name='renting_mode']:checked")?.value || "billing";
        const isBilling = rentingMode === "billing";
        const particularFields = this.el.querySelector(".js-workshop-particular-fields");
        const rentingFields = this.el.querySelector(".js-workshop-renting-fields");

        particularFields.classList.toggle("d-none", isBilling);
        rentingFields.classList.toggle("d-none", !isBilling);

        for (const input of particularFields.querySelectorAll("input, select, textarea")) {
            input.disabled = isBilling;
        }
        for (const input of rentingFields.querySelectorAll("input, select, textarea")) {
            input.disabled = isBilling;
        }
        for (const input of particularFields.querySelectorAll(".js-workshop-particular-required")) {
            input.required = !isBilling;
        }
    },

    _onVehicleBrandChanged() {
        this._updateVehicleModels();
    },

    // ── Combobox: Marca + Línea ─────────────────────────────────────────────

    _initVehicleComboboxes() {
        const brandWrap = this.el.querySelector(".js-workshop-brand-combobox");
        const modelWrap = this.el.querySelector(".js-workshop-model-combobox");
        if (!brandWrap || !modelWrap) return;

        this._brandInput    = brandWrap.querySelector(".js-brand-search-input");
        this._brandDropdown = brandWrap.querySelector(".js-brand-dropdown");
        this._modelInput    = modelWrap.querySelector(".js-model-search-input");
        this._modelDropdown = modelWrap.querySelector(".js-model-dropdown");

        // Brand events
        this._brandInput.addEventListener("input",   () => this._onBrandInput());
        this._brandInput.addEventListener("focus",   () => this._onBrandFocus());
        this._brandInput.addEventListener("click",   () => this._onBrandFocus());
        this._brandInput.addEventListener("blur",    () => {
            setTimeout(() => {
                this._closeBrandDropdown();
                this._syncBrandDisplay();
            }, 200);
        });
        this._brandInput.addEventListener("keydown", (e) => {
            if (e.key === "Escape") { this._closeBrandDropdown(); this._syncBrandDisplay(); }
            if (e.key === "Enter")  { e.preventDefault(); this._pickFirstBrand(); }
        });

        // Model events
        this._modelInput.addEventListener("input",   () => this._onModelInput());
        this._modelInput.addEventListener("focus",   () => this._onModelFocus());
        this._modelInput.addEventListener("click",   () => this._onModelFocus());
        this._modelInput.addEventListener("blur",    () => {
            setTimeout(() => {
                this._closeModelDropdown();
                this._syncModelDisplay();
            }, 200);
        });
        this._modelInput.addEventListener("keydown", (e) => {
            if (e.key === "Escape") { this._closeModelDropdown(); this._syncModelDisplay(); }
            if (e.key === "Enter")  { e.preventDefault(); this._pickFirstModel(); }
        });

        document.addEventListener("click", (e) => {
            if (!brandWrap.contains(e.target)) this._closeBrandDropdown();
            if (!modelWrap.contains(e.target)) this._closeModelDropdown();
        });
    },

    _brandOptions() {
        if (!this.brandSelect) return [];
        return Array.from(this.brandSelect.options)
            .filter(o => o.value)
            .map(o => ({ id: o.value, name: o.text }));
    },

    _modelOptions(brandId) {
        if (!this.modelSelect) return [];
        return Array.from(this.modelSelect.options)
            .filter(o => o.value && (!brandId || String(o.dataset.brandId) === String(brandId)))
            .map(o => ({ id: o.value, name: o.text }));
    },

    _onBrandInput() {
        const q = (this._brandInput.value || "").toLowerCase().trim();
        const opts = q
            ? this._brandOptions().filter(o => o.name.toLowerCase().includes(q))
            : this._brandOptions();
        this._renderBrandDropdown(opts);
    },

    _onBrandFocus() {
        this._brandInput.select();
        const q = (this._brandInput.value || "").toLowerCase().trim();
        const opts = q
            ? this._brandOptions().filter(o => o.name.toLowerCase().includes(q))
            : this._brandOptions();
        this._renderBrandDropdown(opts);
    },

    _renderBrandDropdown(opts) {
        this._brandDropdown.replaceChildren();
        const currentId = this.brandSelect ? this.brandSelect.value : "";
        if (opts.length === 0) {
            const el = document.createElement("div");
            el.className = "dropdown-item text-muted small disabled py-2";
            el.textContent = "Sin resultados";
            this._brandDropdown.appendChild(el);
        } else {
            for (const opt of opts) {
                const a = document.createElement("a");
                a.className = "dropdown-item py-2" + (opt.id === currentId ? " active" : "");
                a.href = "#";
                a.textContent = opt.name;
                a.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    this._selectBrand(opt.id, opt.name);
                });
                this._brandDropdown.appendChild(a);
            }
        }
        this._brandDropdown.style.display = "block";
    },

    _closeBrandDropdown() {
        this._brandDropdown.style.display = "none";
    },

    _selectBrand(id, name) {
        if (this.brandSelect) this.brandSelect.value = id;
        if (this._brandInput) this._brandInput.value = name;
        this._closeBrandDropdown();
        // Reset model
        if (this.modelSelect) this.modelSelect.value = "";
        if (this._modelInput) {
            this._modelInput.value = "";
            this._modelInput.disabled = !id;
            this._modelInput.placeholder = id ? "Buscar línea..." : "Seleccione marca primero...";
        }
        this._closeModelDropdown();
        this._updateVehicleModels();
    },

    _pickFirstBrand() {
        const first = this._brandDropdown.querySelector("a.dropdown-item:not(.disabled)");
        if (first) first.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    },

    _syncBrandDisplay() {
        if (!this.brandSelect || !this._brandInput) return;
        const sel = this.brandSelect.options[this.brandSelect.selectedIndex];
        this._brandInput.value = (sel && sel.value) ? sel.text : "";
    },

    _onModelInput() {
        const brandId = this.brandSelect ? this.brandSelect.value : "";
        const q = (this._modelInput.value || "").toLowerCase().trim();
        const opts = this._modelOptions(brandId).filter(o =>
            !q || o.name.toLowerCase().includes(q)
        );
        this._renderModelDropdown(opts);
    },

    _onModelFocus() {
        const brandId = this.brandSelect ? this.brandSelect.value : "";
        if (!brandId) return;
        this._modelInput.select();
        const q = (this._modelInput.value || "").toLowerCase().trim();
        const opts = q
            ? this._modelOptions(brandId).filter(o => o.name.toLowerCase().includes(q))
            : this._modelOptions(brandId);
        this._renderModelDropdown(opts);
    },

    _renderModelDropdown(opts) {
        this._modelDropdown.replaceChildren();
        const currentId = this.modelSelect ? this.modelSelect.value : "";
        if (opts.length === 0) {
            const el = document.createElement("div");
            el.className = "dropdown-item text-muted small disabled py-2";
            el.textContent = "Sin resultados para esta marca";
            this._modelDropdown.appendChild(el);
        } else {
            for (const opt of opts) {
                const a = document.createElement("a");
                a.className = "dropdown-item py-2" + (opt.id === currentId ? " active" : "");
                a.href = "#";
                a.textContent = opt.name;
                a.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    this._selectModel(opt.id, opt.name);
                });
                this._modelDropdown.appendChild(a);
            }
        }
        this._modelDropdown.style.display = "block";
    },

    _closeModelDropdown() {
        this._modelDropdown.style.display = "none";
    },

    _selectModel(id, name) {
        if (this.modelSelect) this.modelSelect.value = id;
        if (this._modelInput) this._modelInput.value = name;
        this._closeModelDropdown();
    },

    _pickFirstModel() {
        const first = this._modelDropdown.querySelector("a.dropdown-item:not(.disabled)");
        if (first) first.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    },

    _syncModelDisplay() {
        if (!this.modelSelect || !this._modelInput) return;
        const sel = this.modelSelect.options[this.modelSelect.selectedIndex];
        this._modelInput.value = (sel && sel.value) ? sel.text : "";
    },

    // ───────────────────────────────────────────────────────────────────────

    _onUppercaseInput(ev) {
        const el = ev.target;
        const start = el.selectionStart;
        const end = el.selectionEnd;
        el.value = el.value.toUpperCase();
        if (el.setSelectionRange) {
            el.setSelectionRange(start, end);
        }
    },

    _onDocTypeChange() {
        this._updateDocTypeDisplay();
    },

    _updateDocTypeDisplay() {
        const section = this.el.querySelector('.js-workshop-particular-fields');
        if (!section) return;
        const docTypeSelect = section.querySelector('[name="client_doc_type"]');
        const isNit = docTypeSelect && docTypeSelect.value === 'nit';
        const nameInput = section.querySelector('[name="client_name"]');
        const nameLabel = section.querySelector('.js-client-name-label');
        const banner = section.querySelector('.js-nit-company-banner');

        if (nameLabel) {
            nameLabel.innerHTML = isNit
                ? 'Razón social <span class="text-danger">*</span>'
                : 'Nombre del cliente <span class="text-danger">*</span>';
        }
        if (nameInput) {
            nameInput.placeholder = isNit ? 'NOMBRE DE LA EMPRESA' : 'NOMBRE COMPLETO';
        }
        if (banner) {
            banner.classList.toggle('d-none', !isNit);
        }
    },

    _onSamePersonCheck(ev) {
        this._syncSamePerson(ev.target.checked);
    },

    _onClientFieldChange() {
        const checkbox = this.el.querySelector('.js-same-person-check');
        if (checkbox && checkbox.checked) {
            this._syncSamePerson(true);
        }
    },

    _syncSamePerson(checked) {
        const nameEl    = this.el.querySelector('[name="delivered_by_name"]');
        const phoneEl   = this.el.querySelector('[name="delivered_by_phone"]');
        const emailEl   = this.el.querySelector('[name="delivered_by_email"]');
        const docEl     = this.el.querySelector('[name="delivered_by_document"]');
        const fieldsRow = this.el.querySelector('.js-delivered-by-fields');

        if (checked) {
            const clientName  = (this.el.querySelector('[name="client_name"]')?.value || '').toUpperCase();
            const clientPhone = this.el.querySelector('[name="client_phone"]')?.value || '';
            const clientEmail = this.el.querySelector('[name="client_email"]')?.value || '';
            const clientVat   = (this.el.querySelector('[name="client_vat"]')?.value || '').toUpperCase();

            if (nameEl)  { nameEl.value  = clientName;  nameEl.readOnly  = true; }
            if (phoneEl) { phoneEl.value = clientPhone; phoneEl.readOnly = true; }
            if (emailEl) { emailEl.value = clientEmail; emailEl.readOnly = true; }
            if (docEl)   { docEl.value   = clientVat;   docEl.readOnly   = true; }
            if (fieldsRow) fieldsRow.style.opacity = '0.7';
        } else {
            if (nameEl)  { nameEl.value  = ''; nameEl.readOnly  = false; }
            if (phoneEl) { phoneEl.value = ''; phoneEl.readOnly = false; }
            if (emailEl) { emailEl.value = ''; emailEl.readOnly = false; }
            if (docEl)   { docEl.value   = ''; docEl.readOnly   = false; }
            if (fieldsRow) fieldsRow.style.opacity = '1';
        }
    },

    _onVatInput(ev) {
        clearTimeout(this._vatLookupTimer);
        this._vatLookupTimer = setTimeout(() => this._doVatLookup(ev.target.value), 500);
    },

    _onPlateInput(ev) {
        clearTimeout(this._plateLookupTimer);
        this._plateLookupTimer = setTimeout(() => this._doVehicleLookup(ev.target.value), 600);
    },

    async _doVehicleLookup(rawPlate) {
        const plate = (rawPlate || '').trim().toUpperCase();
        const section = this.el.querySelector('[name="license_plate"]').closest('.workshop-form-section');
        const statusEl = section && section.querySelector('.js-vehicle-lookup-status');
        const iconEl = section && section.querySelector('.js-plate-lookup-icon');

        if (plate.length < 4) {
            if (statusEl) statusEl.innerHTML = '';
            return;
        }

        if (iconEl) iconEl.className = 'fa fa-spinner fa-spin';
        try {
            const resp = await fetch(`/my/workshop/vehicle-lookup?plate=${encodeURIComponent(plate)}`);
            const data = await resp.json();
            if (iconEl) iconEl.className = 'fa fa-search';

            if (data.found) {
                // Campos de texto simples
                const textFields = {
                    model_year: data.model_year,
                    engine_displacement: data.engine_displacement,
                    engine_number: data.engine_number,
                    vin_sn: data.vin_sn,
                };
                for (const [name, val] of Object.entries(textFields)) {
                    const el = this.el.querySelector(`[name="${name}"]`);
                    if (el && val) el.value = val;
                }

                // Marca → actualiza opciones de modelo → selecciona modelo
                if (data.brand_id && this.brandSelect) {
                    this.brandSelect.value = String(data.brand_id);
                    this._updateVehicleModels();
                }
                if (data.model_id && this.modelSelect) {
                    this.modelSelect.value = String(data.model_id);
                }
                // Sync combobox visual display after plate autofill
                this._syncBrandDisplay();
                this._syncModelDisplay();
                if (this._modelInput && this.brandSelect && this.brandSelect.value) {
                    this._modelInput.disabled = false;
                    this._modelInput.placeholder = "Buscar línea...";
                }

                // Tipo de combustible
                if (data.fuel_type) {
                    const fuelEl = this.el.querySelector('[name="fuel_type"]');
                    if (fuelEl) fuelEl.value = data.fuel_type;
                }

                if (statusEl) statusEl.innerHTML =
                    '<span class="badge bg-success"><i class="fa fa-check me-1"></i>Vehículo encontrado</span>';
            } else {
                if (statusEl) statusEl.innerHTML =
                    '<span class="badge bg-secondary"><i class="fa fa-car me-1"></i>Vehículo nuevo</span>';
            }
        } catch (_) {
            if (iconEl) iconEl.className = 'fa fa-search';
        }
    },

    async _doVatLookup(rawVat) {
        const vat = (rawVat || '').trim().toUpperCase();
        const section = this.el.querySelector('.js-workshop-particular-fields');
        const statusEl = section && section.querySelector('.js-vat-lookup-status');
        const iconEl = section && section.querySelector('.js-vat-lookup-icon');
        const docType = (section && section.querySelector('[name="client_doc_type"]')?.value) || 'cedula';

        if (vat.length < 3) {
            if (statusEl) statusEl.innerHTML = '';
            return;
        }

        if (iconEl) iconEl.className = 'fa fa-spinner fa-spin';
        try {
            const url = `/my/workshop/partner-lookup?vat=${encodeURIComponent(vat)}&doc_type=${encodeURIComponent(docType)}`;
            const resp = await fetch(url);
            const data = await resp.json();
            if (iconEl) iconEl.className = 'fa fa-search';

            if (data.found) {
                const nameEl = section.querySelector('[name="client_name"]');
                const phoneEl = section.querySelector('[name="client_phone"]');
                const emailEl = section.querySelector('[name="client_email"]');
                if (nameEl) nameEl.value = (data.name || '').toUpperCase();
                if (phoneEl && data.phone) phoneEl.value = data.phone;
                if (emailEl && data.email) emailEl.value = data.email;
                if (statusEl) statusEl.innerHTML =
                    '<span class="badge bg-success"><i class="fa fa-check me-1"></i>Cliente encontrado — datos cargados</span>';
            } else {
                if (statusEl) statusEl.innerHTML =
                    '<span class="badge bg-warning text-dark"><i class="fa fa-user-plus me-1"></i>Nuevo cliente — se registrará al guardar</span>';
            }
        } catch (_) {
            if (iconEl) iconEl.className = 'fa fa-search';
        }
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

    _onCameraFileSelected(event) {
        const selectedFiles = Array.from(event.currentTarget.files || []);
        this.photos.push(...selectedFiles.map((file) => ({file, category: "externa"})));
        this._syncInputFiles();
        this._renderPreviews();
        event.currentTarget.value = "";
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

publicWidget.registry.WorkshopServiceSelector = publicWidget.Widget.extend({
    selector: ".js-workshop-service-selector",

    start() {
        this._selectedIds = [];   // [{id, name}]  — existing service.type records
        this._newNames = [];      // [string]       — new names to create on submit
        this._debounce = null;

        this._searchInput  = this.el.querySelector("#service-search-input");
        this._dropdown     = this.el.querySelector("#service-search-dropdown");
        this._chipsEl      = this.el.querySelector("#service-selected-chips");
        this._hiddenEl     = this.el.querySelector("#service-hidden-inputs");
        this._emptyMsg     = this.el.querySelector("#service-empty-msg");
        this._errorMsg     = this.el.querySelector("#service-error-msg");

        this._searchInput.addEventListener("input",   () => this._onSearchInput());
        this._searchInput.addEventListener("focus",   () => this._onSearchInput());
        this._searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Escape") this._closeDropdown();
        });
        this._initCreateModal();

        document.addEventListener("click", (e) => {
            if (!this.el.contains(e.target)) this._closeDropdown();
        });

        const form = this.el.closest("form");
        if (form) {
            form.addEventListener("submit", (e) => {
                if (this._selectedIds.length === 0 && this._newNames.length === 0) {
                    e.preventDefault();
                    this._errorMsg.classList.remove("d-none");
                    this.el.scrollIntoView({ behavior: "smooth", block: "center" });
                } else {
                    this._errorMsg.classList.add("d-none");
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Creando orden...';
                    }
                }
            });
        }

        return this._super(...arguments);
    },

    _onSearchInput() {
        clearTimeout(this._debounce);
        const q = this._searchInput.value.trim();
        this._debounce = setTimeout(() => this._fetchServices(q), q ? 250 : 0);
    },

    async _fetchServices(q) {
        try {
            const resp = await fetch(
                `/my/workshop/service-search?q=${encodeURIComponent(q)}`,
                { headers: { "X-Requested-With": "XMLHttpRequest" } }
            );
            if (!resp.ok) return;
            const items = await resp.json();
            this._renderDropdown(items);
        } catch { /* silent */ }
    },

    _renderDropdown(items) {
        this._dropdown.replaceChildren();
        const q = (this._searchInput.value || "").trim();
        if (!items || items.length === 0) {
            const el = document.createElement("div");
            el.className = "dropdown-item text-muted small disabled py-2";
            el.textContent = "Sin resultados";
            this._dropdown.appendChild(el);
        } else {
            for (const item of items) {
                const isSelected = this._selectedIds.some(s => s.id === item.id);
                const a = document.createElement("a");
                a.className = "dropdown-item py-2" + (isSelected ? " text-muted" : "");
                a.href = "#";
                a.innerHTML = `<i class="fa fa-wrench me-1 text-secondary"></i>${this._esc(item.name)}`
                    + (isSelected ? ` <i class="fa fa-check text-success ms-1 float-end"></i>` : "");
                a.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    this._selectExisting(item.id, item.name);
                });
                this._dropdown.appendChild(a);
            }
        }
        if (q) {
            this._appendCreateOption(q);
        }
        this._dropdown.style.display = "block";
    },

    _appendCreateOption(name) {
        const divider = document.createElement("div");
        divider.className = "dropdown-divider";
        this._dropdown.appendChild(divider);
        const a = document.createElement("a");
        a.className = "dropdown-item py-2 fw-semibold ws-create-service-option";
        a.href = "#";
        a.innerHTML = `<i class="fa fa-plus-circle me-1 text-success"></i>Crear nuevo servicio: <strong>"${this._esc(name)}"</strong>`;
        a.addEventListener("mousedown", (e) => {
            e.preventDefault();
            this._closeDropdown();
            this._openCreateModal(name);
        });
        this._dropdown.appendChild(a);
    },

    _closeDropdown() {
        this._dropdown.style.display = "none";
        this._dropdown.replaceChildren();
    },

    _selectExisting(id, name) {
        if (!this._selectedIds.some(s => s.id === id)) {
            this._selectedIds.push({ id, name });
            this._sync();
        }
        this._searchInput.value = "";
        this._closeDropdown();
        this._searchInput.focus();
        this._fetchServices("");
    },

    _removeExisting(id) {
        this._selectedIds = this._selectedIds.filter(s => s.id !== id);
        this._sync();
    },

    _removeNew(name) {
        this._newNames = this._newNames.filter(n => n !== name);
        this._sync();
    },

    _sync() {
        this._renderChips();
        this._renderHiddenInputs();
        const total = this._selectedIds.length + this._newNames.length;
        this._emptyMsg.style.display = total ? "none" : "";
        if (total > 0) this._errorMsg.classList.add("d-none");
    },

    _renderChips() {
        this._chipsEl.replaceChildren();
        for (const { id, name } of this._selectedIds) {
            this._chipsEl.appendChild(this._buildChip(name, false, () => this._removeExisting(id)));
        }
        for (const name of this._newNames) {
            this._chipsEl.appendChild(this._buildChip(name, true, () => this._removeNew(name)));
        }
    },

    _buildChip(label, isNew, onRemove) {
        const chip = document.createElement("span");
        chip.className = `badge rounded-pill d-inline-flex align-items-center gap-1 py-2 px-3 ${isNew ? "bg-success" : "bg-primary"}`;
        chip.style.fontSize = "0.82rem";
        const icon = document.createElement("i");
        icon.className = "fa fa-wrench";
        const text = document.createElement("span");
        text.textContent = label + (isNew ? " ✦" : "");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-close btn-close-white ms-1";
        btn.style.cssText = "font-size:0.55rem;opacity:0.8;";
        btn.setAttribute("aria-label", "Quitar");
        btn.addEventListener("click", onRemove);
        chip.append(icon, text, btn);
        return chip;
    },

    _renderHiddenInputs() {
        this._hiddenEl.replaceChildren();
        for (const { id } of this._selectedIds) {
            const inp = document.createElement("input");
            inp.type = "hidden";
            inp.name = "service_types";
            inp.value = id;
            this._hiddenEl.appendChild(inp);
        }
        for (const name of this._newNames) {
            const inp = document.createElement("input");
            inp.type = "hidden";
            inp.name = "new_service_names";
            inp.value = name;
            this._hiddenEl.appendChild(inp);
        }
    },

    _initCreateModal() {
        const MODAL_ID = "ws-create-service-modal";
        if (document.getElementById(MODAL_ID)) {
            this._modal = document.getElementById(MODAL_ID);
        } else {
            const el = document.createElement("div");
            el.id = MODAL_ID;
            el.className = "ws-service-modal";
            el.innerHTML = `
  <div class="ws-service-modal-dialog">
    <div class="ws-service-modal-header">
      <span class="fw-semibold"><i class="fa fa-plus-circle me-2 text-success"></i>Nuevo servicio</span>
      <button type="button" class="ws-modal-close-btn" aria-label="Cerrar">&times;</button>
    </div>
    <div class="ws-service-modal-body">
      <label class="form-label small fw-semibold mb-1">Nombre del servicio</label>
      <input type="text" class="form-control workshop-input-uppercase ws-modal-name-input"
             placeholder="NOMBRE DEL SERVICIO..." autocomplete="off" spellcheck="false"/>
      <div class="ws-modal-error text-danger small mt-1 d-none"></div>
      <p class="text-muted small mt-2 mb-0">
        <i class="fa fa-info-circle me-1"></i>Si ya existe en el catálogo se enlazará automáticamente.
      </p>
    </div>
    <div class="ws-service-modal-footer">
      <button type="button" class="btn btn-sm btn-light ws-modal-cancel-btn">Cancelar</button>
      <button type="button" class="btn btn-sm btn-success ws-modal-save-btn">
        <i class="fa fa-check me-1"></i>Crear y seleccionar
      </button>
    </div>
  </div>`;
            document.body.appendChild(el);
            this._modal = el;
        }
        const nameInput = this._modal.querySelector(".ws-modal-name-input");
        this._modal.querySelector(".ws-modal-save-btn")
            .addEventListener("click", () => this._onModalSave());
        this._modal.querySelector(".ws-modal-cancel-btn")
            .addEventListener("click", () => this._closeCreateModal());
        this._modal.querySelector(".ws-modal-close-btn")
            .addEventListener("click", () => this._closeCreateModal());
        nameInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter")  { e.preventDefault(); this._onModalSave(); }
            if (e.key === "Escape") { this._closeCreateModal(); }
        });
        this._modal.addEventListener("click", (e) => {
            if (e.target === this._modal) this._closeCreateModal();
        });
    },

    _openCreateModal(searchText) {
        const nameInput = this._modal.querySelector(".ws-modal-name-input");
        const errorEl   = this._modal.querySelector(".ws-modal-error");
        const saveBtn   = this._modal.querySelector(".ws-modal-save-btn");
        nameInput.value = (searchText || "").toUpperCase();
        errorEl.classList.add("d-none");
        errorEl.textContent = "";
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa fa-check me-1"></i>Crear y seleccionar';
        this._modal.style.display = "flex";
        document.body.style.overflow = "hidden";
        requestAnimationFrame(() => {
            this._modal.classList.add("ws-modal-visible");
            nameInput.select();
            nameInput.focus();
        });
    },

    _closeCreateModal() {
        this._modal.classList.remove("ws-modal-visible");
        document.body.style.overflow = "";
        setTimeout(() => { this._modal.style.display = "none"; }, 200);
    },

    async _onModalSave() {
        const nameInput = this._modal.querySelector(".ws-modal-name-input");
        const errorEl   = this._modal.querySelector(".ws-modal-error");
        const saveBtn   = this._modal.querySelector(".ws-modal-save-btn");
        const name = (nameInput.value || "").trim();
        if (!name) {
            errorEl.textContent = "Ingresa el nombre del servicio.";
            errorEl.classList.remove("d-none");
            nameInput.focus();
            return;
        }
        const lc = name.toLowerCase();
        if (this._selectedIds.some(s => s.name.toLowerCase() === lc) ||
            this._newNames.some(n => n.toLowerCase() === lc)) {
            this._closeCreateModal();
            this._searchInput.value = "";
            return;
        }
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Verificando...';
        try {
            const resp = await fetch(
                `/my/workshop/service-search?q=${encodeURIComponent(name)}`,
                { headers: { "X-Requested-With": "XMLHttpRequest" } }
            );
            if (resp.ok) {
                const items = await resp.json();
                const match = items.find(i => i.name.toLowerCase() === lc);
                if (match) {
                    this._selectExisting(match.id, match.name);
                    this._closeCreateModal();
                    this._searchInput.value = "";
                    return;
                }
            }
            this._newNames.push(name);
            this._sync();
            this._closeCreateModal();
            this._searchInput.value = "";
        } catch {
            errorEl.textContent = "Error de conexión. Intenta de nuevo.";
            errorEl.classList.remove("d-none");
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa fa-check me-1"></i>Crear y seleccionar';
        }
    },

    _esc(str) {
        return String(str || "")
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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
publicWidget.registry.WorkshopAddServiceOrder = publicWidget.Widget.extend({
    selector: ".js-add-service-order",

    start() {
        this._repairId = this.el.dataset.repairId;
        this._csrf = this.el.dataset.csrf;
        this._input = this.el.querySelector("#new-service-name");
        this._btn = this.el.querySelector("#btn-add-service-order");
        this._msg = this.el.querySelector("#add-service-msg");
        this._tbody = document.querySelector("#workshop-services-form tbody");

        this._btn.addEventListener("click", () => this._onAdd());
        this._input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); this._onAdd(); }
        });
        return this._super(...arguments);
    },

    async _onAdd() {
        const name = this._input.value.trim();
        if (!name) return;

        this._btn.disabled = true;
        this._showMsg("", "");

        try {
            const resp = await fetch(
                `/my/workshop/order/${this._repairId}/services/add`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { name } }),
                }
            );
            const data = await resp.json();
            const result = data.result || {};

            if (result.error === "forbidden") {
                this._showMsg("No tienes permiso para agregar servicios.", "danger");
            } else if (result.already_exists) {
                this._showMsg(
                    `<i class="fa fa-info-circle me-1"></i>El servicio "<strong>${result.service_name}</strong>" ya está en esta orden.`,
                    "warning"
                );
            } else if (result.success) {
                this._appendRow(result);
                this._input.value = "";
                this._showMsg(
                    `<i class="fa fa-check-circle me-1"></i>Servicio "<strong>${result.service_name}</strong>" agregado${result.is_new_type ? " (nuevo)" : ""}.`,
                    "success"
                );
            }
        } catch {
            this._showMsg("Error de conexión. Intenta de nuevo.", "danger");
        } finally {
            this._btn.disabled = false;
        }
    },

    _appendRow(result) {
        if (!this._tbody) return;
        const rowCount = this._tbody.querySelectorAll("tr").length + 1;
        const tr = document.createElement("tr");
        tr.className = "workshop-service-row workshop-service-row-pendiente";
        tr.innerHTML = `
            <td class="workshop-service-num">${result.seq || rowCount}</td>
            <td><div class="fw-semibold">${result.service_name}</div></td>
            <td>
                <select name="svc_status_${result.line_id}" class="form-select form-select-sm workshop-service-status-select">
                    <option value="pendiente" selected>⏳ Pendiente</option>
                    <option value="en_progreso">⚙ En progreso</option>
                    <option value="completado">✓ Completado</option>
                </select>
            </td>
            <td>
                <input name="svc_notes_${result.line_id}" class="form-control form-control-sm"
                       placeholder="Notas sobre ${result.service_name}" value=""/>
            </td>`;
        this._tbody.appendChild(tr);
    },

    _showMsg(html, type) {
        if (!html) { this._msg.classList.add("d-none"); return; }
        this._msg.className = `small mt-2 text-${type}`;
        this._msg.innerHTML = html;
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

        if (!this._searchInput) {
            return this._super(...arguments);
        }

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

publicWidget.registry.WorkshopSpareEditLine = publicWidget.Widget.extend({
    selector: "#workshop-spare-request-section",

    start() {
        this._catalogUrl = this.el.dataset.catalogUrl || "/my/workshop/spare-catalog";
        this._activeForm = null;
        this._debounce = null;

        this.el.addEventListener("click", (e) => {
            const toggle = e.target.closest(".js-spare-add-toggle");
            const del = e.target.closest(".js-spare-delete-existing");
            const cancel = e.target.closest(".js-spare-add-cancel");
            const confirm = e.target.closest(".js-spare-add-confirm");
            if (toggle) { e.preventDefault(); this._onToggleForm(toggle); }
            else if (del) { e.preventDefault(); this._onDeleteLine(del); }
            else if (cancel) { e.preventDefault(); this._onCancelForm(cancel); }
            else if (confirm) { e.preventDefault(); this._onConfirmAdd(confirm); }
        });

        this.el.addEventListener("input", (e) => {
            const search = e.target.closest(".js-spare-edit-search");
            if (search) this._onSearchInput(search);
        });

        document.addEventListener("click", (e) => {
            if (this._activeForm && !this._activeForm.contains(e.target)) {
                const dd = this._activeForm.querySelector(".js-spare-edit-dropdown");
                if (dd) dd.style.display = "none";
            }
        });

        return this._super(...arguments);
    },

    _onToggleForm(btn) {
        const reqId = btn.dataset.requestId;
        const form = this.el.querySelector(`#spare-add-form-${reqId}`);
        if (!form) return;
        const hidden = form.classList.contains("d-none");
        if (this._activeForm && this._activeForm !== form) {
            this._closeForm(this._activeForm);
        }
        if (hidden) {
            form.classList.remove("d-none");
            this._activeForm = form;
            form.querySelector(".js-spare-edit-search")?.focus();
        } else {
            this._closeForm(form);
        }
    },

    _closeForm(form) {
        form.classList.add("d-none");
        const search = form.querySelector(".js-spare-edit-search");
        const catId = form.querySelector(".js-spare-edit-catalog-id");
        const dd = form.querySelector(".js-spare-edit-dropdown");
        const confirm = form.querySelector(".js-spare-add-confirm");
        const msg = form.querySelector(".js-spare-add-msg");
        const qty = form.querySelector(".js-spare-edit-qty");
        const note = form.querySelector(".js-spare-edit-note");
        if (search) search.value = "";
        if (catId) catId.value = "";
        if (qty) qty.value = "1";
        if (note) note.value = "";
        if (dd) { dd.replaceChildren(); dd.style.display = "none"; }
        if (confirm) confirm.disabled = true;
        if (msg) { msg.classList.add("d-none"); msg.textContent = ""; }
        this._activeForm = null;
    },

    _onCancelForm(cancelBtn) {
        const form = cancelBtn.closest(".js-spare-add-form");
        if (form) this._closeForm(form);
    },

    _onSearchInput(searchEl) {
        clearTimeout(this._debounce);
        const form = searchEl.closest(".js-spare-add-form");
        if (!form) return;
        const catId = form.querySelector(".js-spare-edit-catalog-id");
        const confirm = form.querySelector(".js-spare-add-confirm");
        if (catId) catId.value = "";
        if (confirm) confirm.disabled = true;
        const q = searchEl.value.trim();
        if (q.length < 2) {
            const dd = form.querySelector(".js-spare-edit-dropdown");
            if (dd) dd.style.display = "none";
            return;
        }
        this._debounce = setTimeout(() => this._fetchCatalog(q, form), 300);
    },

    async _fetchCatalog(q, form) {
        try {
            const resp = await fetch(`${this._catalogUrl}?q=${encodeURIComponent(q)}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!resp.ok) return;
            const items = await resp.json();
            this._renderDropdown(items, form);
        } catch { /* silent */ }
    },

    _renderDropdown(items, form) {
        const dd = form.querySelector(".js-spare-edit-dropdown");
        if (!dd) return;
        dd.replaceChildren();
        if (!items || items.length === 0) { dd.style.display = "none"; return; }
        for (const item of items) {
            const a = document.createElement("a");
            a.className = "dropdown-item small py-1";
            a.href = "#";
            a.textContent = item.name;
            a.addEventListener("mousedown", (e) => { e.preventDefault(); this._selectItem(item, form); });
            dd.appendChild(a);
        }
        dd.style.display = "block";
    },

    _selectItem(item, form) {
        const search = form.querySelector(".js-spare-edit-search");
        const catId = form.querySelector(".js-spare-edit-catalog-id");
        const confirm = form.querySelector(".js-spare-add-confirm");
        const dd = form.querySelector(".js-spare-edit-dropdown");
        if (search) search.value = item.name;
        if (catId) catId.value = item.id;
        if (confirm) confirm.disabled = false;
        if (dd) { dd.replaceChildren(); dd.style.display = "none"; }
    },

    async _onConfirmAdd(confirmBtn) {
        const form = confirmBtn.closest(".js-spare-add-form");
        if (!form) return;
        const requestId = form.dataset.requestId;
        const catalogId = form.querySelector(".js-spare-edit-catalog-id")?.value;
        const qty = parseFloat(form.querySelector(".js-spare-edit-qty")?.value) || 0;
        const note = form.querySelector(".js-spare-edit-note")?.value.trim() || "";
        const msg = form.querySelector(".js-spare-add-msg");
        const tbodyId = form.dataset.tbodyId;
        if (!catalogId || qty <= 0) return;
        confirmBtn.disabled = true;
        try {
            const resp = await fetch("/my/workshop/spares/line/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call",
                    params: { request_id: requestId, catalog_id: catalogId, quantity: qty, note } }),
            });
            const data = await resp.json();
            const result = data.result || {};
            if (result.ok) {
                this._appendRow(tbodyId, result, form);
                const search = form.querySelector(".js-spare-edit-search");
                const qtyEl = form.querySelector(".js-spare-edit-qty");
                const noteEl = form.querySelector(".js-spare-edit-note");
                const catEl = form.querySelector(".js-spare-edit-catalog-id");
                if (search) search.value = "";
                if (qtyEl) qtyEl.value = "1";
                if (noteEl) noteEl.value = "";
                if (catEl) catEl.value = "";
                this._showMsg(msg, "Repuesto agregado.", "success");
                setTimeout(() => this._clearMsg(msg), 3000);
            } else {
                this._showMsg(msg, result.msg || "Error al agregar.", "danger");
                confirmBtn.disabled = false;
            }
        } catch {
            this._showMsg(msg, "Error de red.", "danger");
            confirmBtn.disabled = false;
        }
    },

    _appendRow(tbodyId, result, form) {
        const tbody = document.getElementById(tbodyId);
        if (!tbody) return;
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="fw-semibold">${this._esc(result.name)}</td>
            <td class="text-center">${result.quantity}</td>
            <td class="small text-muted">${this._esc(result.note || "—")}</td>
            <td class="text-center p-1">
                <button type="button" class="btn btn-sm btn-link text-danger p-0 js-spare-delete-existing"
                        data-line-id="${result.line_id}" title="Quitar">
                    <i class="fa fa-trash"></i>
                </button>
            </td>`;
        tbody.appendChild(tr);
    },

    async _onDeleteLine(delBtn) {
        const lineId = delBtn.dataset.lineId;
        if (!lineId) return;
        delBtn.disabled = true;
        try {
            const resp = await fetch("/my/workshop/spares/line/remove", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { line_id: lineId } }),
            });
            const data = await resp.json();
            const result = data.result || {};
            if (result.ok) {
                delBtn.closest("tr")?.remove();
            } else {
                alert(result.msg || "No se puede eliminar esta línea.");
                delBtn.disabled = false;
            }
        } catch {
            alert("Error de red.");
            delBtn.disabled = false;
        }
    },

    _showMsg(el, text, type) {
        if (!el) return;
        el.className = `small mt-1 text-${type}`;
        el.textContent = text;
        el.classList.remove("d-none");
    },

    _clearMsg(el) {
        if (!el) return;
        el.classList.add("d-none");
        el.textContent = "";
    },

    _esc(str) {
        return String(str || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    },
});

publicWidget.registry.WorkshopChecklistSave = publicWidget.Widget.extend({
    selector: '#tecnico_checklist_form',
    events: { 'submit': '_onSubmit' },
    start() {
        this._repairId = this.el.dataset.repairId;
        return this._super(...arguments);
    },
    async _onSubmit(ev) {
        ev.preventDefault();
        const form = this.el;
        const errorBox = document.getElementById('checklist-error-msg');
        let firstInvalid = null;

        form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

        const radioGroups = {};
        form.querySelectorAll("input[type='radio'][required]").forEach(radio => {
            if (!(radio.name in radioGroups)) radioGroups[radio.name] = { checked: false, radios: [] };
            radioGroups[radio.name].radios.push(radio);
            if (radio.checked) radioGroups[radio.name].checked = true;
        });
        Object.values(radioGroups).forEach(group => {
            if (!group.checked) {
                group.radios.forEach(r => r.classList.add('is-invalid'));
                if (!firstInvalid) firstInvalid = group.radios[0];
            }
        });

        form.querySelectorAll("input[type='text'][required], input:not([type])[required]").forEach(input => {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                if (!firstInvalid) firstInvalid = input;
            }
        });

        if (firstInvalid) {
            if (errorBox) errorBox.classList.remove('d-none');
            firstInvalid.closest('tr')
                ? firstInvalid.closest('tr').scrollIntoView({ behavior: 'smooth', block: 'center' })
                : firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        if (errorBox) errorBox.classList.add('d-none');

        const lineMap = {};
        const getLine = id => { if (!lineMap[id]) lineMap[id] = { id: parseInt(id, 10) }; return lineMap[id]; };

        const seenState = new Set();
        form.querySelectorAll('[name^="tech_state_"]').forEach(el => {
            const id = el.name.replace('tech_state_', '');
            if (seenState.has(id)) return;
            seenState.add(id);
            if (el.tagName === 'SELECT') {
                getLine(id).state = el.value;
            } else {
                const checked = form.querySelector(`input[name="${el.name}"]:checked`);
                if (checked) getLine(id).state = checked.value;
            }
        });
        form.querySelectorAll('[name^="tech_obs_"]').forEach(el => {
            getLine(el.name.replace('tech_obs_', '')).observation = el.value || '';
        });
        form.querySelectorAll('[name^="tech_measure_left_"]').forEach(el => {
            getLine(el.name.replace('tech_measure_left_', '')).measurement_left = el.value || '';
        });
        form.querySelectorAll('[name^="tech_measure_right_"]').forEach(el => {
            getLine(el.name.replace('tech_measure_right_', '')).measurement_right = el.value || '';
        });
        form.querySelectorAll('[name^="tech_position_"]').forEach(el => {
            getLine(el.name.replace('tech_position_', '')).position = el.value || '';
        });

        const btn = form.querySelector('[type="submit"]');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Guardando...';

        try {
            const result = await _rpc(`/my/workshop/order/${this._repairId}/checklist/save`, {
                lines: Object.values(lineMap),
            });
            if (result.ok) {
                _showWorkshopToast('Checklist guardado correctamente');
                btn.innerHTML = '<i class="fa fa-check me-1"></i> Guardado';
                setTimeout(() => { btn.innerHTML = original; btn.disabled = false; }, 2500);
            } else {
                _showWorkshopToast(result.error || 'Error al guardar', 'danger');
                btn.innerHTML = original;
                btn.disabled = false;
            }
        } catch (err) {
            _showWorkshopToast(err.message || 'Error de red.', 'danger');
            btn.innerHTML = original;
            btn.disabled = false;
        }
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

function _showWorkshopToast(message, type = 'success') {
    let container = document.getElementById('workshop-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'workshop-toast-container';
        container.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} shadow mb-0 py-2 px-3`;
    toast.style.cssText = 'min-width:220px;max-width:360px;animation:fadeIn .2s ease;';
    toast.innerHTML = `<i class="fa fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>${message}`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

async function _rpc(route, params) {
    const resp = await fetch(route, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params }),
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.error.data?.message || data.error.message || 'Error del servidor');
    return data.result;
}

publicWidget.registry.WorkshopServicesSave = publicWidget.Widget.extend({
    selector: '#workshop-services-form',
    events: { 'submit': '_onSubmit' },
    start() {
        this._repairId = this.el.dataset.repairId;
        return this._super(...arguments);
    },
    async _onSubmit(ev) {
        ev.preventDefault();
        const form = this.el;
        const btn = form.querySelector('[type="submit"]');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Guardando...';

        const params = { services: [] };
        const seen = new Set();
        form.querySelectorAll('[name^="svc_status_"]').forEach(el => {
            const lineId = el.name.replace('svc_status_', '');
            if (seen.has(lineId)) return;
            seen.add(lineId);
            params.services.push({
                id: parseInt(lineId, 10),
                status: el.value,
                notes: form.querySelector(`[name="svc_notes_${lineId}"]`)?.value || '',
            });
        });

        try {
            const result = await _rpc(`/my/workshop/order/${this._repairId}/technician/save`, params);
            if (result.ok) {
                _showWorkshopToast('Guardado correctamente');
                btn.innerHTML = '<i class="fa fa-check me-1"></i> Guardado';
                setTimeout(() => { btn.innerHTML = original; btn.disabled = false; }, 2500);
            } else {
                _showWorkshopToast(result.error || 'Error al guardar', 'danger');
                btn.innerHTML = original;
                btn.disabled = false;
            }
        } catch (err) {
            _showWorkshopToast(err.message || 'Error de red.', 'danger');
            btn.innerHTML = original;
            btn.disabled = false;
        }
    },
});

publicWidget.registry.WorkshopRoadTestSave = publicWidget.Widget.extend({
    selector: '#workshop-road-test-form',
    events: { 'submit': '_onSubmit' },
    start() {
        this._repairId = this.el.dataset.repairId;
        return this._super(...arguments);
    },
    async _onSubmit(ev) {
        ev.preventDefault();
        const form = this.el;
        const action = ev.submitter?.value || 'finish';
        const btn = ev.submitter || form.querySelector('[type="submit"]');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i> Guardando...';

        try {
            const result = await _rpc(`/my/workshop/order/${this._repairId}/road-test/save`, {
                road_test_result: form.querySelector('[name="road_test_result"]')?.value || '',
                action,
            });
            if (result.ok) {
                _showWorkshopToast(action === 'start' ? 'Prueba de ruta iniciada' : 'Prueba de ruta finalizada');
                if (result.reload) {
                    setTimeout(() => window.location.reload(), 1200);
                } else {
                    btn.innerHTML = original;
                    btn.disabled = false;
                }
            } else {
                _showWorkshopToast(result.error || 'Error al guardar', 'danger');
                btn.innerHTML = original;
                btn.disabled = false;
            }
        } catch (err) {
            _showWorkshopToast(err.message || 'Error de red.', 'danger');
            btn.innerHTML = original;
            btn.disabled = false;
        }
    },
});
