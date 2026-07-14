import urllib.request
import urllib.error
import json
import logging
from app.infrastructure.sendgrid import EmailService
from app.common.config import settings
