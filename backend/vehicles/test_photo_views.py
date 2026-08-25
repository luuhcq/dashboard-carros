import io
import os
import tempfile
import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from vehicles.models import Vehicle, VehiclePhoto


def make_vehicle(company, **overrides):
    defaults = {
        'company': company,
        'brand': 'Marca',
        'model': 'Modelo',
        'purchase_date': date(2026, 1, 1),
        'purchase_price': Decimal('50000.00'),
    }
    defaults.update(overrides)
    return Vehicle.objects.create(**defaults)


def make_uploaded_image(name='photo.jpg', size=(60, 40), color='blue', exif_bytes=None):
    buffer = io.BytesIO()
    img = Image.new('RGB', size, color=color)
    if exif_bytes is not None:
        img.save(buffer, format='JPEG', exif=exif_bytes)
    else:
        img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


class PhotoAPITestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root_dir = tempfile.TemporaryDirectory()
        cls._media_root_override = override_settings(MEDIA_ROOT=cls._media_root_dir.name)
        cls._media_root_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_root_override.disable()
        cls._media_root_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='revenda', password='S3nhaForte!23'
        )
        response = self.client.post(
            reverse('auth-login'),
            {'username': 'revenda', 'password': 'S3nhaForte!23'},
            format='json',
        )
        assert response.status_code == 200, response.data

        self.company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(self.company)

    def photo_list_url(self, vehicle=None):
        return reverse('vehicle-photo-list', kwargs={'vehicle_id': (vehicle or self.vehicle).pk})

    def photo_detail_url(self, photo):
        return reverse('photo-detail', kwargs={'photo_id': photo.pk})


