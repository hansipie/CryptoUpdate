from django.db import models
from django.utils import timezone
import datetime

# Create your models here.
class CsvStore(models.Model):
    token = models.CharField(max_length=100)
    amount_invested = models.FloatField(default=0)
    coins_invested = models.FloatField(default=0)
    coin_price = models.FloatField(default=0)
    coins_count = models.FloatField(default=0)
    wallet_value = models.FloatField(default=0)
    nfts_count = models.FloatField(default=0)
    nfts_value = models.FloatField(default=0)
    total_value = models.FloatField(default=0)
    profit = models.FloatField(default=0)
    timestamp = models.IntegerField(default=0)
