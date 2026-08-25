import uuid
import time
from django.db import models
from django.test import TestCase

from apps.common.models import BaseModel, SoftDeleteModel, TimeStampedModel, UUIDModel


# Concrete test models for testing abstract abstractions
class ConcreteUUIDModel(UUIDModel):
    name = models.CharField(max_length=50, default="test")

    class Meta:
        app_label = "common"


class ConcreteTimeStampedModel(TimeStampedModel):
    name = models.CharField(max_length=50, default="test")

    class Meta:
        app_label = "common"


class ConcreteSoftDeleteModel(SoftDeleteModel):
    name = models.CharField(max_length=50, default="test")

    class Meta:
        app_label = "common"


class ConcreteBaseModel(BaseModel):
    title = models.CharField(max_length=50, default="item")

    class Meta:
        app_label = "common"


class CommonModelsTestCase(TestCase):
    """
    Test suite for Common abstract base models:
    - UUIDModel
    - TimeStampedModel
    - SoftDeleteModel
    - BaseModel
    """

    # --- UUIDModel Tests ---

    def test_uuid_model_generates_valid_uuid(self):
        instance = ConcreteUUIDModel.objects.create(name="uuid-test-1")
        self.assertIsInstance(instance.id, uuid.UUID)
        self.assertEqual(instance.pk, instance.id)

    def test_uuid_model_uniqueness(self):
        instance_1 = ConcreteUUIDModel.objects.create(name="uuid-1")
        instance_2 = ConcreteUUIDModel.objects.create(name="uuid-2")
        self.assertNotEqual(instance_1.id, instance_2.id)

    def test_abstract_model_flags(self):
        self.assertTrue(UUIDModel._meta.abstract)
        self.assertTrue(TimeStampedModel._meta.abstract)
        self.assertTrue(SoftDeleteModel._meta.abstract)
        self.assertTrue(BaseModel._meta.abstract)

    # --- TimeStampedModel Tests ---

    def test_timestamped_model_sets_created_and_updated_at(self):
        instance = ConcreteTimeStampedModel.objects.create(name="ts-test")
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.updated_at)
        self.assertAlmostEqual(
            instance.created_at.timestamp(),
            instance.updated_at.timestamp(),
            delta=1.0,
        )

    def test_timestamped_model_updates_updated_at_on_save(self):
        instance = ConcreteTimeStampedModel.objects.create(name="ts-update")
        original_created_at = instance.created_at
        original_updated_at = instance.updated_at

        # Sleep briefly to ensure timestamp distinction
        time.sleep(0.05)
        instance.name = "ts-updated"
        instance.save()

        instance.refresh_from_db()
        self.assertEqual(instance.created_at, original_created_at)
        self.assertGreater(instance.updated_at, original_updated_at)

    # --- SoftDeleteModel Tests ---

    def test_soft_delete_lifecycle(self):
        instance = ConcreteSoftDeleteModel.objects.create(name="soft-delete-1")
        self.assertIsNone(instance.deleted_at)
        self.assertFalse(instance.is_deleted)

        # Soft delete
        instance.delete()
        instance.refresh_from_db()

        self.assertIsNotNone(instance.deleted_at)
        self.assertTrue(instance.is_deleted)

        # Default manager hides soft-deleted record
        self.assertEqual(ConcreteSoftDeleteModel.objects.filter(id=instance.id).count(), 0)

        # all_objects includes soft-deleted record
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.filter(id=instance.id).count(), 1)

        # deleted_objects includes only soft-deleted record
        self.assertEqual(ConcreteSoftDeleteModel.deleted_objects.filter(id=instance.id).count(), 1)

        # Restore record
        instance.restore()
        instance.refresh_from_db()

        self.assertIsNone(instance.deleted_at)
        self.assertFalse(instance.is_deleted)
        self.assertEqual(ConcreteSoftDeleteModel.objects.filter(id=instance.id).count(), 1)
        self.assertEqual(ConcreteSoftDeleteModel.deleted_objects.filter(id=instance.id).count(), 0)

    def test_hard_delete_on_instance(self):
        instance = ConcreteSoftDeleteModel.objects.create(name="hard-delete-instance")
        instance_id = instance.id

        instance.hard_delete()
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.filter(id=instance_id).count(), 0)

    def test_delete_with_hard_flag(self):
        instance = ConcreteSoftDeleteModel.objects.create(name="delete-flag-hard")
        instance_id = instance.id

        instance.delete(hard=True)
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.filter(id=instance_id).count(), 0)

    def test_queryset_bulk_soft_delete_and_restore(self):
        item1 = ConcreteSoftDeleteModel.objects.create(name="bulk-1")
        item2 = ConcreteSoftDeleteModel.objects.create(name="bulk-2")
        item3 = ConcreteSoftDeleteModel.objects.create(name="bulk-3")

        # Soft delete queryset
        ConcreteSoftDeleteModel.objects.filter(id__in=[item1.id, item2.id]).delete()

        self.assertEqual(ConcreteSoftDeleteModel.objects.count(), 1)
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.count(), 3)
        self.assertEqual(ConcreteSoftDeleteModel.deleted_objects.count(), 2)

        # QuerySet alive and deleted filters
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.alive().count(), 1)
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.deleted().count(), 2)

        # Restore via queryset
        ConcreteSoftDeleteModel.deleted_objects.restore()
        self.assertEqual(ConcreteSoftDeleteModel.objects.count(), 3)
        self.assertEqual(ConcreteSoftDeleteModel.deleted_objects.count(), 0)

    def test_queryset_bulk_hard_delete(self):
        item1 = ConcreteSoftDeleteModel.objects.create(name="bulk-hard-1")
        item2 = ConcreteSoftDeleteModel.objects.create(name="bulk-hard-2")

        ConcreteSoftDeleteModel.objects.filter(id__in=[item1.id, item2.id]).hard_delete()
        self.assertEqual(ConcreteSoftDeleteModel.all_objects.count(), 0)

    # --- BaseModel Tests ---

    def test_base_model_combines_uuid_timestamp_softdelete(self):
        instance = ConcreteBaseModel.objects.create(title="base-item")

        # UUID
        self.assertIsInstance(instance.id, uuid.UUID)
        self.assertEqual(instance.pk, instance.id)

        # Timestamps
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.updated_at)

        # Soft Delete
        self.assertFalse(instance.is_deleted)
        instance.delete()

        self.assertTrue(instance.is_deleted)
        self.assertEqual(ConcreteBaseModel.objects.filter(id=instance.id).count(), 0)
        self.assertEqual(ConcreteBaseModel.all_objects.filter(id=instance.id).count(), 1)

        instance.restore()
        self.assertFalse(instance.is_deleted)
        self.assertEqual(ConcreteBaseModel.objects.filter(id=instance.id).count(), 1)
