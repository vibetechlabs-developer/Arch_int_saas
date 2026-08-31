import uuid
from django.test import TestCase

from apps.boq.models import BOQ, BOQSection
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project


class BOQModelTestCase(TestCase):
    """
    Unit test suite for BOQ domain model (BE-035).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_boq_creation(self):
        boq = BOQ.objects.create(company=self.company, project=self.project)
        self.assertIsInstance(boq.id, uuid.UUID)
        self.assertEqual(boq.project, self.project)
        self.assertEqual(boq.status, "")
        self.assertFalse(boq.is_deleted)

    def test_boq_str_representation(self):
        boq = BOQ.objects.create(company=self.company, project=self.project)
        self.assertEqual(str(boq), f"BOQ for {self.project.name}")

    def test_boq_one_per_project_enforced(self):
        BOQ.objects.create(company=self.company, project=self.project)
        with self.assertRaises(Exception):
            BOQ.objects.create(company=self.company, project=self.project)

    def test_boq_requires_project(self):
        with self.assertRaises(Exception):
            BOQ.objects.create(company=self.company)

    def test_boq_cascade_delete_with_project(self):
        boq = BOQ.objects.create(company=self.company, project=self.project)
        boq_id = boq.id
        self.project.delete(hard=True)
        self.assertFalse(BOQ.all_objects.filter(id=boq_id).exists())

    def test_boq_soft_delete_lifecycle(self):
        boq = BOQ.objects.create(company=self.company, project=self.project)
        boq_id = boq.id

        boq.delete()
        self.assertTrue(boq.is_deleted)
        self.assertFalse(BOQ.objects.filter(id=boq_id).exists())
        self.assertTrue(BOQ.all_objects.filter(id=boq_id).exists())

        boq.restore()
        self.assertTrue(BOQ.objects.filter(id=boq_id).exists())


class BOQSectionModelTestCase(TestCase):
    """
    Unit test suite for BOQSection domain model (BE-035).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.boq = BOQ.objects.create(company=self.company, project=self.project)

    def test_section_creation(self):
        section = BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        self.assertIsInstance(section.id, uuid.UUID)
        self.assertEqual(section.name, "Flooring")
        self.assertEqual(section.sort_order, 1)
        self.assertFalse(section.is_deleted)

    def test_section_str_representation(self):
        section = BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        self.assertEqual(str(section), f"Flooring (BOQ {self.boq.id})")

    def test_section_default_ordering_by_sort_order(self):
        second = BOQSection.objects.create(boq=self.boq, name="Second", sort_order=2)
        first = BOQSection.objects.create(boq=self.boq, name="First", sort_order=1)

        sections = list(BOQSection.objects.filter(boq=self.boq))
        self.assertEqual(sections, [first, second])

    def test_section_requires_boq(self):
        with self.assertRaises(Exception):
            BOQSection.objects.create(name="Orphan Section", sort_order=1)

    def test_section_cascade_delete_with_boq(self):
        section = BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        section_id = section.id
        self.boq.delete(hard=True)
        self.assertFalse(BOQSection.all_objects.filter(id=section_id).exists())

    def test_section_soft_delete_lifecycle(self):
        section = BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        section_id = section.id

        section.delete()
        self.assertTrue(section.is_deleted)
        self.assertFalse(BOQSection.objects.filter(id=section_id).exists())
        self.assertTrue(BOQSection.all_objects.filter(id=section_id).exists())

        section.restore()
        self.assertTrue(BOQSection.objects.filter(id=section_id).exists())

    def test_boq_soft_delete_leaves_section_fk_untouched(self):
        section = BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        self.boq.delete()

        section.refresh_from_db()
        self.assertEqual(section.boq_id, self.boq.id)
        self.assertFalse(section.is_deleted)

    def test_reverse_accessor_from_boq(self):
        BOQSection.objects.create(boq=self.boq, name="Flooring", sort_order=1)
        self.assertEqual(self.boq.sections.count(), 1)