class UnauthenticatedAccessTests(APITestCase):
    def setUp(self):
        company = Company.objects.create(name='Empresa de teste')
        self.vehicle = make_vehicle(company)

    def test_list_requires_authentication(self):
        url = reverse('vehicle-photo-list', kwargs={'vehicle_id': self.vehicle.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        url = reverse('vehicle-photo-list', kwargs={'vehicle_id': self.vehicle.pk})
        response = self.client.post(url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_requires_authentication(self):
        url = reverse('photo-detail', kwargs={'photo_id': uuid.uuid4()})
        response = self.client.patch(url, {'position': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_requires_authentication(self):
        url = reverse('photo-detail', kwargs={'photo_id': uuid.uuid4()})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PhotoUploadTests(PhotoAPITestCase):
    def test_upload_links_photo_to_vehicle_from_url(self):
        response = self.client.post(
            self.photo_list_url(),
            {'image': make_uploaded_image(), 'position': 0},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        photo = VehiclePhoto.objects.get(pk=response.data['id'])
        self.assertEqual(photo.vehicle_id, self.vehicle.pk)

    def test_upload_ignores_vehicle_in_body_uses_url_instead(self):
        other_vehicle = make_vehicle(self.company, brand='Outro')

        response = self.client.post(
            self.photo_list_url(self.vehicle),
            {
                'image': make_uploaded_image(),
                'position': 0,
                'vehicle': str(other_vehicle.pk),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        photo = VehiclePhoto.objects.get(pk=response.data['id'])
        self.assertEqual(photo.vehicle_id, self.vehicle.pk)
        self.assertNotEqual(photo.vehicle_id, other_vehicle.pk)

    def test_upload_for_nonexistent_vehicle_returns_404(self):
        url = reverse('vehicle-photo-list', kwargs={'vehicle_id': uuid.uuid4()})
        response = self.client.post(
            url, {'image': make_uploaded_image(), 'position': 0}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(VehiclePhoto.objects.count(), 0)

    def test_upload_generates_thumbnail_and_strips_exif_end_to_end(self):
        """Reaproveita a verificação do Prompt 10, agora via API real, não
        chamando o model diretamente."""
        exif = Image.Exif()
        exif[0x010F] = 'Fabricante de teste'  # tag Make
        exif[0x0110] = 'Camera de teste'  # tag Model
        exif_bytes = exif.tobytes()

        uploaded = make_uploaded_image('com_exif.jpg', size=(800, 600), exif_bytes=exif_bytes)
        uploaded.seek(0)
        sanity_check = Image.open(uploaded)
        self.assertTrue(len(sanity_check.getexif()) > 0)
        uploaded.seek(0)

        response = self.client.post(
            self.photo_list_url(), {'image': uploaded, 'position': 0}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        photo = VehiclePhoto.objects.get(pk=response.data['id'])
        self.assertTrue(photo.thumbnail.name)

        photo.image.open()
        persisted_image = Image.open(photo.image)
        self.assertEqual(len(persisted_image.getexif()), 0)

        photo.thumbnail.open()
        thumb_image = Image.open(photo.thumbnail)
        self.assertLessEqual(thumb_image.width, 400)
        self.assertLessEqual(thumb_image.height, 400)


class PhotoListTests(PhotoAPITestCase):
    def test_list_ordered_by_position(self):
        third = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('c.jpg'), position=2
        )
        first = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), position=0
        )
        second = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('b.jpg'), position=1
        )

        response = self.client.get(self.photo_list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(first.pk), str(second.pk), str(third.pk)])

    def test_list_for_nonexistent_vehicle_returns_404(self):
        url = reverse('vehicle-photo-list', kwargs={'vehicle_id': uuid.uuid4()})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PhotoPatchTests(PhotoAPITestCase):
    def test_patch_swaps_cover_and_unmarks_previous(self):
        """Mesma garantia do Prompt 10, agora via API."""
        photo1 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), is_cover=True
        )
        photo2 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('b.jpg'), is_cover=False
        )

        response = self.client.patch(
            self.photo_detail_url(photo2), {'is_cover': True}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        photo1.refresh_from_db()
        photo2.refresh_from_db()
        self.assertFalse(photo1.is_cover)
        self.assertTrue(photo2.is_cover)

    def test_patch_reorders_multiple_photos(self):
        photo1 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), position=0
        )
        photo2 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('b.jpg'), position=1
        )
        photo3 = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('c.jpg'), position=2
        )

        # inverte a ordem: 1 -> 2 -> 3 vira 3 -> 2 -> 1
        self.client.patch(self.photo_detail_url(photo1), {'position': 2}, format='json')
        self.client.patch(self.photo_detail_url(photo3), {'position': 0}, format='json')

        response = self.client.get(self.photo_list_url())
        ids = [row['id'] for row in response.data]
        self.assertEqual(ids, [str(photo3.pk), str(photo2.pk), str(photo1.pk)])

    def test_patch_rejects_image_field_entirely(self):
        """image é um campo normalmente gravável (no POST), diferente de
        vehicle (sempre roteamento) — por isso é rejeitado explicitamente
        no PATCH, mesmo padrão de asking_price/sale_price (Prompt 15), não
        silenciosamente ignorado. Rejeição total: nem position (campo
        válido do mesmo payload) é aplicado."""
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('original.jpg')
        )
        original_image_name = photo.image.name

        response = self.client.patch(
            self.photo_detail_url(photo),
            {'image': make_uploaded_image('trocada.jpg'), 'position': 5},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

        photo.refresh_from_db()
        self.assertEqual(photo.image.name, original_image_name)  # não mudou
        self.assertEqual(photo.position, 0)  # position TAMBÉM não foi aplicado

    def test_patch_rejects_image_field_alone(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('original.jpg')
        )

        response = self.client.patch(
            self.photo_detail_url(photo),
            {'image': make_uploaded_image('trocada.jpg')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

    def test_patch_ignores_vehicle_field(self):
        """vehicle é campo de roteamento (sempre da URL) — diferente de
        image acima, fica silenciosamente ignorado, não rejeitado. Ver
        justificativa dessa distinção no docstring de VehiclePhotoSerializer."""
        other_vehicle = make_vehicle(self.company, brand='Outro')
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg')
        )

        response = self.client.patch(
            self.photo_detail_url(photo), {'vehicle': str(other_vehicle.pk)}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        photo.refresh_from_db()
        self.assertEqual(photo.vehicle_id, self.vehicle.pk)  # não mudou


class PhotoDeleteTests(PhotoAPITestCase):
    def test_delete_removes_record_and_physical_files(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg')
        )
        image_path = photo.image.path
        thumbnail_path = photo.thumbnail.path
        self.assertTrue(os.path.exists(image_path))
        self.assertTrue(os.path.exists(thumbnail_path))

        response = self.client.delete(self.photo_detail_url(photo))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VehiclePhoto.objects.filter(pk=photo.pk).exists())

        # sem soft delete: não existe "all_objects" pra achar o registro em
        # lugar nenhum, e os arquivos físicos saíram do storage de verdade
        self.assertFalse(os.path.exists(image_path))
        self.assertFalse(os.path.exists(thumbnail_path))

    def test_delete_of_cover_photo_leaves_no_cover_no_constraint_violation(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle, image=make_uploaded_image('a.jpg'), is_cover=True
        )

        response = self.client.delete(self.photo_detail_url(photo))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(VehiclePhoto.objects.filter(vehicle=self.vehicle).count(), 0)
