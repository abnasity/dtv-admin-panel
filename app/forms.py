from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField, TextAreaField, SelectField, DecimalField
from wtforms.validators import DataRequired, Email, Length, ValidationError, NumberRange, EqualTo, Optional
from app.models import User

# USER LOGIN FORM
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')   
    
# USER PROFILE FORM  
class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm New Password')
    submit = SubmitField('Update Profile')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already in use. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different one.')
            
# USER REGISTRATION FORM          
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('staff', 'Staff'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Create User')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already in use. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

# CUSTOMER REGISTRATION AND LOGIN FORMS
class CustomerRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number')
    address = StringField('Address')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Register')

class CustomerLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# DEVICE FORM
class DeviceForm(FlaskForm):
    imei = StringField('IMEI', validators=[
        DataRequired(), Length(min=15, max=15, message='IMEI must be exactly 15 digits long.')
    ])
    brand = StringField('Brand', validators=[DataRequired(), Length(max=50)])
    model = StringField('Model', validators=[DataRequired(), Length(max=50)])
    ram = StringField('RAM', validators=[DataRequired(), Length(max=20)])
    rom = StringField('ROM', validators=[DataRequired(), Length(max=20)])
    purchase_price = DecimalField('Purchase Price', validators=[DataRequired(), NumberRange(min=0)], places=2)
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Device')
    
    def __init__(self, original_imei=None, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.original_imei = original_imei
        
    def validate_imei(self, imei):
        from app.models import Device
        if self.original_imei != imei.data:
            device = Device.query.filter_by(imei=imei.data).first()
            if device:
                raise ValidationError('This IMEI is already registered in the system.')
            
 
# SALE FORM           
class SaleForm(FlaskForm):
    imei = StringField('IMEI', validators=[
        DataRequired(),
        Length(min=15, max=15, message='IMEI must be exactly 15 digits')
    ])
    sale_price = DecimalField('Sale Price',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2
    )
    payment_type = SelectField('Payment Type',
        choices=[('cash', 'Cash'), ('credit', 'Credit')],
        validators=[DataRequired()]
    )
    amount_paid = DecimalField('Amount Paid',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2
    )
    notes = TextAreaField('Notes')
    submit = SubmitField('Record Sale')

    def validate_imei(self, imei):
        from app.models import Device
        device = Device.query.filter_by(imei=imei.data).first()
        if not device:
            raise ValidationError('Device with this IMEI not found in inventory.')
        if not device.is_available:
            raise ValidationError('This device has already been sold.')

    def validate_amount_paid(self, amount_paid):
        if self.payment_type.data == 'cash' and amount_paid.data < self.sale_price.data:
            raise ValidationError('For cash payments, the amount paid must equal the sale price.')
        

# EDIT CUSTOMER FORM
class CustomerEditForm(FlaskForm):
     full_name = StringField('Full Name', validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    
     email = StringField('Email', validators=[
        DataRequired(), Email()
    ])
    
     phone_number = StringField('Phone Number', validators=[
        Optional(), Length(min=10, max=20)
    ])
    
     address = StringField('Address', validators=[
        Optional(), Length(max=255)
    ])
    
     submit = SubmitField('Update Profile')

        
    #   EDIT USER FORM
class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password')  # Optional for editing
    role = SelectField('Role', choices=[('staff', 'Staff'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Update User')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already in use. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different one.')

