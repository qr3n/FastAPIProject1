from typing import List
from shared.models.business import Business
from shared.models.user import User
from app.schemas.business import BusinessCreateSchema, BusinessUpdateSchema
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError
)


class BusinessService:
    """Service for managing businesses."""

    @staticmethod
    async def create_business(
            business_data: BusinessCreateSchema,
            owner: User
    ) -> Business:
        """
        Create a new business with Telegram bot.

        Args:
            business_data: Business creation data
            owner: Business owner

        Returns:
            Created business instance
        """
        business = await Business.create(
            owner=owner,
            name=business_data.name,
            description=business_data.description,
            business_type=business_data.business_type,
            telegram_bot_token=business_data.telegram_bot_token
        )

        print(f"[BOT STUB] Creating Telegram bot for business '{business.name}'")
        print(f"[BOT STUB] Business Type: {business.business_type.value}")
        print(f"[BOT STUB] Bot Token: {business_data.telegram_bot_token[:10]}...")
        print(f"[BOT STUB] Owner: {owner.username}")
        print(f"[BOT STUB] Business ID: {business.id}")

        return business

    @staticmethod
    async def get_business_by_id(business_id: str) -> Business:
        """
        Get business by ID.

        Args:
            business_id: Business UUID

        Returns:
            Business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
        """
        business = await Business.get_or_none(id=business_id)

        if not business:
            raise BusinessNotFoundError(business_id)

        return business

    @staticmethod
    async def get_user_businesses(user: User) -> List[Business]:
        """
        Get all businesses owned by user.

        Args:
            user: User instance

        Returns:
            List of user's businesses
        """
        return await Business.filter(owner=user).all()

    @staticmethod
    async def update_business(
            business_id: str,
            business_data: BusinessUpdateSchema,
            user: User
    ) -> Business:
        """
        Update a business.

        Args:
            business_id: Business UUID
            business_data: Updated business data
            user: User making the request

        Returns:
            Updated business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}

        if business_data.name is not None:
            update_fields['name'] = business_data.name

        if business_data.description is not None:
            update_fields['description'] = business_data.description

        if business_data.business_type is not None:
            update_fields['business_type'] = business_data.business_type

        if business_data.telegram_bot_token is not None:
            update_fields['telegram_bot_token'] = business_data.telegram_bot_token
            print(f"[BOT STUB] Updating bot token for business '{business.name}'")

        if business_data.is_active is not None:
            update_fields['is_active'] = business_data.is_active

        await business.update_from_dict(update_fields).save()
        await business.refresh_from_db()

        return business

    @staticmethod
    async def delete_business(business_id: str, user: User) -> None:
        """
        Delete a business.

        Args:
            business_id: Business UUID
            user: User making the request

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        business = await BusinessService.get_business_by_id(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        print(f"[BOT STUB] Deleting bot for business '{business.name}'")

        await business.delete()

    @staticmethod
    def verify_business_access(business: Business, user: User) -> None:
        """
        Verify user has access to business.

        Args:
            business: Business to check
            user: User to verify

        Raises:
            BusinessAccessDeniedError: If user doesn't own the business
        """
        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()