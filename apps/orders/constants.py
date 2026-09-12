"""Order domain constants."""

ORDER_STATUS_CHOICES = [
    ("new", "New"),
    ("confirmed", "Confirmed"),
    ("processing", "Processing"),
    ("ready", "Ready"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
]

# Valid transitions from each status — enforces the state machine
ORDER_STATUS_TRANSITIONS = {
    "new":        ["confirmed", "cancelled"],
    "confirmed":  ["processing", "cancelled"],
    "processing": ["ready", "cancelled"],
    "ready":      ["completed", "cancelled"],
    "completed":  [],   # terminal
    "cancelled":  [],   # terminal
}

PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("paid", "Paid"),
    ("failed", "Failed"),
    ("refunded", "Refunded"),
]

PAYMENT_METHOD_CHOICES = [
    ("mpesa", "M-PESA"),
    ("cash", "Cash"),
    ("card", "Card"),
    ("bank_transfer", "Bank Transfer"),
    ("whatsapp", "WhatsApp"),
]

ORDER_CHANNEL_CHOICES = [
    ("online", "Online"),
    ("whatsapp", "WhatsApp"),
    ("walk-in", "Walk-in"),
    ("phone", "Phone"),
]

DELIVERY_FEE = 300          # KSh — default delivery fee
FREE_DELIVERY_THRESHOLD = 10000  # KSh — free delivery above this subtotal
