import pytest
from fastapi import HTTPException
from api.payments import router, CreditPackage, CreatePaymentIntentRequest, get_credit_packages, create_payment_intent, process_successful_payment
from unittest.mock import Mock, AsyncMock

@pytest.mark.unit
class TestPayments:
    @pytest.fixture
    def mock_stripe(self, mocker):
        return mocker.patch('api.payments.stripe')

    @pytest.fixture
    def mock_database(self, mocker):
        mock = mocker.patch('api.payments.Database')
        # Configuration des méthodes asynchrones
        mock.create_transaction = AsyncMock()
        mock.add_user_credits = AsyncMock()
        return mock

    @pytest.fixture
    def mock_current_user(self):
        return {"id": "test_user_id"}

    @pytest.mark.asyncio
    async def test_get_credit_packages(self):
        # Act
        packages = await get_credit_packages()

        # Assert
        assert len(packages) == 3
        assert any(p.id == "basic" for p in packages)
        assert any(p.id == "pro" for p in packages)
        assert any(p.id == "enterprise" for p in packages)

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self, mock_stripe, mock_database, mock_current_user):
        # Arrange
        request = CreatePaymentIntentRequest(package_id="basic")
        mock_stripe.PaymentIntent.create.return_value.client_secret = "test_secret"
        mock_stripe.PaymentIntent.create.return_value.id = "pi_test"
        mock_database.create_transaction.return_value = {
            "success": True,
            "transaction": {"id": 1}
        }

        # Act
        result = await create_payment_intent(request, mock_current_user)

        # Assert
        assert result["clientSecret"] == "test_secret"
        assert result["package"].id == "basic"
        assert result["transaction"]["id"] == 1
        mock_stripe.PaymentIntent.create.assert_called_once()
        mock_database.create_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_intent_invalid_package(self, mock_current_user):
        # Arrange
        request = CreatePaymentIntentRequest(package_id="invalid")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_payment_intent(request, mock_current_user)
        assert exc_info.value.status_code == 404
        assert "Package non trouvé" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_successful_payment(self, mock_stripe, mock_database):
        # Arrange
        payment_intent = Mock()
        payment_intent.metadata = {
            "user_id": "test_user_id",
            "credits": "100"
        }
        payment_intent.amount = 999  # 9.99 in cents
        payment_intent.id = "pi_test"
        
        mock_database.create_transaction.return_value = {
            "success": True,
            "transaction": {"id": 1}
        }
        mock_database.add_user_credits.return_value = {
            "success": True,
            "credits": {"amount": 100}
        }

        # Act
        result = await process_successful_payment(payment_intent)

        # Assert
        assert result["success"] is True
        assert "transaction" in result
        assert "credits" in result
        mock_database.create_transaction.assert_called_once()
        mock_database.add_user_credits.assert_called_once_with("test_user_id", 100) 