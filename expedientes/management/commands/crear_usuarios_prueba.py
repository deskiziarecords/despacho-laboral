from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Crea usuarios de prueba (1 superadmin, 4 admins, 15 asesores)'

    def handle(self, *args, **options):
        self.stdout.write('Creando usuarios de prueba...')
        self.stdout.write('-' * 50)

        # 1. Superadmin
        if not User.objects.filter(username='superadmin').exists():
            user = User.objects.create_superuser(
                username='superadmin',
                email='superadmin@despacho.mx',
                password='Admin123!',
                first_name='Admin',
                last_name='Super',
            )
            user.profile.rol = 'superadmin'
            user.profile.save()
            self.stdout.write(self.style.SUCCESS('OK Superadmin creado: superadmin / Admin123!'))
        else:
            self.stdout.write('-- Superadmin ya existe')

        # 2. Administrativos (4)
        admins_data = [
            ('admin1', 'Admin1!', 'Carlos', 'Muñoz'),
            ('admin2', 'Admin2!', 'María', 'González'),
            ('admin3', 'Admin3!', 'Patricia', 'López'),
            ('admin4', 'Admin4!', 'Jorge', 'Martínez'),
        ]

        for username, password, first_name, last_name in admins_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@despacho.mx',
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True,
                )
                user.profile.rol = 'admin'
                user.profile.save()
                self.stdout.write(self.style.SUCCESS(f'OK Admin creado: {username} / {password}'))
            else:
                self.stdout.write(f'-- {username} ya existe')

        # 3. Asesores (15)
        asesores_nombres = [
            ('asesor1', 'Asesor1!', 'Ana', 'Reyes'),
            ('asesor2', 'Asesor2!', 'Pedro', 'Soto'),
            ('asesor3', 'Asesor3!', 'Laura', 'Vargas'),
            ('asesor4', 'Asesor4!', 'Diego', 'Castillo'),
            ('asesor5', 'Asesor5!', 'Sofía', 'Ramos'),
            ('asesor6', 'Asesor6!', 'Andrés', 'Flores'),
            ('asesor7', 'Asesor7!', 'Valentina', 'Ortiz'),
            ('asesor8', 'Asesor8!', 'Felipe', 'Herrera'),
            ('asesor9', 'Asesor9!', 'Camila', 'Peña'),
            ('asesor10', 'Asesor10!', 'Matías', 'Cruz'),
            ('asesor11', 'Asesor11!', 'Isabella', 'Morales'),
            ('asesor12', 'Asesor12!', 'Benjamín', 'Rojas'),
            ('asesor13', 'Asesor13!', 'Antonia', 'Guerra'),
            ('asesor14', 'Asesor14!', 'Sebastián', 'Delgado'),
            ('asesor15', 'Asesor15!', 'Javiera', 'Pizarro'),
        ]

        # 4. Usuarios de Finanzas
        finanzas_data = [
            ('finanzas1', 'Finanzas1!', 'Roberto', 'Contreras'),
        ]

        for username, password, first_name, last_name in finanzas_data:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@despacho.mx',
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.profile.rol = 'finanzas'
                user.profile.save()
                self.stdout.write(self.style.SUCCESS(f'OK Finanzas creado: {username} / {password}'))
            else:
                self.stdout.write(f'-- {username} ya existe')

        for username, password, first_name, last_name in asesores_nombres:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@despacho.mx',
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
                user.profile.rol = 'asesor'
                user.profile.save()
                self.stdout.write(self.style.SUCCESS(f'OK Asesor creado: {username} / {password}'))
            else:
                self.stdout.write(f'-- {username} ya existe')

        self.stdout.write('-' * 50)
        self.stdout.write(self.style.SUCCESS('OK Todos los usuarios han sido creados exitosamente.'))
        self.stdout.write('')
        self.stdout.write('Resumen de accesos:')
        self.stdout.write('  Superadmin: superadmin / Admin123!')
        self.stdout.write('  Admins:     admin1-admin4 / Admin[1-4]!')
        self.stdout.write('  Finanzas:   finanzas1 / Finanzas1!')
        self.stdout.write('  Asesores:   asesor1-asesor15 / Asesor[1-15]!')
