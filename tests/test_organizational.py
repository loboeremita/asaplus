import pytest
from common.exceptions import BusinessRuleViolationError, ValidationError
from organizational.models import UnitType
from organizational.selectors import (
    unit_get_ancestor_ids,
    unit_get_by_id,
    unit_get_descendants,
    unit_get_tree,
)
from organizational.services import unit_create, unit_update


@pytest.mark.django_db
class TestOrganizationalHierarchy:
    def test_create_hierarchical_units(self):
        union = unit_create(name="União Leste Brasileira", unit_type=UnitType.UNION, code="ULB")
        conference = unit_create(
            name="Associação Bahia",
            unit_type=UnitType.CONFERENCE,
            parent=union,
            code="AB",
        )
        district = unit_create(
            name="Distrito Central de Salvador",
            unit_type=UnitType.DISTRICT,
            parent=conference,
            code="D-CENTRAL",
        )
        church1 = unit_create(
            name="Igreja Central",
            unit_type=UnitType.LOCAL_CHURCH,
            parent=district,
            code="IG-CENTRAL",
        )
        church2 = unit_create(
            name="Igreja da Liberdade",
            unit_type=UnitType.LOCAL_CHURCH,
            parent=district,
            code="IG-LIB",
        )

        assert union.parent is None
        assert conference.parent == union
        assert district.parent == conference
        assert church1.parent == district
        assert church2.parent == district

        # Ancestor traversal
        ancestor_ids = church1.get_ancestor_ids(include_self=True)
        assert ancestor_ids == {church1.id, district.id, conference.id, union.id}

        ancestors = church1.get_ancestors(include_self=True)
        assert [u.id for u in ancestors] == [church1.id, district.id, conference.id, union.id]

        # Descendant traversal
        descendant_ids = union.get_descendant_ids(include_self=True)
        assert descendant_ids == {union.id, conference.id, district.id, church1.id, church2.id}

        conf_descendant_ids = conference.get_descendant_ids(include_self=False)
        assert conf_descendant_ids == {district.id, church1.id, church2.id}

        # Hierarchy helper checks
        assert union.is_ancestor_of(church1)
        assert not church1.is_ancestor_of(union)
        assert church1.is_descendant_of(union)
        assert not union.is_descendant_of(church1)

    def test_prevent_cycle_on_update(self):
        union = unit_create(name="União", unit_type=UnitType.UNION)
        conf = unit_create(name="Associação", unit_type=UnitType.CONFERENCE, parent=union)
        dist = unit_create(name="Distrito", unit_type=UnitType.DISTRICT, parent=conf)
        church = unit_create(name="Igreja", unit_type=UnitType.LOCAL_CHURCH, parent=dist)

        # Trying to make union a child of church (its descendant) should fail
        with pytest.raises(BusinessRuleViolationError, match="descendentes"):
            unit_update(union, parent=church)

        # Trying to make a unit its own parent should fail
        with pytest.raises(BusinessRuleViolationError, match="si mesma"):
            unit_update(dist, parent=dist)

    def test_unique_code_validation(self):
        unit_create(name="Igreja A", code="UNIQUE-01")
        with pytest.raises(ValidationError, match="Já existe uma unidade cadastrada com o código"):
            unit_create(name="Igreja B", code="UNIQUE-01")

    def test_selectors_and_tree_generation(self):
        union = unit_create(name="União", unit_type=UnitType.UNION)
        conf = unit_create(name="Associação", unit_type=UnitType.CONFERENCE, parent=union)
        church = unit_create(name="Igreja", unit_type=UnitType.LOCAL_CHURCH, parent=conf)

        tree = unit_get_tree(root_unit=union)
        assert len(tree) == 1
        assert tree[0]["name"] == "União"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "Associação"
        assert len(tree[0]["children"][0]["children"]) == 1
        assert tree[0]["children"][0]["children"][0]["name"] == "Igreja"

        assert unit_get_by_id(church.id) == church
        assert conf.id in unit_get_ancestor_ids(church)
        assert church in unit_get_descendants(union)

    def test_unit_update_and_delete(self):
        from organizational.selectors import unit_list_active
        from organizational.services import unit_delete

        unit = unit_create(name="Unidade Temporária", unit_type=UnitType.LOCAL_CHURCH, code="TEMP-01")
        assert unit in unit_list_active()

        # Update
        updated = unit_update(unit, name="Unidade Atualizada", is_active=False)
        assert updated.name == "Unidade Atualizada"
        assert updated.is_active is False
        assert updated not in unit_list_active()

        # Delete
        unit_delete(unit)
        assert unit_get_by_id(unit.id) is None

