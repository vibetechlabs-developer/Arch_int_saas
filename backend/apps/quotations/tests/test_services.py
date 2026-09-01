from decimal import Decimal

from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.boq.services import BOQItemService, BOQSectionService, BOQService
from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory, ProductUnit
from apps.projects.models import Project
from apps.quotations.models import Quotation, QuotationStatus
from apps.quotations.services import QuotationService


class QuotationServiceCreateFromBOQTestCase(TestCase):
    """
    Unit test suite for QuotationService.create_quotation's "from BOQ" path
    (BE-039) -- `items` omitted entirely pulls the project's current BOQ
    includible items and BOQSummaryService's computed summary.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.boq = BOQService.get_or_create_boq_for_project(self.project)
        self.section = BOQSectionService.create_section(boq=self.boq, name="Flooring")

    def test_create_from_boq_copies_items_and_summary(self):
        BOQItemService.create_item(
            section=self.section, description="Tiling", quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT, rate=Decimal("50.00"), discount=Decimal("10.00"), tax=Decimal("18.00"),
        )
        BOQItemService.create_item(
            section=self.section, description="Skip me", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("999.00"), is_optional=True,
        )

        quotation = QuotationService.create_quotation(project=self.project)

        self.assertEqual(quotation.boq_id, self.boq.id)
        self.assertEqual(quotation.client_id, self.client_obj.id)
        self.assertEqual(quotation.status, QuotationStatus.DRAFT)
        self.assertEqual(quotation.version, 1)
        self.assertEqual(quotation.quote_number, "QT-000001")
        # base=500.00, discount=10% -> 50.00, after_discount=450.00, tax=18% -> 81.00.
        self.assertEqual(quotation.subtotal, Decimal("500.00"))
        self.assertEqual(quotation.discount, Decimal("50.00"))
        self.assertEqual(quotation.tax, Decimal("81.00"))
        self.assertEqual(quotation.total, Decimal("531.00"))

        items = list(quotation.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].description, "Tiling")
        self.assertEqual(items[0].amount, Decimal("500.00"))

    def test_create_from_boq_empty_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            QuotationService.create_quotation(project=self.project)

    def test_quote_number_sequential_per_company(self):
        BOQItemService.create_item(
            section=self.section, description="A", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        first = QuotationService.create_quotation(project=self.project)

        second_project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Second Project"
        )
        second_boq = BOQService.get_or_create_boq_for_project(second_project)
        second_section = BOQSectionService.create_section(boq=second_boq, name="General")
        BOQItemService.create_item(
            section=second_section, description="B", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        second = QuotationService.create_quotation(project=second_project)

        self.assertEqual(first.quote_number, "QT-000001")
        self.assertEqual(second.quote_number, "QT-000002")

    def test_quote_number_sequence_independent_per_company(self):
        BOQItemService.create_item(
            section=self.section, description="A", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        QuotationService.create_quotation(project=self.project)

        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_client = Client.objects.create(company=other_company, name="Other Client")
        other_project = Project.objects.create(
            company=other_company, client=other_client, name="Other Project"
        )
        other_boq = BOQService.get_or_create_boq_for_project(other_project)
        other_section = BOQSectionService.create_section(boq=other_boq, name="General")
        BOQItemService.create_item(
            section=other_section, description="B", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"),
        )
        other_quotation = QuotationService.create_quotation(project=other_project)

        self.assertEqual(other_quotation.quote_number, "QT-000001")


class QuotationServiceCreateManualTestCase(TestCase):
    """
    Unit test suite for QuotationService.create_quotation's manual path
    (BE-039) -- `items` explicitly supplied.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.product = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            unit=ProductUnit.SQFT,
            default_selling_rate=Decimal("120.00"),
        )

    def test_create_manual_free_text_items(self):
        quotation = QuotationService.create_quotation(
            project=self.project,
            items=[
                {"description": "Custom work", "quantity": Decimal("2.00"), "unit": "job", "rate": Decimal("100.00")},
            ],
            discount=Decimal("20.00"),
            tax=Decimal("10.00"),
        )

        self.assertIsNone(quotation.boq_id)
        self.assertEqual(quotation.subtotal, Decimal("200.00"))
        self.assertEqual(quotation.discount, Decimal("20.00"))
        self.assertEqual(quotation.tax, Decimal("10.00"))
        self.assertEqual(quotation.total, Decimal("190.00"))
        self.assertEqual(quotation.items.count(), 1)

    def test_create_manual_product_referenced_item_defaults_rate_and_unit(self):
        quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"product_id": self.product.id, "quantity": Decimal("3.00")}],
        )

        item = quotation.items.first()
        self.assertEqual(item.description, "Ceramic Tile")
        self.assertEqual(item.unit, ProductUnit.SQFT)
        self.assertEqual(item.rate, Decimal("120.00"))
        self.assertEqual(item.amount, Decimal("360.00"))

    def test_create_manual_missing_description_and_no_product_raises(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            QuotationService.create_quotation(
                project=self.project,
                items=[{"quantity": Decimal("1.00"), "rate": Decimal("10.00")}],
            )

    def test_create_manual_zero_quantity_raises(self):
        """
        validators.require_positive_quantity raises a plain ValueError, not
        drf_exceptions.ValidationError -- matching
        apps.boq.validators.require_section_name's own precedent
        (BOQSectionService's identical test,
        test_create_section_blank_name_rejected). This is a
        defense-in-depth guard for direct service calls; the HTTP-reachable
        path is protected by QuotationItemInputSerializer's own
        `min_value=0.01` on `quantity`, exercised at the view layer
        instead (see test_views.py).
        """
        with self.assertRaises(ValueError):
            QuotationService.create_quotation(
                project=self.project,
                items=[{"description": "X", "quantity": Decimal("0.00"), "rate": Decimal("10.00")}],
            )

    def test_create_manual_product_from_another_company_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_category = ProductCategory.objects.create(company=other_company, name="Other")
        other_subcategory = ProductSubcategory.objects.create(
            company=other_company, category=other_category, name="Other"
        )
        other_product = Product.objects.create(
            company=other_company, subcategory=other_subcategory, name="Foreign Product"
        )

        with self.assertRaises(drf_exceptions.NotFound):
            QuotationService.create_quotation(
                project=self.project,
                items=[{"product_id": other_product.id, "quantity": Decimal("1.00")}],
            )

    def test_create_manual_discount_tax_default_to_zero(self):
        quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("50.00")}],
        )
        self.assertEqual(quotation.discount, Decimal("0.00"))
        self.assertEqual(quotation.tax, Decimal("0.00"))
        self.assertEqual(quotation.total, Decimal("50.00"))


