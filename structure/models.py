from django.db import models

class City(models.Model):
    city = models.CharField(max_length=255)
    long = models.FloatField()
    lat = models.FloatField()

    def __str__(self):
        return self.city

class Testimonial(models.Model):
    SOURCE_CHOICES = [
        ('Candidate', 'Candidate'),
        ('Client', 'Client'),
    ]

    name = models.CharField(max_length=100)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    rating = models.PositiveIntegerField()  # Rating out of 5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.source}) - {self.rating} Stars"