# -*- coding: utf-8 -*-
import logging

from psycopg2 import sql  #type:ignore

_logger = logging.getLogger(__name__)

MOVE_TABLE = "account_move"
OLD_COLUMN = "x_studio_concepto"
NEW_COLUMN = "mega_concepto"


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def sync_mega_concepto_from_studio(cr):
    """Copia x_studio_concepto -> mega_concepto en account_move.

    Solo completa mega_concepto donde está vacío; nunca sobrescribe valores
    existentes ni toca x_studio_concepto. Idempotente: ejecutarla varias
    veces produce el mismo resultado. Se invoca tanto desde el
    post_init_hook (instalación limpia) como desde la migración post
    (actualización de un módulo ya instalado), para no duplicar lógica.
    """
    if not _column_exists(cr, MOVE_TABLE, OLD_COLUMN):
        _logger.info(
            "mega_account_move_business_fields: la columna %s.%s no existe, "
            "no hay nada que migrar.",
            MOVE_TABLE, OLD_COLUMN,
        )
        return

    if not _column_exists(cr, MOVE_TABLE, NEW_COLUMN):
        _logger.warning(
            "mega_account_move_business_fields: la columna %s.%s todavía no "
            "existe en el esquema, se omite la sincronización.",
            MOVE_TABLE, NEW_COLUMN,
        )
        return

    table = sql.Identifier(MOVE_TABLE)
    old_col = sql.Identifier(OLD_COLUMN)
    new_col = sql.Identifier(NEW_COLUMN)

    cr.execute(sql.SQL("""
        SELECT count(*) FROM {table}
        WHERE {old} IS NOT NULL AND btrim({old}) <> ''
          AND ({new} IS NULL OR btrim({new}) = '')
    """).format(table=table, old=old_col, new=new_col))
    candidates = cr.fetchone()[0]

    cr.execute(sql.SQL("""
        SELECT count(*) FROM {table}
        WHERE {old} IS NOT NULL AND btrim({old}) <> ''
          AND {new} IS NOT NULL AND btrim({new}) <> ''
          AND {new} <> {old}
    """).format(table=table, old=old_col, new=new_col))
    diffs_preexistentes = cr.fetchone()[0]

    cr.execute(sql.SQL("""
        UPDATE {table}
           SET {new} = {old}
         WHERE {old} IS NOT NULL AND btrim({old}) <> ''
           AND ({new} IS NULL OR btrim({new}) = '')
    """).format(table=table, old=old_col, new=new_col))
    updated = cr.rowcount

    _logger.info(
        "mega_account_move_business_fields: sync x_studio_concepto -> "
        "mega_concepto | candidatos=%s actualizados=%s "
        "registros_con_valor_distinto_preexistente=%s",
        candidates, updated, diffs_preexistentes,
    )