class QuotationServiceGetByIdTestCase(TestCase):
    """
    Unit test suite for QuotationService.get_quotation_by_id (BE-039).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("50.00")}],
        )

    def test_get_by_id_success(self):
        found = QuotationService.get_quotation_by_id(self.quotation.id)
        self.assertEqual(found.id, self.quotation.id)

    def test_get_by_id_cross_tenant_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        with self.assertRaises(drf_exceptions.NotFound):
            QuotationService.get_quotation_by_id(self.quotation.id, company_id=other_company.id)

    def test_get_by_id_nonexistent_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            QuotationService.get_quotation_by_id("00000000-0000-0000-0000-000000000000")


class QuotationServiceReviseTestCase(TestCase):
    """
    Unit test suite for QuotationService.revise_quotation (BE-040).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"description": "Original item", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
            discount=Decimal("10.00"),
            tax=Decimal("5.00"),
            terms="Original terms",
            notes="Original notes",
        )

    def test_revise_with_no_overrides_clones_source_version(self):
        revised = QuotationService.revise_quotation(self.quotation)

        self.assertEqual(revised.quote_number, self.quotation.quote_number)
        self.assertEqual(revised.version, 2)
        self.assertEqual(revised.status, QuotationStatus.DRAFT)
        self.assertEqual(revised.subtotal, self.quotation.subtotal)
        self.assertEqual(revised.discount, self.quotation.discount)
        self.assertEqual(revised.tax, self.quotation.tax)
        self.assertEqual(revised.total, self.quotation.total)
        self.assertEqual(revised.terms, "Original terms")
        self.assertEqual(revised.notes, "Original notes")
        self.assertEqual(revised.items.count(), 1)
        self.assertEqual(revised.items.first().description, "Original item")
        # Source version is untouched.
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.version, 1)
        self.assertEqual(self.quotation.status, QuotationStatus.DRAFT)

    def test_revise_overrides_only_supplied_fields(self):
        revised = QuotationService.revise_quotation(self.quotation, terms="New terms")

        self.assertEqual(revised.terms, "New terms")
        self.assertEqual(revised.notes, "Original notes")
        self.assertEqual(revised.discount, self.quotation.discount)

    def test_revise_with_new_items_recomputes_subtotal_and_clears_boq(self):
        revised = QuotationService.revise_quotation(
            self.quotation,
            items=[{"description": "New item", "quantity": Decimal("2.00"), "rate": Decimal("50.00")}],
        )

        self.assertIsNone(revised.boq_id)
        self.assertEqual(revised.subtotal, Decimal("100.00"))
        # discount/tax still carry over from the source version.
        self.assertEqual(revised.discount, Decimal("10.00"))
        self.assertEqual(revised.tax, Decimal("5.00"))
        self.assertEqual(revised.total, Decimal("95.00"))

    def test_revise_blocked_when_not_latest_version(self):
        QuotationService.revise_quotation(self.quotation)

        with self.assertRaises(ConflictError):
            QuotationService.revise_quotation(self.quotation)

    def test_revise_chain_of_two_versions(self):
        v2 = QuotationService.revise_quotation(self.quotation, terms="v2 terms")
        v3 = QuotationService.revise_quotation(v2, terms="v3 terms")

        self.assertEqual(v3.version, 3)
        self.assertEqual(v3.quote_number, self.quotation.quote_number)
        self.assertEqual(Quotation.objects.filter(quote_number=self.quotation.quote_number).count(), 3)


