from flask_mail import Message
from flask import url_for, current_app
from app.extensions import mail

def send_customer_reset_email(customer):
    token = customer.get_reset_token()
    reset_url = url_for('customers.customer_reset_token', token=token, _external=True)
    msg = Message('Reset Your Customer Password',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[customer.email])
    msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg)
