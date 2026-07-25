# -*- coding: utf-8 -*-
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProductAttributeLineDeleteProtect(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_manager = cls.env.ref(
            "mega_product_attribute_line_delete_protect.group_product_attribute_line_manager"
        )

        # `product.group_product_manager` already grants full CRUD on the
        # attribute/value/line/PTAV models at the ACL level (see diagnosis),
        # so the unauthorized user MUST have it too: otherwise a plain
        # AccessError from the base ACL would make the test pass for the
        # wrong reason, without ever exercising our own group check.
        common_groups = (
            "base.group_user,product.group_product_manager,"
            "product.group_product_variant"
        )
        cls.unauthorized_user = new_test_user(
            cls.env, login="attr_unauthorized", groups=common_groups,
        )
        cls.authorized_user = new_test_user(
            cls.env, login="attr_authorized", groups=common_groups,
        )
        cls.authorized_user.write({
            "groups_id": [Command.link(cls.group_manager.id)],
        })

        cls.env_authorized = cls.env(user=cls.authorized_user)
        cls.env_unauthorized = cls.env(user=cls.unauthorized_user)

        # Fixtures are created through the authorized user on purpose: this
        # proves the setup itself does not trip the new protection.
        cls.attribute = cls.env_authorized["product.attribute"].create({
            "name": "Test Color",
            "create_variant": "always",
        })
        cls.value_red, cls.value_blue = cls.env_authorized[
            "product.attribute.value"
        ].create([
            {"name": "Red", "attribute_id": cls.attribute.id},
            {"name": "Blue", "attribute_id": cls.attribute.id},
        ])

        cls.product_tmpl = cls.env_authorized["product.template"].create({
            "name": "Test Protected Product",
            "list_price": 100.0,
            "attribute_line_ids": [Command.create({
                "attribute_id": cls.attribute.id,
                "value_ids": [Command.set(
                    [cls.value_red.id, cls.value_blue.id]
                )],
            })],
        })
        cls.ptal = cls.product_tmpl.attribute_line_ids
        cls.ptav = cls.ptal.product_template_value_ids

    # ------------------------------------------------------------------
    # Unauthorized user: read access must be preserved
    # ------------------------------------------------------------------
    def test_unauthorized_can_read_products_attributes_variants(self):
        tmpl = self.product_tmpl.with_user(self.unauthorized_user)
        self.assertEqual(tmpl.name, "Test Protected Product")
        self.assertTrue(tmpl.attribute_line_ids)
        self.assertTrue(tmpl.attribute_line_ids.value_ids)
        self.assertTrue(tmpl.product_variant_ids)
        self.env_unauthorized["product.attribute"].search(
            [("id", "=", self.attribute.id)]
        )
        self.env_unauthorized["product.attribute.value"].search(
            [("id", "=", self.value_red.id)]
        )

    # ------------------------------------------------------------------
    # Unauthorized user: product.template.attribute.line
    # ------------------------------------------------------------------
    def test_unauthorized_cannot_create_line_single(self):
        with self.assertRaises(UserError):
            self.env_unauthorized["product.template.attribute.line"].create({
                "product_tmpl_id": self.product_tmpl.id,
                "attribute_id": self.attribute.id,
                "value_ids": [Command.set([self.value_red.id])],
            })

    def test_unauthorized_cannot_create_line_multi(self):
        attribute2 = self.env_authorized["product.attribute"].create(
            {"name": "Test Size"}
        )
        value2 = self.env_authorized["product.attribute.value"].create(
            {"name": "Large", "attribute_id": attribute2.id}
        )
        with self.assertRaises(UserError):
            self.env_unauthorized["product.template.attribute.line"].create([
                {
                    "product_tmpl_id": self.product_tmpl.id,
                    "attribute_id": attribute2.id,
                    "value_ids": [Command.set([value2.id])],
                },
            ])

    def test_unauthorized_cannot_write_line_single(self):
        with self.assertRaises(UserError):
            self.ptal.with_user(self.unauthorized_user).write({
                "sequence": 99,
            })

    def test_unauthorized_cannot_reorder_or_edit_multi_lines(self):
        attribute2 = self.env_authorized["product.attribute"].create(
            {"name": "Test Material"}
        )
        value2 = self.env_authorized["product.attribute.value"].create(
            {"name": "Cotton", "attribute_id": attribute2.id}
        )
        line2 = self.env_authorized["product.template.attribute.line"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "attribute_id": attribute2.id,
            "value_ids": [Command.set([value2.id])],
        })
        lines = (self.ptal | line2).with_user(self.unauthorized_user)
        with self.assertRaises(UserError):
            lines.write({"sequence": 5})

    def test_unauthorized_cannot_add_remove_values(self):
        with self.assertRaises(UserError):
            self.ptal.with_user(self.unauthorized_user).write({
                "value_ids": [Command.unlink(self.value_blue.id)],
            })

    def test_unauthorized_cannot_unlink_line_single(self):
        with self.assertRaises(UserError):
            self.ptal.with_user(self.unauthorized_user).unlink()

    def test_unauthorized_cannot_unlink_line_multi(self):
        attribute2 = self.env_authorized["product.attribute"].create(
            {"name": "Test Fabric"}
        )
        value2 = self.env_authorized["product.attribute.value"].create(
            {"name": "Wool", "attribute_id": attribute2.id}
        )
        line2 = self.env_authorized["product.template.attribute.line"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "attribute_id": attribute2.id,
            "value_ids": [Command.set([value2.id])],
        })
        lines = (self.ptal | line2).with_user(self.unauthorized_user)
        with self.assertRaises(UserError):
            lines.unlink()

    # ------------------------------------------------------------------
    # Unauthorized user: product.attribute / product.attribute.value
    # ------------------------------------------------------------------
    def test_unauthorized_cannot_create_attribute(self):
        with self.assertRaises(UserError):
            self.env_unauthorized["product.attribute"].create(
                {"name": "Hack Attribute"}
            )

    def test_unauthorized_cannot_write_attribute(self):
        with self.assertRaises(UserError):
            self.attribute.with_user(self.unauthorized_user).write(
                {"name": "Renamed"}
            )

    def test_unauthorized_cannot_archive_attribute(self):
        with self.assertRaises(UserError):
            self.attribute.with_user(self.unauthorized_user).write(
                {"active": False}
            )

    def test_unauthorized_cannot_unlink_attribute(self):
        free_attribute = self.env_authorized["product.attribute"].create(
            {"name": "Unused Attribute"}
        )
        with self.assertRaises(UserError):
            free_attribute.with_user(self.unauthorized_user).unlink()

    def test_unauthorized_cannot_create_attribute_value(self):
        with self.assertRaises(UserError):
            self.env_unauthorized["product.attribute.value"].create({
                "name": "Hack Value", "attribute_id": self.attribute.id,
            })

    def test_unauthorized_cannot_write_attribute_value_multi(self):
        with self.assertRaises(UserError):
            (self.value_red | self.value_blue).with_user(
                self.unauthorized_user
            ).write({"default_extra_price": 1.0})

    def test_unauthorized_cannot_archive_attribute_value(self):
        with self.assertRaises(UserError):
            self.value_red.with_user(self.unauthorized_user).write(
                {"active": False}
            )

    def test_unauthorized_cannot_unlink_attribute_value(self):
        free_value = self.env_authorized["product.attribute.value"].create({
            "name": "Unused Value", "attribute_id": self.attribute.id,
        })
        with self.assertRaises(UserError):
            free_value.with_user(self.unauthorized_user).unlink()

    def test_unauthorized_cannot_write_ptav_configure_button(self):
        # This is exactly what the "Configure" button lets an authorized
        # user edit (price_extra / exclude_for on product.template.attribute.value).
        with self.assertRaises(UserError):
            self.ptav[:1].with_user(self.unauthorized_user).write(
                {"price_extra": 50.0}
            )

    def test_unauthorized_cannot_bypass_via_direct_orm_multi_records(self):
        # Simulates a raw RPC/ORM call touching several records at once,
        # bypassing any client-side widget entirely.
        with self.assertRaises(UserError):
            self.ptav.with_user(self.unauthorized_user).write(
                {"price_extra": 10.0}
            )

    # ------------------------------------------------------------------
    # Unauthorized user: unrelated product fields remain fully editable
    # ------------------------------------------------------------------
    def test_unauthorized_can_edit_general_product_fields(self):
        tmpl = self.product_tmpl.with_user(self.unauthorized_user)
        tmpl.write({"name": "Renamed By Unauthorized", "list_price": 250.0})
        self.assertEqual(tmpl.name, "Renamed By Unauthorized")
        self.assertEqual(tmpl.list_price, 250.0)

    # ------------------------------------------------------------------
    # Authorized user: full functionality preserved
    # ------------------------------------------------------------------
    def test_authorized_can_create_write_unlink_line_single(self):
        attribute2 = self.env_authorized["product.attribute"].create(
            {"name": "Auth Size"}
        )
        value2 = self.env_authorized["product.attribute.value"].create(
            {"name": "Medium", "attribute_id": attribute2.id}
        )
        line = self.env_authorized["product.template.attribute.line"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "attribute_id": attribute2.id,
            "value_ids": [Command.set([value2.id])],
        })
        self.assertTrue(line.exists())

        value3 = self.env_authorized["product.attribute.value"].create(
            {"name": "Small", "attribute_id": attribute2.id}
        )
        line.write({"value_ids": [Command.link(value3.id)]})
        self.assertIn(value3, line.value_ids)

        line.unlink()
        self.assertFalse(line.exists())

    def test_authorized_can_create_write_unlink_lines_multi(self):
        attribute_a = self.env_authorized["product.attribute"].create(
            {"name": "Multi A"}
        )
        attribute_b = self.env_authorized["product.attribute"].create(
            {"name": "Multi B"}
        )
        value_a = self.env_authorized["product.attribute.value"].create(
            {"name": "A1", "attribute_id": attribute_a.id}
        )
        value_b = self.env_authorized["product.attribute.value"].create(
            {"name": "B1", "attribute_id": attribute_b.id}
        )
        lines = self.env_authorized["product.template.attribute.line"].create([
            {
                "product_tmpl_id": self.product_tmpl.id,
                "attribute_id": attribute_a.id,
                "value_ids": [Command.set([value_a.id])],
            },
            {
                "product_tmpl_id": self.product_tmpl.id,
                "attribute_id": attribute_b.id,
                "value_ids": [Command.set([value_b.id])],
            },
        ])
        self.assertEqual(len(lines), 2)
        lines.write({"sequence": 20})
        lines.unlink()
        self.assertFalse(lines.exists())

    def test_authorized_can_manage_attributes_and_values(self):
        attribute = self.env_authorized["product.attribute"].create(
            {"name": "Auth Attribute"}
        )
        attribute.write({"name": "Auth Attribute Renamed"})
        value = self.env_authorized["product.attribute.value"].create(
            {"name": "Auth Value", "attribute_id": attribute.id}
        )
        value.write({"name": "Auth Value Renamed"})
        value.unlink()
        attribute.unlink()

    def test_authorized_can_configure_ptav(self):
        self.ptav[:1].with_user(self.authorized_user).write(
            {"price_extra": 15.0}
        )
        self.assertEqual(self.ptav[:1].price_extra, 15.0)

    def test_authorized_variant_generation_normal(self):
        variants_before = len(self.product_tmpl.product_variant_ids)
        attribute2 = self.env_authorized["product.attribute"].create(
            {"name": "Variant Attr"}
        )
        value2a = self.env_authorized["product.attribute.value"].create(
            {"name": "V1", "attribute_id": attribute2.id}
        )
        value2b = self.env_authorized["product.attribute.value"].create(
            {"name": "V2", "attribute_id": attribute2.id}
        )
        self.env_authorized["product.template.attribute.line"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "attribute_id": attribute2.id,
            "value_ids": [Command.set([value2a.id, value2b.id])],
        })
        self.product_tmpl.invalidate_recordset()
        self.assertGreater(
            len(self.product_tmpl.product_variant_ids), variants_before
        )

    # ------------------------------------------------------------------
    # View rendering: read-only tab for unauthorized, normal for authorized
    # ------------------------------------------------------------------
    def test_view_arch_locked_for_unauthorized(self):
        view_id = self.env.ref(
            "product.product_template_only_form_view"
        ).id
        arch = self.env_unauthorized["product.template"].get_view(
            view_id=view_id, view_type="form"
        )["arch"]
        self.assertIn('name="attribute_line_ids"', arch)
        self.assertIn('create="0"', arch)
        self.assertIn('delete="0"', arch)
        self.assertIn('no_open="1"', arch)
        self.assertNotIn("action_open_attribute_values", arch)
        self.assertNotIn('widget="handle"', arch)

    def test_view_arch_full_for_authorized(self):
        view_id = self.env.ref(
            "product.product_template_only_form_view"
        ).id
        arch = self.env_authorized["product.template"].get_view(
            view_id=view_id, view_type="form"
        )["arch"]
        self.assertIn('name="attribute_line_ids"', arch)
        self.assertIn("action_open_attribute_values", arch)
        self.assertIn('widget="handle"', arch)
        self.assertNotIn("no_open", arch)
