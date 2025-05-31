from apps.notifications.services import (
    UserNotificationService,
    FirebaseNotificationService,
)

import datetime
from apps.clients.models import (
    Contract,
    UserProfile,
    PointsCategory,
    PointsByPlanCategory,
    Transaction,
)


def assign_anniversary_points():
    # Obtener la categoría de puntos "ANIVERSARIO"
    anniversary_category = PointsCategory.objects.filter(
        name="ANIVERSARIO", enabled=True
    ).first()

    if not anniversary_category:
        print("⚠️ No se ha encontrado la categoría de ANIVERSARIO.")
        return

    # Obtener todos los contratos con fecha de inicio
    contracts = Contract.objects.filter(fecha_inicio__isnull=False)

    # Verificar que se cumpla un aniversario
    for contract in contracts:
        today = datetime.date.today()
        anniversary_date = contract.fecha_inicio.replace(year=today.year)

        if anniversary_date == today:
            if anniversary_category.enabled:
                usuarios = []

                if anniversary_category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not anniversary_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if anniversary_category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not anniversary_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios.append(usuario)

                # Asignar puntos a los usuarios
                point_config = PointsByPlanCategory.objects.filter(
                    category=anniversary_category, plan=contract.planInternet
                ).first()

                # Para cada usuario válido, asignar puntos
                for user in usuarios:
                    # Asignar puntos
                    user.points += point_config.points
                    user.save()

                    # Crear la transacción
                    Transaction.objects.create(
                        user=user,
                        amount=point_config.points,
                        status=0,
                        tipo="Internal",
                        transaction_status="Completed",
                        saldo=user.points,
                        descripcion=f"Asignación de puntos por aniversario del contrato {contract.contract_id}",
                    )

                    # Crear notificación
                    try:
                        notification_text = anniversary_category.description
                        message = f"{contract.contract_id}: Se te han asignado {point_config.points} puntos {notification_text}"
                        UserNotificationService.create_notification(
                            user,
                            "Puntos acreditados",
                            message,
                        )
                    except Exception as e:
                        print(e)

                    # Enviar notificación push
                    device = user.fcmdevice_set.first()
                    if device and device.registration_id:
                        try:
                            notification_text = anniversary_category.description
                            message = f"{contract.contract_id}: Se te han asignado {point_config.points} puntos {notification_text}"
                            FirebaseNotificationService.send_firebase_notification(
                                device.registration_id,
                                "Puntos acreditados",
                                message,
                                data=None,
                            )
                        except Exception as e:
                            print(e)


import datetime


def assign_birthday_points():
    # Obtener la categoría de puntos "CUMPLEANOS"
    birthday_category = PointsCategory.objects.filter(
        name="CUMPLEANOS", enabled=True
    ).first()

    if not birthday_category:
        print("⚠️ No se ha encontrado la categoría de CUMPLEANOS.")
        return

    # Obtener todos los contratos con fecha de nacimiento
    contracts = Contract.objects.filter(fecha_nacimiento__isnull=False)

    # Verificar si hoy es el cumpleaños
    for contract in contracts:
        today = datetime.date.today()

        # Reemplazar el año en la fecha de nacimiento
        try:
            birth_date = contract.fecha_nacimiento.replace(year=today.year)
        except ValueError:
            if today.year % 4 != 0 or (today.year % 100 == 0 and today.year % 400 != 0):
                # Ajustar a 28 de febrero si no es bisiesto
                birth_date = contract.fecha_nacimiento.replace(
                    year=today.year, month=2, day=28
                )
            else:
                # Si es bisiesto, mantener la fecha con el 29 de febrero
                birth_date = contract.fecha_nacimiento.replace(year=today.year)

        # Verificar si hoy es el día exacto del cumpleaños
        if birth_date == today:
            if birthday_category.enabled:
                usuarios = []

                if birthday_category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not birthday_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if birthday_category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not birthday_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios.append(usuario)

                # Asignar puntos a los usuarios
                point_config = PointsByPlanCategory.objects.filter(
                    category=birthday_category, plan=contract.planInternet
                ).first()

                if not point_config:
                    print(
                        f"⚠️ Sin configuración de puntos para el contrato: {contract.contract_id}"
                    )
                    continue

                for user in usuarios:
                    # Asignar puntos
                    user.points += point_config.points
                    user.save()

                    # Crear la transacción
                    Transaction.objects.create(
                        user=user,
                        amount=point_config.points,
                        status=0,
                        tipo="Internal",
                        transaction_status="Completed",
                        saldo=user.points,
                        descripcion=f"Asignación de puntos por cumpleaños del contrato {contract.contract_id}",
                    )

                    # Crear notificación
                    try:
                        notification_text = birthday_category.description
                        message = f"Se te han asignado {point_config.points} puntos {notification_text}"
                        UserNotificationService.create_notification(
                            user,
                            "Puntos acreditados",
                            message,
                        )

                    except Exception as e:
                        print(e)

                    # Enviar notificación push
                    device = user.fcmdevice_set.first()
                    if device and device.registration_id:
                        try:
                            notification_text = birthday_category.description
                            message = f"Se te han asignado {point_config.points} puntos {notification_text}"
                            FirebaseNotificationService.send_firebase_notification(
                                device.registration_id,
                                "Puntos acreditados",
                                message,
                                data=None,
                            )
                        except Exception as e:
                            print(e)


