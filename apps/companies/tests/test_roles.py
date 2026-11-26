"""Roles con permisos: los de sistema no se editan; un rol de empresa no lleva permisos de Hurgo."""

from django.contrib.auth.models import Group, User
from rest_framework.test import APITestCase

from enginedj.base.models import M_user_company

from apps.testing import build_world, run_workflow


class RoleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        build_world(cls)
        cls.uma_admin = User.objects.create_user("admin_uma", password="x-Clave-2026")
        cls.uma_admin.groups.add(Group.objects.get(name="admin_empresa"))
        M_user_company.objects.create(user_id=cls.uma_admin, company_id=cls.uma)

    def ok(self, result):
        self.assertTrue(result.ok, result.reason)
        return result.data

    def test_system_roles_are_listed_read_only(self):
        roles = {r["name"]: r for r in self.ok(run_workflow(self.admin, "roles.list"))}
        self.assertTrue(roles["despacho"]["is_system"])
        self.assertEqual((roles["comercial"]["scope"], roles["despacho"]["scope"]), ("company", "hurgo"))
        r = run_workflow(self.admin, "roles.save", {"id": roles["despacho"]["id"], "permissions": []})
        self.assertIn("no se editan", r.reason)
        self.assertFalse(run_workflow(self.dispatch, "roles.list").ok)  # solo administración

    def test_company_role_only_takes_company_permissions(self):
        r = run_workflow(self.admin, "roles.save", {
            "name": "bodeguero", "scope": "company", "permissions": ["orders.view_m_order", "orders.view_all_order"]})
        self.assertIn("orders.view_all_order", r.reason)
        role = self.ok(run_workflow(self.admin, "roles.save", {
            "name": "bodeguero", "label": "Bodeguero", "scope": "company",
            "permissions": ["orders.view_m_order", "orders.view_m_order_line"]}))
        self.assertEqual(role["permissions"], ["orders.view_m_order", "orders.view_m_order_line"])
        # El admin de empresa ya puede dar el rol nuevo a sus usuarios
        mine = self.ok(run_workflow(self.uma_admin, "companies.mine"))
        self.assertIn("bodeguero", [r["value"] for r in mine["roles"]])
        user = self.ok(run_workflow(self.uma_admin, "companies.user.save", {
            "company_id": self.uma.id, "username": "bodega_uma", "password": "Bodega-2026!x", "role": "bodeguero"}))
        self.assertEqual(user["role_label"], "Bodeguero")
        # Un rol de Hurgo no se puede dar desde la empresa
        hurgo_role = self.ok(run_workflow(self.admin, "roles.save", {
            "name": "auditor", "scope": "hurgo", "permissions": ["orders.view_all_order"]}))
        self.assertEqual(hurgo_role["scope"], "hurgo")
        self.assertIn("Rol no permitido", run_workflow(self.uma_admin, "companies.user.save", {
            "company_id": self.uma.id, "user_id": user["id"], "role": "auditor"}).reason)

    def test_admin_creates_hurgo_users_with_roles(self):
        created = self.ok(run_workflow(self.admin, "users.save", {
            "username": "despacho2", "password": "Despa-2026!x", "first_name": "Luis", "roles": ["despacho"]}))
        self.assertEqual(created["roles"], ["despacho"])
        self.assertTrue(User.objects.get(username="despacho2").has_perm("trips.build_trip"))
        self.assertIn("no existe", run_workflow(self.admin, "users.save", {
            "user_id": created["id"], "roles": ["inventado"]}).reason)
        self.assertIn("No puedes desactivarte", run_workflow(self.admin, "users.save", {
            "user_id": self.admin.id, "is_active": False}).reason)
