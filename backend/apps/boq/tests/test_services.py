import uuid
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.boq.models import BOQ, BOQSection
from apps.boq.services import BOQSectionService, BOQService
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project


class BOQServiceTestCase(TestCase):
    """
    Unit test suite for BOQService business logic (BE-035).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Client One")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_get_or_create_creates_on_first_call(self):
        boq = BOQService.get_or_create_boq_for_project(self.project)
        self.assertEqual(boq.project_id, self.project.id)
        self.assertEqual(boq.company_id, self.company.id)

    def test_get_or_create_is_idempotent(self):
        first = BOQService.get_or_create_boq_for_project(self.project)
        second = BOQService.get_or_create_boq_for_project(self.project)
        self.assertEqual(first.id, second.id)
        self.assertEqual(BOQ.objects.filter(project=self.project).count(), 1)

    def test_get_or_create_writes_audit_log_only_on_creation(self):
        BOQService.get_or_create_boq_for_project(self.project)
        BOQService.get_or_create_boq_for_project(self.project)

        entries = AuditLog.objects.filter(entity_type="boq", action="create")
        self.assertEqual(entries.count(), 1)


class BOQSectionServiceTestCase(TestCase):
    """
    Unit test suite for BOQSectionService business logic (BE-035).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

        self.boq1 = BOQService.get_or_create_boq_for_project(self.project1)
        self.boq2 = BOQService.get_or_create_boq_for_project(self.project2)

    def test_create_section_success(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        self.assertEqual(section.name, "Flooring")
        self.assertEqual(section.boq_id, self.boq1.id)
        self.assertEqual(section.sort_order, 1)

    def test_create_section_auto_increments_sort_order(self):
        first = BOQSectionService.create_section(boq=self.boq1, name="First")
        second = BOQSectionService.create_section(boq=self.boq1, name="Second")
        self.assertEqual(first.sort_order, 1)
        self.assertEqual(second.sort_order, 2)

    def test_create_section_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            BOQSectionService.create_section(boq=self.boq1, name="   ")

    def test_list_sections(self):
        BOQSectionService.create_section(boq=self.boq1, name="First")
        BOQSectionService.create_section(boq=self.boq1, name="Second")
        BOQSectionService.create_section(boq=self.boq2, name="Other BOQ Section")

        sections = BOQSectionService.list_sections(self.boq1)
        self.assertEqual(sections.count(), 2)

    def test_get_section_by_id_success(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        fetched = BOQSectionService.get_section_by_id(section.id)
        self.assertEqual(fetched.id, section.id)

    def test_get_section_by_id_cross_tenant_raises_not_found(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        with self.assertRaises(drf_exceptions.NotFound):
            BOQSectionService.get_section_by_id(section.id, company_id=self.company2.id)

    def test_update_section_success(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        updated = BOQSectionService.update_section(
            section_id=section.id, validated_data={"name": "Renamed"}
        )
        self.assertEqual(updated.name, "Renamed")

    def test_update_section_cross_tenant_raises_not_found(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        with self.assertRaises(drf_exceptions.NotFound):
            BOQSectionService.update_section(
                section_id=section.id,
                validated_data={"name": "Hacked"},
                company_id=self.company2.id,
            )

    def test_soft_delete_section(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        section_id = section.id
        BOQSectionService.soft_delete_section(section_id)

        with self.assertRaises(drf_exceptions.NotFound):
            BOQSectionService.get_section_by_id(section_id)

        self.assertTrue(BOQSection.all_objects.filter(id=section_id).exists())

    def test_create_section_writes_audit_log_entry(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Audited Section")
        entry = AuditLog.objects.get(
            entity_type="boq_section", entity_id=section.id, action="create"
        )
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertEqual(entry.after_state["name"], "Audited Section")

    def test_update_section_writes_audit_log_entry(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Original")
        BOQSectionService.update_section(section_id=section.id, validated_data={"name": "Renamed"})

        entry = AuditLog.objects.filter(
            entity_type="boq_section", entity_id=section.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Original")
        self.assertEqual(entry.after_state["name"], "Renamed")

    def test_soft_delete_section_writes_audit_log_entry(self):
        section = BOQSectionService.create_section(boq=self.boq1, name="Flooring")
        section_id = section.id
        BOQSectionService.soft_delete_section(section_id)

        entry = AuditLog.objects.get(
            entity_type="boq_section", entity_id=section_id, action="delete"
        )
        self.assertEqual(entry.before_state["name"], "Flooring")
        self.assertIsNone(entry.after_state)
