/** @odoo-module **/

import { CrmKanbanDynamicGroupList, CrmKanbanModel } from "@crm/views/crm_kanban/crm_kanban_model";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

async function openLostStageWizard(env, leadId, targetStageId, onClose) {
    if (!leadId || !targetStageId) {
        env.notification?.add(
            "No se pudo abrir el asistente: falta la oportunidad o la etapa destino.",
            { type: "danger" }
        );
        return true;
    }
    const action = await env.orm.call(
        "crm.lead",
        "action_open_lost_stage_reason_wizard",
        [[leadId], targetStageId]
    );
    if (!action) {
        return false;
    }
    await env.action.doAction(
        {
            ...action,
            view_mode: action.view_mode || "form",
            views: action.views || [[false, "form"]],
        },
        { onClose }
    );
    return true;
}

patch(CrmKanbanModel.prototype, {
    setup(params, services) {
        super.setup(...arguments);
        this.action = services.action;
        this.notification = services.notification;
    },
});

patch(CrmKanbanDynamicGroupList.prototype, {
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        const sourceGroup = this.groups.find((group) => group.id === dataGroupId);
        const targetGroup = this.groups.find((group) => group.id === targetGroupId);

        if (
            dataGroupId !== targetGroupId &&
            sourceGroup &&
            targetGroup &&
            sourceGroup.groupByField.name === "stage_id" &&
            this.model.root.resModel === "crm.lead"
        ) {
            const sourceRecord = sourceGroup.list.records.find((record) => record.id === dataRecordId);
            const opened = await openLostStageWizard(
                this.model,
                sourceRecord?.resId,
                targetGroup.value,
                async () => {
                    await this.model.load();
                    this.model.notify();
                }
            );
            if (opened) {
                return;
            }
        }

        return super.moveRecord(...arguments);
    },
});

patch(StatusBarField.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
    },

    async selectItem(item) {
        const { name, record } = this.props;
        if (
            record.resModel === "crm.lead" &&
            name === "stage_id" &&
            this.field.type === "many2one" &&
            record.resId &&
            item.value &&
            !item.isSelected
        ) {
            const opened = await openLostStageWizard(
                this,
                record.resId,
                item.value,
                async () => {
                    await record.model.load();
                    record.model.notify();
                }
            );
            if (opened) {
                return;
            }
        }

        return super.selectItem(...arguments);
    },
});
