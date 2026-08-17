import urllib.request
import urllib.error
import json
import logging
from app.infrastructure.sendgrid import EmailService
from app.core.config import settings
