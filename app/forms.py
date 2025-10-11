from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, DecimalField, RadioField
from wtforms.validators import DataRequired, Email, Length, ValidationError, NumberRange, EqualTo, Optional
from app.models import User, Device
from flask_wtf.file import FileField, FileAllowed

# USER LOGIN FORM
class LoginForm(FlaskForm):
    identifier = StringField('Username or Email', validators=[DataRequired(), Length(min=3, max=120)])
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
    username = StringField("Username", validators=[Optional()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    role = SelectField(
        "Role",
        choices=[
            ("admin", "Admin"),
            ("staff", "Staff")
        ],
        validators=[DataRequired()]
    )
    address = StringField("Address", validators=[Optional()])
    submit = SubmitField("Create User")

    def validate(self):
        rv = super().validate()
        if not rv:
            return False

        # Require username and address only if staff
        if self.role.data == "staff":
            if not self.username.data.strip():
                self.username.errors.append("Username is required for staff members.")
                return False
            if not self.address.data.strip():
                self.address.errors.append("Address is required for staff members.")
                return False
        return True


    

# DEVICE FORM
class DeviceForm(FlaskForm):
    brand = SelectField(
        "Brand",
        choices=[
            ("itel", "Itel"),
            ("samsung", "Samsung"),
            ("tecno", "Tecno"),
            ("infinix", "Infinix"),
        ],
        validators=[DataRequired()],
    )
    imei = StringField(
        "IMEI",
        validators=[Optional(), Length(min=15, max=15, message="IMEI must be exactly 15 digits long.")],
    )
    model = StringField("Model", validators=[DataRequired(), Length(max=50)])
    ram = SelectField(
        'RAM',
        choices=[('4GB', '4GB'), ('6GB', '6GB'), ('8GB', '8GB')],
        validators=[DataRequired()]
    )
    rom = SelectField(
        'ROM',
        choices=[('64GB', '64GB'), ('128GB', '128GB'), ('256GB', '256GB'), ('512GB', '512GB')],
        validators=[DataRequired()]
    )
    purchase_price = DecimalField("Purchase Price", validators=[DataRequired(), NumberRange(min=0)], places=2)
    price_cash = DecimalField("Selling Price", validators=[Optional(), NumberRange(min=0)])
    price_credit = DecimalField("Credit Price", validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField("Description", validators=[Optional()])
    assigned_staff_id = SelectField("Assign to Staff", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Save Device")

    def __init__(self, original_imei=None, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.original_imei = original_imei

    def set_staff_choices(self):
        # Query staff users only
        staff_users = User.query.filter_by(role="staff").order_by(User.username).all()
        self.assigned_staff_id.choices = [(u.id, u.username) for u in staff_users]

    def validate_imei(self, imei):
        if not imei.data:
            raise ValidationError("IMEI is required.")
        if len(imei.data) != 15:
            raise ValidationError("IMEI must be exactly 15 digits long.")

        if hasattr(self, "original_imei") and self.original_imei != imei.data:
            device = Device.query.filter_by(imei=imei.data).first()
            if device:
                raise ValidationError("This IMEI is already registered in the system.")

class SaleForm(FlaskForm):
    imei = StringField('IMEI', validators=[
        DataRequired(),
        Length(min=15, max=15, message='IMEI must be exactly 15 digits')
    ])
    sale_price = DecimalField('Sale Price',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2
    )
    payment_type = SelectField(
        'Payment Type',
        choices=[('cash', 'Cash'), ('credit', 'Credit')],
        validators=[DataRequired()]
    )

    amount_paid = DecimalField(
        'Amount Paid',
        validators=[DataRequired(), NumberRange(min=0)],
        places=2
    )
  # NEW: shop dropdown
    shop = SelectField(
        "Shop",
        choices=[
            ("Machu", "Machu"),
            ("Wachumba", "Wachumba"),
            ("ANC", "ANC"),
            ("Oasis", "Oasis"),
        ],
        validators=[DataRequired()]
    )

    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=100)])
    customer_phone = StringField('Phone Number', validators=[DataRequired(), Length(max=15)])
    id_number = StringField('ID Number', validators=[DataRequired(), Length(max=20)])
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
        


        
    #   EDIT USER FORM
class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password')  # Optional for editing
    role = SelectField('Role', choices=[('staff', 'Staff'), ('admin', 'Admin')], validators=[DataRequired()])
    address = StringField('Address', validators=[Optional()])
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



    
    
# RESET PASSWORD FORMS
class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


