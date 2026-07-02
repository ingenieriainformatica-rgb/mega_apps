/** @odoo-module */

import { Component } from "@odoo/owl";

/**
 * KpiBannerSkeleton: placeholder animado para las 6 tarjetas KPI
 * mientras los datos cargan por primera vez (isReady = false).
 */
export class KpiBannerSkeleton extends Component {
    static template = "mega_dashboard.KpiBannerSkeleton";
    static props = {};

    // Array de 6 items para generar las 6 tarjetas en el template
    get skeletonItems() {
        return [1, 2, 3, 4, 5, 6];
    }
}
