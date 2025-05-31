import smtplib
import time
import dns.resolver
from django.core.exceptions import ValidationError

def verificar_dominio_email(email):
    """
    Verifica si el dominio del email tiene registros MX válidos.
    """
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        return {"success": True, "message": f"Dominio {domain} válido con MX: {mx_record}"}
    except Exception as e:
        raise ValidationError("No se pudo verificar la existencia del correo.")

def verificar_existencia_email(email):
    try:
        # Obtener el dominio y el servidor MX
        domain = email.split('@')[1]
        print(domain)

        # Obtener el servidor MX
        mx_records = dns.resolver.resolve(domain, 'MX')
        print(mx_records)

        # Tomar el primer registro MX
        mx_host = str(mx_records[0].exchange)
        print(mx_host)

        # Conectar con el servidor de correo
        attempts = 0
        max_attempts = 6
        while attempts < max_attempts:
            try:
                server = smtplib.SMTP(mx_host, timeout=2)  # Conectar con el servidor MX con un timeout de 2 segundos
                server.set_debuglevel(0)  # 0 para no mostrar mensajes
                server.helo()  # Saludo al servidor
                server.mail('test@example.com')  # Se puede usar un correo genérico
                code, message = server.rcpt(email)
                server.quit()
                break
            except Exception as e:
                attempts += 1
                time.sleep(1)
                if attempts == max_attempts:
                    raise e

        if code == 250:
            return {"success": True, "message": "📧 Correo válido y existente"}
        else:
            raise ValidationError("Correo no existe.")
    except Exception as e:
        raise ValidationError("No se pudo verificar la existencia del correo.")

def validate_email_format(email):
    # Verificar dominio
    try:
        domain = email.split('@')[1]
        records = dns.resolver.resolve(domain, 'MX')
    except Exception as e:
        raise ValidationError("El dominio del correo no es válido.")

    # Verificar existencia
    try:
        mx_record = str(records[0].exchange)
        server = smtplib.SMTP(mx_record, timeout=2)
        server.helo()
        server.mail('test@example.com')
        code, message = server.rcpt(email)
        server.quit()
        if code != 250:
            raise ValidationError("El correo no existe en el servidor.")
    except Exception:
        raise ValidationError("No se pudo verificar la existencia del correo.")