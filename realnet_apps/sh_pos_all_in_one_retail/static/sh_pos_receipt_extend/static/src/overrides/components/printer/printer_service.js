/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PrinterService } from "@point_of_sale/app/printer/printer_service";
import { loadAllImages } from "@point_of_sale/utils";

patch(PrinterService.prototype, {
  setup() {
    super.setup(...arguments);
  },

async print(component, props, options) {
  const el = await this.renderer.toHtml(component, props);
  if(this && this.hardware_proxy && this.hardware_proxy.pos && this.hardware_proxy.pos.receipt_type == false){
    super.print(...arguments)
  }
  else if(this && this.hardware_proxy && this.hardware_proxy.pos && this.hardware_proxy.pos.receipt_type == "a3_size"){
    try {
      await loadAllImages($(".a3_size_receipt")[0]);
      return await this.printHtml($(".a3_size_receipt")[0], options);
    } catch (error) {
      console.error("Images could not be loaded correctly", error);
    }
  }
  else if(this && this.hardware_proxy && this.hardware_proxy.pos && this.hardware_proxy.pos.receipt_type == "a4_size"){
    try {
      await loadAllImages($(".a4_size_receipt")[0]);
      return await this.printHtml($(".a4_size_receipt")[0], options);
    } catch (error) {
      console.error("Images could not be loaded correctly", error);
    }
  }
  else if(this && this.hardware_proxy && this.hardware_proxy.pos && this.hardware_proxy.pos.receipt_type == "a5_size"){
    try {
      await loadAllImages($(".a5_size_receipt")[0]);
    return await this.printHtml($(".a5_size_receipt")[0], options);
    } catch (error) {
      console.error("Images could not be loaded correctly", error);
    }
  }else{
    super.print(...arguments)
  }
}
});
