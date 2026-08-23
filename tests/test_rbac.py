import pytest
from django.contrib.auth import get_user_model
from common.exceptions import PermissionDeniedError
from accounts.models import RoleType
from accounts.rbac import (
    PERM_GRANT_BENEFITS,
    PERM_MANAGE_BENEFITS,
    PERM_MANAGE_UNITS,
    PERM_REGISTER_BENEFICIARIES,
    PERM_VIEW_DATA,
    check_user_unit_permission,
    get_user_accessible_units,
    has_unit_permission,
)
from accounts.services import membership_create
from organizational.models import OrganizationalUnit, UnitType

User = get_user_model()


@pytest.mark.django_db
class TestRBACAndHierarchy:
    @pytest.fixture
    def hierarchy(self):
        union = OrganizationalUnit.objects.create(name="União", unit_type=UnitType.UNION)
        conf = OrganizationalUnit.objects.create(name="Associação", unit_type=UnitType.CONFERENCE, parent=union)
        dist = OrganizationalUnit.objects.create(name="Distrito", unit_type=UnitType.DISTRICT, parent=conf)
        church1 = OrganizationalUnit.objects.create(name="Igreja 1", unit_type=UnitType.LOCAL_CHURCH, parent=dist)
        church2 = OrganizationalUnit.objects.create(name="Igreja 2", unit_type=UnitType.LOCAL_CHURCH, parent=dist)

        # Another branch
        other_dist = OrganizationalUnit.objects.create(
            name="Outro Distrito", unit_type=UnitType.DISTRICT, parent=conf
        )
        other_church = OrganizationalUnit.objects.create(
            name="Outra Igreja", unit_type=UnitType.LOCAL_CHURCH, parent=other_dist
        )

        return {
            "union": union,
            "conf": conf,
            "dist": dist,
            "church1": church1,
            "church2": church2,
            "other_dist": other_dist,
            "other_church": other_church,
        }

    def test_admin_staff_has_all_permissions_everywhere(self, hierarchy):
        admin = User.objects.create_user(username="admin", is_staff=True)

        for unit in hierarchy.values():
            assert has_unit_permission(admin, unit, PERM_MANAGE_UNITS)
            assert has_unit_permission(admin, unit, PERM_MANAGE_BENEFITS)
            assert has_unit_permission(admin, unit, PERM_REGISTER_BENEFICIARIES)
            assert has_unit_permission(admin, unit, PERM_GRANT_BENEFITS)
            assert has_unit_permission(admin, unit, PERM_VIEW_DATA)

    def test_pastor_permissions_inherited_to_child_units_only(self, hierarchy):
        pastor = User.objects.create_user(username="pastor_distrito")
        membership_create(user=pastor, unit=hierarchy["dist"], role=RoleType.PASTOR)

        # Pastor at District should have permissions in District and its churches (church1, church2)
        for target in [hierarchy["dist"], hierarchy["church1"], hierarchy["church2"]]:
            assert has_unit_permission(pastor, target, PERM_MANAGE_BENEFITS)
            assert has_unit_permission(pastor, target, PERM_REGISTER_BENEFICIARIES)
            assert has_unit_permission(pastor, target, PERM_GRANT_BENEFITS)
            assert has_unit_permission(pastor, target, PERM_VIEW_DATA)
            # Pastor CANNOT manage organizational units
            assert not has_unit_permission(pastor, target, PERM_MANAGE_UNITS)

        # Pastor should NOT have permissions in parent units (Conference, Union)
        assert not has_unit_permission(pastor, hierarchy["conf"], PERM_VIEW_DATA)
        assert not has_unit_permission(pastor, hierarchy["union"], PERM_VIEW_DATA)

        # Pastor should NOT have permissions in sibling district/church
        assert not has_unit_permission(pastor, hierarchy["other_dist"], PERM_VIEW_DATA)
        assert not has_unit_permission(pastor, hierarchy["other_church"], PERM_VIEW_DATA)

    def test_director_permissions(self, hierarchy):
        director = User.objects.create_user(username="diretor_igreja")
        membership_create(user=director, unit=hierarchy["church1"], role=RoleType.DIRECTOR)

        # In church1
        assert has_unit_permission(director, hierarchy["church1"], PERM_MANAGE_BENEFITS)
        assert has_unit_permission(director, hierarchy["church1"], PERM_REGISTER_BENEFICIARIES)
        assert has_unit_permission(director, hierarchy["church1"], PERM_GRANT_BENEFITS)
        assert has_unit_permission(director, hierarchy["church1"], PERM_VIEW_DATA)
        assert not has_unit_permission(director, hierarchy["church1"], PERM_MANAGE_UNITS)

        # In church2
        assert not has_unit_permission(director, hierarchy["church2"], PERM_VIEW_DATA)

    def test_secretary_is_view_only(self, hierarchy):
        secretary = User.objects.create_user(username="secretaria")
        membership_create(user=secretary, unit=hierarchy["dist"], role=RoleType.SECRETARY)

        # In dist and church1
        for target in [hierarchy["dist"], hierarchy["church1"]]:
            assert has_unit_permission(secretary, target, PERM_VIEW_DATA)
            assert not has_unit_permission(secretary, target, PERM_MANAGE_BENEFITS)
            assert not has_unit_permission(secretary, target, PERM_REGISTER_BENEFICIARIES)
            assert not has_unit_permission(secretary, target, PERM_GRANT_BENEFITS)
            assert not has_unit_permission(secretary, target, PERM_MANAGE_UNITS)

    def test_assistant_permissions(self, hierarchy):
        assistant = User.objects.create_user(username="auxiliar")
        membership_create(user=assistant, unit=hierarchy["church1"], role=RoleType.ASSISTANT)

        assert has_unit_permission(assistant, hierarchy["church1"], PERM_REGISTER_BENEFICIARIES)
        assert has_unit_permission(assistant, hierarchy["church1"], PERM_GRANT_BENEFITS)
        assert has_unit_permission(assistant, hierarchy["church1"], PERM_VIEW_DATA)
        # Forbidden from creating/managing benefits or units
        assert not has_unit_permission(assistant, hierarchy["church1"], PERM_MANAGE_BENEFITS)
        assert not has_unit_permission(assistant, hierarchy["church1"], PERM_MANAGE_UNITS)

    def test_check_user_unit_permission_raises_error(self, hierarchy):
        user = User.objects.create_user(username="regular_user")
        with pytest.raises(PermissionDeniedError, match="não possui a permissão"):
            check_user_unit_permission(user, hierarchy["church1"], PERM_GRANT_BENEFITS)

    def test_get_user_accessible_units(self, hierarchy):
        pastor = User.objects.create_user(username="pastor")
        membership_create(user=pastor, unit=hierarchy["dist"], role=RoleType.PASTOR)

        accessible = get_user_accessible_units(pastor)
        accessible_ids = set(accessible.values_list("id", flat=True))

        assert accessible_ids == {hierarchy["dist"].id, hierarchy["church1"].id, hierarchy["church2"].id}

    def test_membership_lifecycle_and_selectors(self, hierarchy):
        from accounts.selectors import membership_get, membership_list_by_unit, membership_list_by_user
        from accounts.services import membership_delete, membership_update

        admin = User.objects.create_user(username="admin_user", is_staff=True)
        user = User.objects.create_user(username="member_user")

        # Create
        m = membership_create(user=user, unit=hierarchy["church1"], role=RoleType.ASSISTANT, actor_user=admin)
        assert m.role == RoleType.ASSISTANT

        # Get & List
        assert membership_get(user, hierarchy["church1"]) == m
        assert m in membership_list_by_user(user)
        assert m in membership_list_by_unit(hierarchy["church1"])

        # Update
        membership_update(m, role=RoleType.DIRECTOR, actor_user=admin)
        m.refresh_from_db()
        assert m.role == RoleType.DIRECTOR

        # Delete
        membership_delete(m, actor_user=admin)
        assert membership_get(user, hierarchy["church1"]) is None

    def test_require_unit_permission_decorator(self, hierarchy):
        from accounts.rbac import require_unit_permission

        @require_unit_permission(PERM_MANAGE_BENEFITS, unit_kwarg="unit_id")
        def mock_view(request, unit_id):
            return "SUCCESS"

        admin = User.objects.create_user(username="admin_view", is_staff=True)
        secretary = User.objects.create_user(username="sec_view")
        membership_create(user=secretary, unit=hierarchy["church1"], role=RoleType.SECRETARY)

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        # Admin succeeds
        assert mock_view(DummyRequest(admin), unit_id=hierarchy["church1"].id) == "SUCCESS"

        # Secretary fails
        with pytest.raises(PermissionDeniedError):
            mock_view(DummyRequest(secretary), unit_id=hierarchy["church1"].id)

