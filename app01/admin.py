from django.contrib import admin
from app01 import models

admin.site.register(models.User)
admin.site.register(models.Role)
admin.site.register(models.Permission)
