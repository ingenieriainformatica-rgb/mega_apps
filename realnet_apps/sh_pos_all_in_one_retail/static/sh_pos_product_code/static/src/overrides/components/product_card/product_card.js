/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";

patch(ProductCard, {
    props: {
        ...ProductCard.props,
        default_code: { type: [Boolean, String, Number], optional: true },
    },
});
