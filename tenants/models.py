from django.db import models

class Client(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tenants'

    def __str__(self):
        return self.name