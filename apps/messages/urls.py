"""
Messages URL patterns.
Mounted at /api/v1/businesses/{business_id}/messages/

GET    /                  List messages (filterable by status)
GET    /{message_id}/     Message detail (auto-marks as read)
PATCH  /{message_id}/     Update status (read/replied)
"""
from django.urls import path
from apps.messages.views import MessageDetailView, MessageListView

urlpatterns = [
    path("", MessageListView.as_view(), name="message-list"),
    path("<uuid:message_id>/", MessageDetailView.as_view(), name="message-detail"),
]
