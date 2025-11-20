/** @odoo-module */
/**
 * Slot Type Icons field widget: replaces many2one dropdown with 3 large icons
 * (Auto, Moto, Otro). Keeps writing to slot_type_id to preserve all logic.
 */

import { Component, xml, markup, onWillStart, onWillUpdateProps, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { useService } from '@web/core/utils/hooks';

class SlotTypeIcons extends Component {
    static template = xml`<div class="o_slot_type_icons d-flex gap-2 flex-wrap">
        <t t-foreach="state.icons" t-as="it" t-key="it.key">
            <button type="button" class="btn o_slot_icon_btn" t-attf-class="{{ props.readonly ? 'disabled' : '' }} {{ state.selectedId === it.id ? 'active' : '' }}" t-on-click="() => this.onPick(it)">
                <t t-out="it.svg"/>
                <span class="d-block small mt-1"><t t-esc="it.label"/></span>
            </button>
        </t>
    </div>`;
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService('orm');
        this.state = useState({ icons: [
            { key: 'auto', label: _t('Automovil'), svg: markup('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" width="28" height="28"><path d="M199.2 181.4L173.1 256L466.9 256L440.8 181.4C436.3 168.6 424.2 160 410.6 160L229.4 160C215.8 160 203.7 168.6 199.2 181.4zM103.6 260.8L138.8 160.3C152.3 121.8 188.6 96 229.4 96L410.6 96C451.4 96 487.7 121.8 501.2 160.3L536.4 260.8C559.6 270.4 576 293.3 576 320L576 512C576 529.7 561.7 544 544 544L512 544C494.3 544 480 529.7 480 512L480 480L160 480L160 512C160 529.7 145.7 544 128 544L96 544C78.3 544 64 529.7 64 512L64 320C64 293.3 80.4 270.4 103.6 260.8zM192 368C192 350.3 177.7 336 160 336C142.3 336 128 350.3 128 368C128 385.7 142.3 400 160 400C177.7 400 192 385.7 192 368zM480 400C497.7 400 512 385.7 512 368C512 350.3 497.7 336 480 336C462.3 336 448 350.3 448 368C448 385.7 462.3 400 480 400z"/></svg>') },
            { key: 'moto', label: _t('Moto'), svg: markup('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" width="28" height="28"><path d="M280 80C266.7 80 256 90.7 256 104C256 117.3 266.7 128 280 128L336.6 128L359.1 176.7L264 248C230.6 222.9 189 208 144 208L88 208C74.7 208 64 218.7 64 232C64 245.3 74.7 256 88 256L144 256C222.5 256 287.2 315.6 295.2 392L269.8 392C258.6 332.8 206.5 288 144 288C73.3 288 16 345.3 16 416C16 486.7 73.3 544 144 544C206.5 544 258.5 499.2 269.8 440L320 440C333.3 440 344 429.3 344 416L344 393.5C344 348.4 369.7 308.1 409.5 285.8L421.6 311.9C389.2 335.1 368.1 373.1 368.1 416C368.1 486.7 425.4 544 496.1 544C566.8 544 624.1 486.7 624.1 416C624.1 345.3 566.8 288 496.1 288C485.4 288 475.1 289.3 465.2 291.8L433.8 224L488 224C501.3 224 512 213.3 512 200L512 152C512 138.7 501.3 128 488 128L434.7 128C427.8 128 421 130.2 415.5 134.4L398.4 147.2L373.8 93.9C369.9 85.4 361.4 80 352 80L280 80zM445.8 364.4L474.2 426C479.8 438 494 443.3 506 437.7C518 432.1 523.3 417.9 517.7 405.9L489.2 344.3C491.4 344.1 493.6 344 495.9 344C535.7 344 567.9 376.2 567.9 416C567.9 455.8 535.7 488 495.9 488C456.1 488 423.9 455.8 423.9 416C423.9 395.8 432.2 377.5 445.7 364.4zM144 488C104.2 488 72 455.8 72 416C72 376.2 104.2 344 144 344C175.3 344 202 364 211.9 392L144 392C130.7 392 120 402.7 120 416C120 429.3 130.7 440 144 440L211.9 440C202 468 175.3 488 144 488z"/></svg>') },
            { key: 'other', label: _t('Otro'), svg: markup('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" width="28" height="28"><path d="M352 128C352 110.3 337.7 96 320 96C302.3 96 288 110.3 288 128L288 288L128 288C110.3 288 96 302.3 96 320C96 337.7 110.3 352 128 352L288 352L288 512C288 529.7 302.3 544 320 544C337.7 544 352 529.7 352 512L352 352L512 352C529.7 352 544 337.7 544 320C544 302.3 529.7 288 512 288L352 288L352 128z"/></svg>') },
        ], selectedId: null, pendingKey: null});

        onWillStart(async () => {
            // load default ids to enable active state highlighting
            const res = await this.orm.call('slot.type', 'get_or_create_defaults', [], {});
            this.state.icons = this.state.icons.map((x) => ({ ...x, id: res[x.key]?.id }));
            const current = this._currentId();
            this.state.selectedId = current || null;
        });

        onWillUpdateProps(() => {
            this.state.selectedId = this._currentId();
        });
    }

    _currentId() {
        const val = this.props.record.data[this.props.name];
        return Array.isArray(val) ? val[0] : val;
    }

    onPick(item) {
        if (this.props.readonly) {
            return;
        }
        // Do not return the promise to the event system; update after resolution
        this.orm
            .call('slot.type', 'get_or_create_defaults', [], {})
            .then((res) => {
                const target = res[item.key];
                if (target && target.id) {
                    const pair = [target.id, target.display_name || item.label];
                    this.props.record.update({ [this.props.name]: pair });
                    this.state.selectedId = target.id;
                }
            })
            .catch(() => {});
    }
}

registry.category('fields').add('slot_type_icons', {
    component: SlotTypeIcons,
    displayName: _t('Slot Type Icons'),
    supportedTypes: ['many2one'],
    isEmpty: (record, fieldName) => !record.data[fieldName],
    extractProps: () => ({}),
});
