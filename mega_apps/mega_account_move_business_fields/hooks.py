# -*- coding: utf-8 -*-
import logging

from psycopg2 import sql  #type:ignore

_logger = logging.getLogger(__name__)

MOVE_TABLE = "account_move"

CONCEPTO_OLD_COLUMN = "x_studio_concepto"
CONCEPTO_NEW_COLUMN = "mega_concepto"

DESCRIPCION_GENERAL_OLD_COLUMN = "x_studio_descripcin_1"
DESCRIPCION_GENERAL_NEW_COLUMN = "mega_descripcion_general"


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def _sync_column_from_studio(cr, table, old_column, new_column):
    """Copia old_column -> new_column en table.

    Solo completa new_column donde está vacío; nunca sobrescribe valores
    existentes ni toca old_column. Idempotente: ejecutarla varias veces
    produce el mismo resultado.
    """
    if not _column_exists(cr, table, old_column):
        _logger.info(
            "mega_account_move_business_fields: la columna %s.%s no existe, "
            "no hay nada que migrar.",
            table, old_column,
        )
        return

    if not _column_exists(cr, table, new_column):
        _logger.warning(
            "mega_account_move_business_fields: la columna %s.%s todavía no "
            "existe en el esquema, se omite la sincronización.",
            table, new_column,
        )
        return

    table_id = sql.Identifier(table)
    old_col = sql.Identifier(old_column)
    new_col = sql.Identifier(new_column)

    cr.execute(sql.SQL("""
        SELECT count(*) FROM {table}
        WHERE {old} IS NOT NULL AND btrim({old}) <> ''
          AND ({new} IS NULL OR btrim({new}) = '')
    """).format(table=table_id, old=old_col, new=new_col))
    candidates = cr.fetchone()[0]

    cr.execute(sql.SQL("""
        SELECT count(*) FROM {table}
        WHERE {old} IS NOT NULL AND btrim({old}) <> ''
          AND {new} IS NOT NULL AND btrim({new}) <> ''
          AND {new} <> {old}
    """).format(table=table_id, old=old_col, new=new_col))
    diffs_preexistentes = cr.fetchone()[0]

    cr.execute(sql.SQL("""
        UPDATE {table}
           SET {new} = {old}
         WHERE {old} IS NOT NULL AND btrim({old}) <> ''
           AND ({new} IS NULL OR btrim({new}) = '')
    """).format(table=table_id, old=old_col, new=new_col))
    updated = cr.rowcount

    _logger.info(
        "mega_account_move_business_fields: sync %s -> %s | candidatos=%s "
        "actualizados=%s registros_con_valor_distinto_preexistente=%s",
        old_column, new_column, candidates, updated, diffs_preexistentes,
    )


def sync_mega_concepto_from_studio(cr):
    """Copia x_studio_concepto -> mega_concepto en account_move.

    Se invoca tanto desde el post_init_hook (instalación limpia) como desde
    la migración post (actualización de un módulo ya instalado), para no
    duplicar lógica.
    """
    _sync_column_from_studio(cr, MOVE_TABLE, CONCEPTO_OLD_COLUMN, CONCEPTO_NEW_COLUMN)


def sync_mega_descripcion_general_from_studio(cr):
    """Copia x_studio_descripcin_1 -> mega_descripcion_general en account_move.

    Se invoca tanto desde el post_init_hook (instalación limpia) como desde
    la migración post (actualización de un módulo ya instalado), para no
    duplicar lógica.
    """
    _sync_column_from_studio(
        cr, MOVE_TABLE, DESCRIPCION_GENERAL_OLD_COLUMN, DESCRIPCION_GENERAL_NEW_COLUMN
    )