def assign_christmas_points():
    christmas_category = PointsCategory.objects.filter(
        name="CUMPLEANOS", enabled=True
    ).first()

    if not christmas_category:
        print("⚠️ No se ha encontrado la categoría de CUMPLEANOS.")
        return

    # Obtener todos los contratos con fecha de inicio
    contracts = Contract.objects.filter(fecha_inicio__isnull=False)

    # Verificar que se cumpla un aniversario
    for contract in contracts:
        today = datetime.date.today()

        if today.month == 12 and today.day == 25:
            if christmas_category.enabled:
                usuarios = []

                if christmas_category.only_with_fathers:
                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not christmas_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios = [usuario]
                else:
                    usuarios_qs = UserProfile.objects.filter(
                        contract=contract, is_active=True
                    )

                    if christmas_category.only_privacy_terms:
                        usuarios_qs = usuarios_qs.filter(privacityandterms=True)
                    usuarios = list(usuarios_qs)

                    usuario = contract.userprofile
                    if (
                        usuario
                        and usuario.is_active
                        and usuario.father
                        and (
                            not christmas_category.only_privacy_terms
                            or usuario.privacityandterms
                        )
                    ):
                        usuarios.append(usuario)

                # Asignar puntos a los usuarios
                point_config = PointsByPlanCategory.objects.filter(
                    category=christmas_category, plan=contract.planInternet
                ).first()

                # Para cada usuario válido, asignar puntos
                for user in usuarios:
                    # Asignar puntos
                    user.points += point_config.points
                    user.save()

                    # Crear la transacción
                    Transaction.objects.create(
                        user=user,
                        amount=point_config.points,
                        status=0,
                        tipo="Internal",
                        transaction_status="Completed",
                        saldo=user.points,
                        descripcion=f"Asignación de puntos por aniversario del contrato {contract.contract_id}",
                    )

                    # Crear notificación
                    try:
                        notification_text = christmas_category.description
                        message = f"Se te han asignado {point_config.points} puntos {notification_text}"
                        UserNotificationService.create_notification(
                            user,
                            "Puntos acreditados",
                            message,
                        )

                    except Exception as e:
                        print(e)

                    # Enviar notificación push
                    device = user.fcmdevice_set.first()
                    if device and device.registration_id:
                        try:
                            notification_text = christmas_category.description
                            message = f"Se te han asignado {point_config.points} puntos {notification_text}"
                            FirebaseNotificationService.send_firebase_notification(
                                device.registration_id,
                                "Puntos acreditados",
                                message,
                                data=None,
                            )
                        except Exception as e:
                            print(e)
