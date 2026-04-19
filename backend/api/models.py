from django.db import models


class User(models.Model):
    googleId = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, default="customer")
    phone = models.CharField(max_length=50, blank=True, null=True)
    cin = models.CharField(max_length=50, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    google_access_token = models.TextField(blank=True, null=True)
    picture = models.URLField(blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        ordering = []

    def __str__(self):
        return self.name


class Customer(models.Model):
    customer_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    cin = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"
        ordering = []

    def __str__(self):
        return self.name


class Account(models.Model):
    customer_id = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="TND")
    status = models.CharField(max_length=50, default="active")
    opened_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "accounts"
        ordering = []

    def __str__(self):
        return f"{self.account_number} - {self.customer_id}"


class BankTransaction(models.Model):
    customer_id = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=100, unique=True)
    transaction_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=10, default="TND")
    description = models.TextField(blank=True, null=True)
    transaction_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bank_transactions"
        ordering = []

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"


class Cheque(models.Model):
    customer_id = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)
    cheque_number = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payee = models.CharField(max_length=255, blank=True, null=True)
    issue_date = models.DateField()
    status = models.CharField(max_length=50, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cheques"
        ordering = []

    def __str__(self):
        return f"{self.cheque_number} - {self.status}"


class Reclamation(models.Model):
    customer_id = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    complaint = models.TextField()
    type = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default="pending")
    priority = models.CharField(max_length=50, default="normal")
    assigned_to = models.CharField(max_length=255, blank=True, null=True)
    resolution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reclamations"
        ordering = []

    def __str__(self):
        return f"{self.id} - {self.status}"


class Booking(models.Model):
    customer_id = models.CharField(max_length=255)
    summary = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default="confirmed")
    calendar_sync = models.BooleanField(default=False)
    calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookings"
        ordering = []

    def __str__(self):
        return f"{self.summary} - {self.start}"


class RecoveryLoan(models.Model):
    customer_id = models.CharField(max_length=255)
    loan_number = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=50, default="active")
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recovery_loans"
        ordering = []

    def __str__(self):
        return f"{self.loan_number} - {self.status}"


class BankParam(models.Model):
    param_key = models.CharField(max_length=100, unique=True)
    param_value = models.TextField()
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_params"
        ordering = []

    def __str__(self):
        return self.param_key
