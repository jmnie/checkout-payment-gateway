from uuid import UUID, uuid4

from payment_gateway_api.bank import BankClient
from payment_gateway_api.models import Payment, PaymentRequest


class PaymentService:
    def __init__(self, bank: BankClient):
        self.bank = bank
        self.payments: dict[UUID, Payment] = {}

    async def create(self, request: PaymentRequest) -> Payment:
        authorized = await self.bank.authorize(request)
        payment = Payment(
            id=uuid4(),
            status="Authorized" if authorized else "Declined",
            card_number_last_four=request.card_number[-4:],
            expiry_month=request.expiry_month,
            expiry_year=request.expiry_year,
            currency=request.currency,
            amount=request.amount,
        )
        self.payments[payment.id] = payment
        return payment

    def get(self, payment_id: UUID) -> Payment | None:
        return self.payments.get(payment_id)
