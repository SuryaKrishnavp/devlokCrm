from django.db import models
from django.utils import timezone
from auth_section.models import Sales_manager_reg
# Create your models here.
class Leads(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phonenumber = models.CharField(max_length=15)
    district = models.CharField(max_length=100)
    place = models.CharField(max_length=100)
    address = models.CharField(max_length=120)
    purpose = models.CharField(max_length=100)
    mode_of_purpose = models.CharField(max_length=100)
    message = models.TextField(max_length=250)
    status = models.CharField(max_length = 100,default="Pending")
    stage = models.CharField(max_length=100,default="Not Opened")
    closed_date = models.DateField(null=True,blank=True)
    follower = models.CharField(max_length=100,default="Nil")
    staff_id = models.IntegerField(default=0)