class QuotationServiceApprovalWorkflowTestCase(TestCase):
    """
    Unit test suite for QuotationService.send_quotation/approve_quotation/
    reject_quotation (BE-041).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )

    def test_send_transitions_draft_to_sent(self):
        updated = QuotationService.send_quotation(self.quotation)
        self.assertEqual(updated.status, QuotationStatus.SENT)

    def test_send_from_non_draft_raises_conflict(self):
        QuotationService.send_quotation(self.quotation)
        with self.assertRaises(ConflictError):
            QuotationService.send_quotation(self.quotation)

    def test_approve_transitions_sent_to_approved(self):
        QuotationService.send_quotation(self.quotation)
        self.quotation.refresh_from_db()
        updated = QuotationService.approve_quotation(self.quotation)
        self.assertEqual(updated.status, QuotationStatus.APPROVED)

    def test_approve_from_draft_raises_conflict(self):
        with self.assertRaises(ConflictError):
            QuotationService.approve_quotation(self.quotation)

    def test_reject_transitions_sent_to_rejected(self):
        QuotationService.send_quotation(self.quotation)
        self.quotation.refresh_from_db()
        updated = QuotationService.reject_quotation(self.quotation)
        self.assertEqual(updated.status, QuotationStatus.REJECTED)

    def test_reject_from_draft_raises_conflict(self):
        with self.assertRaises(ConflictError):
            QuotationService.reject_quotation(self.quotation)

    def test_send_blocked_when_not_latest_version(self):
        revised = QuotationService.revise_quotation(self.quotation)
        with self.assertRaises(ConflictError):
            QuotationService.send_quotation(self.quotation)
        # The latest version itself is unaffected by the stale guard.
        QuotationService.send_quotation(revised)

    def test_rejected_quotation_can_still_be_revised(self):
        QuotationService.send_quotation(self.quotation)
        self.quotation.refresh_from_db()
        QuotationService.reject_quotation(self.quotation)
        self.quotation.refresh_from_db()

        revised = QuotationService.revise_quotation(self.quotation)
        self.assertEqual(revised.status, QuotationStatus.DRAFT)
        self.assertEqual(revised.version, 2)
