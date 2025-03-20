import pytest
from datetime import datetime
from api.database import Database

@pytest.mark.unit
@pytest.mark.async_test
class TestDatabase:
    @pytest.fixture
    def mock_supabase(self, mocker):
        return mocker.patch('api.database.supabase')

    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_supabase):
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user = {"id": "123", "email": email}
        mock_supabase.auth.sign_up.return_value.user = mock_user

        # Act
        result = await Database.create_user(email, password)

        # Assert
        assert result["success"] is True
        assert result["user"] == mock_user
        mock_supabase.auth.sign_up.assert_called_once_with({
            "email": email,
            "password": password
        })

    @pytest.mark.asyncio
    async def test_add_user_credits_new_user(self, mock_supabase):
        # Arrange
        user_id = "123"
        amount = 100.0
        mock_supabase.table().select().eq().single().execute.side_effect = Exception()
        mock_table = mock_supabase.table.return_value
        mock_table.insert.return_value.execute.return_value.data = [{"amount": amount}]

        # Act
        result = await Database.add_user_credits(user_id, amount)

        # Assert
        assert result["success"] is True
        assert result["credits"]["amount"] == amount
        mock_table.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_user_credits_existing_user(self, mock_supabase):
        # Arrange
        user_id = "123"
        current_amount = 50.0
        add_amount = 100.0
        mock_supabase.table().select().eq().single().execute.return_value.data = {"amount": current_amount}
        mock_supabase.table().update().eq().execute.return_value.data = [{"amount": current_amount + add_amount}]

        # Act
        result = await Database.add_user_credits(user_id, add_amount)

        # Assert
        assert result["success"] is True
        assert result["credits"]["amount"] == current_amount + add_amount

    @pytest.mark.asyncio
    async def test_create_transaction_success(self, mock_supabase):
        # Arrange
        user_id = "123"
        amount = 100.0
        transaction_type = "credit_purchase"
        description = "Test transaction"
        mock_supabase.table().insert().execute.return_value.data = [{
            "id": 1,
            "user_id": user_id,
            "amount": amount,
            "type": transaction_type,
            "description": description,
            "status": "completed"
        }]

        # Act
        result = await Database.create_transaction(
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            description=description
        )

        # Assert
        assert result["success"] is True
        assert result["transaction"]["amount"] == amount
        assert result["transaction"]["type"] == transaction_type

    @pytest.mark.asyncio
    async def test_use_credits_insufficient_balance(self, mock_supabase):
        # Arrange
        user_id = "123"
        amount = 100.0
        mock_supabase.table().select().eq().single().execute.return_value.data = {"amount": 50.0}

        # Act
        result = await Database.use_credits(user_id, amount)

        # Assert
        assert result["success"] is False
        assert "insuffisants" in result["error"] 