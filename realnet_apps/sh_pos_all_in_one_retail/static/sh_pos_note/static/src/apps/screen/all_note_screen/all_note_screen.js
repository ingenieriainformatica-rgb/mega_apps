/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { _t } from "@web/core/l10n/translation";


export class AllNoteScreen extends Component {
    static template = "sh_pos_all_in_one_retail.AllNoteScreen";

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }
    back() {
        this.pos.showScreen("ProductScreen");
    }
    get pre_defined_note_data(){
        let PreDefineNotes = [];
        PreDefineNotes = Object.values(this.pos.models["pos.note"].getAll())
        return PreDefineNotes
    }
    async onClickGlobalNoteScreen() {
        const payload = await makeAwaitable(this.dialog, TextInputPopup, {
            title: _t(" Add New Note"),
            rows: 4,
            is_create : true,
        });
        if(payload){
            await this.pos.models["pos.note"].create({"name" : payload})
            
            this.pos.showScreen("AllNoteScreen");
            await this.pos.data.create("pos.note", [{ 'name': payload }]);
        }

        
    }
    async delete_note(event) {
        const note_id = event.currentTarget.dataset.id;
        const note =  this.pos.models["pos.note"].get(note_id)
        await this.pos.models["pos.note"].delete(note)
        this.pos.showScreen("AllNoteScreen");
        this.pos.data.call("pos.note", "unlink", [[note_id]]);
    }
    
    async edit_note(event) {
        const row = event.currentTarget.closest("tr");        
        const inputNameElement = row.querySelector(".input_name");
        const noteNameElement = row.querySelector(".note_name");
        inputNameElement.classList.add("show_input_name");
        noteNameElement.classList.add("hide_note_name");
    }
    
    async save_note(event) {
        const row = event.currentTarget.closest("tr");
        row.querySelector(".input_name").classList.remove("show_input_name");
        row.querySelector(".note_name").classList.remove("hide_note_name");

        const note_id = event.currentTarget.dataset.id;
        const inputTagNameElement = row.querySelector(".input_tag_name");
        const new_note = inputTagNameElement.value;
        const note =  this.pos.models["pos.note"].get(note_id)
        await this.pos.models["pos.note"].update(note ,{"name" : new_note})
         await this.pos.data.write("pos.note",  [note_id], { 'name': new_note });
        this.pos.showScreen("AllNoteScreen");
    }

}
registry.category("pos_screens").add("AllNoteScreen", AllNoteScreen);
