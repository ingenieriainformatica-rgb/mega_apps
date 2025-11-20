from odoo import api, models
from ..const import CLAUSE_VARS  # ← única fuente

class ClauseVarsBridge(models.AbstractModel):
    _name = "industry_real_estate.clause_vars_bridge"
    _description = "Bridge: expose CLAUSE_VARS to JS"

    @api.model
    def get_clause_vars(self):
        # devuélvelo tal cual (lista) o si prefieres: {'vars': CLAUSE_VARS, 'version': 1}
        return CLAUSE_VARS
