from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import base64

def get_adjust_points_flag():
    """
    Indica si los puntos deben ajustarse.
    Puedes personalizar esta lógica según las necesidades del proyecto.
    """
    return True

def enviar_correo_bienvenida(user, email, generated_password):
    subject = 'Bienvenido a Nettplus'
    from_email = 'ticsncs@nettplus.net'
    to = [email]

    # Cargar logo desde archivo local y convertir a base64
    with open("static/img/logo_nettplus.png", "rb") as image_file:
        encoded_logo = base64.b64encode(image_file.read()).decode('utf-8')

    context = {
        'username': user.username,
        'password': generated_password,
        'logo_base64': encoded_logo,
    }

    html_content = render_to_string('email.html', context)
    text_content = f'Hola {user.username}, tu contraseña temporal es: {generated_password}'

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()