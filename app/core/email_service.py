"""
Servicio de envío de emails con soporte SMTP.
Incluye templates HTML para emails transaccionales.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os


class EmailService:
    """Servicio para envío de emails."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "Cisnatura")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Enviar un email.
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            html_content: Contenido HTML del email
            plain_content: Contenido en texto plano (opcional)
        
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Agregar versión texto plano si existe
            if plain_content:
                part1 = MIMEText(plain_content, "plain")
                message.attach(part1)
            
            # Agregar versión HTML
            part2 = MIMEText(html_content, "html")
            message.attach(part2)
            
            # Configurar conexión según si hay credenciales o no
            # MailHog no requiere autenticación
            if self.smtp_user and self.smtp_password:
                # Determinar si usar SSL o STARTTLS según el puerto
                if self.smtp_port == 465:
                    # Puerto 465: SSL directo (Hostinger, Gmail SSL)
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        username=self.smtp_user,
                        password=self.smtp_password,
                        use_tls=True
                    )
                else:
                    # Puerto 587: STARTTLS (Gmail, SendGrid, etc.)
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        username=self.smtp_user,
                        password=self.smtp_password,
                        start_tls=True
                    )
            else:
                # Modo sin autenticación (MailHog, desarrollo)
                await aiosmtplib.send(
                    message,
                    hostname=self.smtp_host,
                    port=self.smtp_port
                )
            
            return True
            
        except Exception as e:
            print(f"Error al enviar email: {e}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        full_name: str,
        verification_token: str
    ) -> bool:
        """
        Enviar email de verificación de cuenta.
        
        Args:
            to_email: Email del usuario
            full_name: Nombre completo del usuario
            verification_token: Token de verificación
        
        Returns:
            bool: True si se envió correctamente
        """
        verification_url = f"{self.frontend_url}/verify-email?token={verification_token}"
        
        subject = "Confirma tu correo electrónico - Cisnatura"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verifica tu email</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">¡Bienvenido a Cisnatura!</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hola <strong>{full_name}</strong>,</p>
                
                <p style="font-size: 16px;">
                    Gracias por registrarte en Cisnatura. Para completar tu registro y poder acceder a tu cuenta, 
                    necesitamos que verifiques tu correo electrónico.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              font-weight: bold;
                              display: inline-block;
                              font-size: 16px;">
                        Verificar mi correo
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">
                    Si el botón no funciona, copia y pega este enlace en tu navegador:
                </p>
                <p style="font-size: 12px; color: #667eea; word-break: break-all;">
                    {verification_url}
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <p style="font-size: 12px; color: #666;">
                        <strong>Nota:</strong> Este enlace expirará en 24 horas por motivos de seguridad.
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Si no creaste esta cuenta, puedes ignorar este mensaje.
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                <p>© 2025 Cisnatura. Todos los derechos reservados.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        ¡Bienvenido a Cisnatura!
        
        Hola {full_name},
        
        Gracias por registrarte en Cisnatura. Para completar tu registro, verifica tu correo haciendo clic en el siguiente enlace:
        
        {verification_url}
        
        Este enlace expirará en 24 horas.
        
        Si no creaste esta cuenta, puedes ignorar este mensaje.
        
        © 2025 Cisnatura
        """
        
        return await self.send_email(to_email, subject, html_content, plain_content)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        full_name: str,
        reset_token: str
    ) -> bool:
        """
        Enviar email de recuperación de contraseña.
        
        Args:
            to_email: Email del usuario
            full_name: Nombre completo del usuario
            reset_token: Token de recuperación
        
        Returns:
            bool: True si se envió correctamente
        """
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
        
        subject = "Recuperación de contraseña - Cisnatura"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recuperar contraseña</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Recuperar Contraseña</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hola <strong>{full_name}</strong>,</p>
                
                <p style="font-size: 16px;">
                    Recibimos una solicitud para restablecer la contraseña de tu cuenta en Cisnatura.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              font-weight: bold;
                              display: inline-block;
                              font-size: 16px;">
                        Restablecer contraseña
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">
                    Si el botón no funciona, copia y pega este enlace en tu navegador:
                </p>
                <p style="font-size: 12px; color: #667eea; word-break: break-all;">
                    {reset_url}
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <p style="font-size: 12px; color: #666;">
                        <strong>Nota:</strong> Este enlace expirará en 1 hora por motivos de seguridad.
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Si no solicitaste restablecer tu contraseña, puedes ignorar este mensaje.
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                <p>© 2025 Cisnatura. Todos los derechos reservados.</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Recuperar Contraseña - Cisnatura
        
        Hola {full_name},
        
        Recibimos una solicitud para restablecer tu contraseña. Haz clic en el siguiente enlace:
        
        {reset_url}
        
        Este enlace expirará en 1 hora.
        
        Si no solicitaste esto, puedes ignorar este mensaje.
        
        © 2025 Cisnatura
        """
        
        return await self.send_email(to_email, subject, html_content, plain_content)


# Instancia singleton
email_service = EmailService()
